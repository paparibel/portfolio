# === Krok 1: Szkielet projektu (Python - FastAPI backend) ===

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os
import sqlite3



DB_FILE = "messages.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL
        )
        """)
        conn.commit()


app = FastAPI()
init_db()

# === ZAPIS/ODCZYT wiadomości ===
DATA_FILE = "messages.json"

def load_messages():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_messages(messages):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


# CORS config - front-end moze byc hostowany osobno
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MODELE ===
class Project(BaseModel):
    id: int
    title: str
    description: str
    link: str

class ContactMessage(BaseModel):
    name: str
    email: str
    message: str

# === MOCK DANE ===
projects = [
    Project(id=1, title="Portfolio Website", description="My personal portfolio", link="https://myportfolio.com"),
    Project(id=2, title="Blog App", description="Simple blog engine in Flask", link="https://myblog.com")
]

contact_messages = []


# === ENDPOINTY ===
@app.get("/api/projects", response_model=List[Project])
def get_projects():
    return projects

@app.get("/api/projects/{project_id}", response_model=Project)
def get_project(project_id: int):
    for proj in projects:
        if proj.id == project_id:
            return proj
    return {"error": "Project not found"}

# === Główna informacja ===
@app.get("/api/about")
def about():
    return {
        "name": "Twoje Imię",
        "role": "Python Developer",
        "bio": "Krótka notka o mnie..."
    }
@app.post("/api/contact")
def contact_form(message: ContactMessage):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO contact_messages (name, email, message)
            VALUES (?, ?, ?)
        """, (message.name, message.email, message.message))
        conn.commit()
    return {"status": "received", "message": "Dziękujemy za kontakt!"}

from typing import Union

@app.get("/api/messages")
def get_messages():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, email, message FROM contact_messages")
        rows = c.fetchall()
    return [
        {"id": row[0], "name": row[1], "email": row[2], "message": row[3]}
        for row in rows
    ]

@app.delete("/api/messages/{id}")
def delete_message(id: int):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM contact_messages WHERE id = ?", (id,))
        conn.commit()
    return {"status": "deleted"}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Serwowanie folderu z plikami statycznymi (CSS, JS, img itd.)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Serwowanie index.html przy wejściu na /
@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join("frontend", "index.html"))

@app.get("/admin")
def serve_admin():
    return FileResponse(os.path.join("frontend", "admin.html"))


