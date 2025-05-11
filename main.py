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
def get_tracks(page: int = 1, limit: int = 10):
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
            ]
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
            return {"status": "registered"}
        elif row[0] == user.password:
            # Пароль совпал — вход разрешён
            cursor.execute("SELECT id FROM users WHERE username = ?", (user.username,))
            user_id = cursor.fetchone()[0]
            return {"status": "ok"}
        else:
            # Пароль неверный
            raise HTTPException(status_code=401, detail="Invalid password")