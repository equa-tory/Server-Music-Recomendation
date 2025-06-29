from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sqlite3
import os

app = FastAPI()

DB_FILE = "tracks.db"

# ----------------------------------------------------------------
# table creation
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moods (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                url TEXT NOT NULL,
                mood_id INTEGER,
                "comment" TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                FOREIGN KEY(mood_id) REFERENCES moods(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS follows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                track_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(track_id) REFERENCES tracks(id),
                UNIQUE(user_id, track_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                track_id INTEGER,
                category TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(sender_id) REFERENCES users(id),
                FOREIGN KEY(track_id) REFERENCES tracks(id)
            )
        ''')
        
        # moods table filler
        cursor.execute("SELECT COUNT(*) FROM moods")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO moods (id, name) VALUES (?, ?)", [
                (1, '👻 Other'),
                (2, '💥 Drive'),
                (3, '🛋️ Chill'),
                (4, '💔 Sad'),
                (5, '❄ Christmas')
            ])
            
init_db()

# ----------------------------------------------------------------
# classes
class Track(BaseModel):
    title: str = Field(..., min_length=2, max_length=30)
    author: str = Field(..., min_length=2, max_length=22)
    url: str = Field(..., max_length=120)
    mood_id: int
    comment: str
    user_id: int

class User(BaseModel):
    login: str
    password: str

class Follow(BaseModel):
    user_id: int
    track_id: int

class Report(BaseModel):
    sender_id: int
    track_id: int
    category: str

class DeleteRequest(BaseModel):
    track_id: int

# ----------------------------------------------------------------
# requests
@app.post("/submit")
def submit_track(track: Track):
    # Link generation check if it's null
    if not track.url.strip():
        query = f"{track.title} {track.author}".strip().replace(" ", "+")
        track.url = f"https://www.youtube.com/results?search_query={query}"

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tracks (title, author, url, mood_id, comment, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (track.title, track.author, track.url, track.mood_id, track.comment, track.user_id))
        conn.commit()
    return {"status": "ok"}

@app.post("/delete")
def delete_track(data: DeleteRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM tracks
            WHERE id = ?
        ''', (data.track_id,))
        conn.commit()
    return {"status": "deleted"}

@app.get("/tracks")
def get_tracks(user_id: int, page: int = 1, limit: int = 5, sort: str = "none", profile: bool = False):
    offset = (page - 1) * limit
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        if profile:
            total_query = 'SELECT COUNT(*) FROM tracks WHERE user_id = ?'
            cursor.execute(total_query, (user_id,))
            total = cursor.fetchone()[0]

            query = '''
                SELECT t.id, t.title, t.author, t.url, t.mood_id, t.comment, t.timestamp
                FROM tracks t
                WHERE t.user_id = ?
                ORDER BY t.timestamp DESC
                LIMIT ? OFFSET ?
            '''
            cursor.execute(query, (user_id, limit, offset))
            rows = cursor.fetchall()

            cursor.execute("SELECT track_id FROM follows WHERE user_id = ?", (user_id,))
            followed_ids = [row[0] for row in cursor.fetchall()]

            return {
                "total": total,
                "data": [
                    {
                        "id": row[0],
                        "title": row[1],
                        "author": row[2],
                        "url": row[3],
                        "mood_id": row[4],
                        "comment": row[5],
                        "timestamp": row[6]
                    }
                    for row in rows
                ],
                "followed_ids": followed_ids
            }

        cursor.execute("SELECT COUNT(*) FROM tracks")
        total = cursor.fetchone()[0]

        # sort selection
        if sort == "popular":
            order_by = "(SELECT COUNT(*) FROM follows WHERE track_id = t.id) DESC"
        elif sort == "followed":
            order_by = "CASE WHEN f.user_id = ? THEN 0 ELSE 1 END, t.timestamp DESC"
        elif sort == "week":
            order_by = "(SELECT COUNT(*) FROM follows WHERE track_id = t.id AND DATE(timestamp) >= DATE('now', '-7 day')) DESC"
        elif "mood" in sort:
            mood_index = int(sort.split(":")[1])
            order_by = f"t.mood_id = {mood_index} DESC"
        else:
            order_by = "t.timestamp DESC"

        query = f'''
            SELECT t.id, t.title, t.author, t.url, t.mood_id, t.comment, t.timestamp
            FROM tracks t
            LEFT JOIN follows f ON t.id = f.track_id
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        '''
        if sort == "followed":
            cursor.execute(query, (user_id, limit, offset))
        else:
            cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()

        cursor.execute("SELECT track_id FROM follows WHERE user_id = ?", (user_id,))
        followed_ids = [row[0] for row in cursor.fetchall()]

        return {
            "total": total,
            "data": [
                {
                    "id": row[0],
                    "title": row[1],
                    "author": row[2],
                    "url": row[3],
                    "mood_id": row[4],
                    "comment": row[5],
                    "timestamp": row[6]
                }
                for row in rows
            ],
            "followed_ids": followed_ids
        }
    
@app.get("/moods")
def get_moods():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM moods")
        rows = cursor.fetchall()
        return [{"id": row[0], "name": row[1]} for row in rows]

@app.post("/user")
def submit_track(user: User):
    if not (2 <= len(user.login) <= 16):
        raise HTTPException(status_code=400, detail="Login and password must be 2–16 characters long")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # User existance check
        cursor.execute("SELECT password FROM users WHERE login = ?", (user.login,))
        row = cursor.fetchone()

        if row is None:
            # Creating new user
            cursor.execute("INSERT INTO users (login, password) VALUES (?, ?)", (user.login, user.password))
            conn.commit()
            user_id = cursor.lastrowid
            return {"status": "registered", "user_id": user_id}
        elif row[0] == user.password:
            # Password is right
            cursor.execute("SELECT id FROM users WHERE login = ?", (user.login,))
            user_id = cursor.fetchone()[0]
            return {"status": "ok", "user_id": user_id}
        else:
            # Wrong password
            raise HTTPException(status_code=401, detail="Invalid password")

@app.post("/follow")
def follow_track(follow: Follow):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO follows (user_id, track_id)
                VALUES (?, ?)
            ''', (follow.user_id, follow.track_id))
            conn.commit()
            return {"status": "followed"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Already followed or invalid ID")

@app.get("/followed")
def get_followed_tracks(user_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.id, t.title, t.author, t.url, t.mood_id, t.comment, t.timestamp
            FROM tracks t
            JOIN follows f ON t.id = f.track_id
            WHERE f.user_id = ?
            ORDER BY f.timestamp DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "title": row[1],
                "author": row[2],
                "url": row[3],
                "mood_id": row[4],
                "comment": row[5],
                "timestamp": row[6]
            }
            for row in rows
        ]

@app.post("/unfollow")
def unfollow_track(follow: Follow):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM follows
            WHERE user_id = ? AND track_id = ?
        ''', (follow.user_id, follow.track_id))
        conn.commit()
        return {"status": "unfollowed"}
    
@app.post("/report")
def report_track(report: Report):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reports (sender_id, track_id, category) VALUES (?, ?, ?)",
                       (report.sender_id, report.track_id, report.category))
        conn.commit()
    return {"status": "ok"}