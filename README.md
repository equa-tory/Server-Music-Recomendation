# 🎧 Luno - Server

Python server for annonimous recommending music to other people.

## 🛠️ Technologies Used
What was used to build this app:
- Python
- FastApi
- Sqlite3

## 🚀 Features
What you can do:
- Post your music recomendation (name, artist, url, mood, commentary)
- Follow prefered music to remember it
- Sort by following, popularity, mood, etc.
- Report bad posts
- Password encryption
- Login / Register / Log out (in profile)

## 📲 Usage
1. Create virtual environment:
```
python3 -m venv venv
```
2. Enter it:
- Linux / macOS:
```
source venv/bin/activate
```
- Windows:
```
venv\Scripts\activate\
```
3. Install packages:
```
pip install -r requirements.txt
```
4. Run the server:
```
uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

## ❓ FAQ
> **Q: What does the Git version means?**
A: Format: `day.major.minor`, for example: `3.2.1` — 3th day working on project, second big update, first fix.

## 🐞 Known Bugs
We currently working on:
- [x] Duplicates after sort

## 📬 Contact
* [GitHub - equa-tory](https://github.comequa-tory/)
* Telegram - @equa_tory
* [Mail](mailto:thesuspect9980@gmail.com)