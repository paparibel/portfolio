# === Krok 1: Szkielet projektu (Python - FastAPI backend) ===

from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List
import json
import os
import sqlite3
from dotenv import load_dotenv
load_dotenv()


# === Ładowanie hasła z .env ===
load_dotenv()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# === BAZA DANYCH ===
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

# === ZAPIS/ODCZYT wiadomości (JSON backup, nie używany już aktywnie) ===
DATA_FILE = "messages.json"
def load_messages():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_messages(messages):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

# === CORS (opcjonalnie) ===
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

# === ENDPOINTY API ===
@app.get("/api/projects", response_model=List[Project])
def get_projects():
    return projects

@app.get("/api/projects/{project_id}", response_model=Project)
def get_project(project_id: int):
    for proj in projects:
        if proj.id == project_id:
            return proj
    return {"error": "Project not found"}

@app.get("/api/about")
def about():
    return {
        "name": "Michał",
        "role": "Python Developer",
        "bio": """Python Developer z ponad 5-letnim doświadczeniem w automatyzacji procesów, analizie danych i wdrażaniu
rozwiązań IT w branży przemysłowej i transportowej.
Specjalizuję się w tworzeniu aplikacji i skryptów automatyzujących pracę biurową, analityczną i inżynieryjną.
Pracuję z Pythonem, SQL, OpenAI API, a także uczę się technologii webowych (Java + Spring Boot).
Świetnie odnajduję się w projektach, w których można zwiększyć efektywność i jakość działania dzięki technologii.
Jestem gotowy na współpracę w modelu B2B – preferuję zdalne zlecenia i projekty z realnym wpływem na produkt.
Python Automation Scripts (GitHub, 2025)
Publiczna kolekcja skryptów automatyzujących – organizacja plików, obsługa CSV, integracje z API, praca na
bazach danych. Repozytorium stworzone z myślą o rekruterach i prezentacji umiejętności Pythona.
github.com/paparibel/python-automation-scripts
"""
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

# === FRONTEND ===
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return FileResponse(os.path.join("frontend", "index.html"))


# Pliki statyczne (CSS, JS itp.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Login
@app.get("/login")
def login_page():
    return FileResponse(os.path.join("frontend", "login.html"))

@app.post("/login")
async def login(password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin", status_code=302)
        response.set_cookie("is_admin", "true")
        return response
    return RedirectResponse(url="/login", status_code=302)


# Admin – zabezpieczony
@app.get("/admin")
def serve_admin(request: Request):
    if request.cookies.get("is_admin") != "true":
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join("frontend", "admin.html"))



