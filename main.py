from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI()

DB_FILE = "tracks.db"

# Автосоздание таблицы при запуске
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                url TEXT NOT NULL,
                mood INTEGER,
                comment TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
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
init_db()

# Pydantic модель
class Track(BaseModel):
    title: str
    author: str
    url: str
    mood: int
    comment: str
    user_id: int  # добавляем сюда ID пользователя

class User(BaseModel):
    username: str
    password: str

class Follow(BaseModel):
    user_id: int
    track_id: int

@app.post("/submit")
def submit_track(track: Track):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tracks (title, author, url, mood, comment, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (track.title, track.author, track.url, track.mood, track.comment, track.user_id))
        conn.commit()
    return {"status": "ok"}

@app.get("/tracks")
def get_tracks(user_id: int, page: int = 1, limit: int = 5):
    offset = (page - 1) * limit
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM tracks")
        total = cursor.fetchone()[0]

        cursor.execute('''
            SELECT id, title, author, url, mood, comment, timestamp
            FROM tracks
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
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
                    "mood": row[4],
                    "comment": row[5],
                    "timestamp": row[6]
                }
                for row in rows
            ],
            "followed_ids": followed_ids
        }
    
@app.post("/user")
def submit_track(user: User):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Проверка существования пользователя
        cursor.execute("SELECT password FROM users WHERE username = ?", (user.username,))
        row = cursor.fetchone()

        if row is None:
            # Новый пользователь — создаём
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user.username, user.password))
            conn.commit()
            user_id = cursor.lastrowid
            return {"status": "registered", "user_id": user_id}
        elif row[0] == user.password:
            # Пароль совпал — вход разрешён
            cursor.execute("SELECT id FROM users WHERE username = ?", (user.username,))
            user_id = cursor.fetchone()[0]
            return {"status": "ok", "user_id": user_id}
        else:
            # Пароль неверный
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
            SELECT t.id, t.title, t.author, t.url, t.mood, t.comment, t.timestamp
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
                "mood": row[4],
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