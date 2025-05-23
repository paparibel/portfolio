# === Krok 1: Szkielet projektu (Python - FastAPI backend) ===
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta

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
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
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


# === FRONTEND ===
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return FileResponse("frontend/index.html")



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


# === JWT konfiguracja ===
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "tajnysekret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# === Baza users.db ===
USERS_DB_FILE = "users.db"

# === Hashowanie hasła ===
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# === Schemat tokena ===
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login-jwt")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_from_db(username: str):
    with sqlite3.connect(USERS_DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT username, hashed_password FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        if row:
            return {"username": row[0], "hashed_password": row[1]}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Nieautoryzowany",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_from_db(username)
    if user is None:
        raise credentials_exception
    return User(username=user["username"])

# === ENDPOINT: REJESTRACJA ===
@app.post("/api/register")
def register(username: str = Form(...), password: str = Form(...)):
    hashed_pw = get_password_hash(password)
    created_at = datetime.utcnow().isoformat()
    try:
        with sqlite3.connect(USERS_DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, hashed_password, created_at) VALUES (?, ?, ?)",
                      (username, hashed_pw, created_at))
            conn.commit()
        return {"status": "registered"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Użytkownik już istnieje")

# === ENDPOINT: LOGOWANIE JWT ===
@app.post("/api/login-jwt", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_from_db(form_data.username)

    if not user:
        raise HTTPException(status_code=401, detail="Błędne dane logowania")

    # SPRAWDZAMY ADMINA PRZEZ .env
    if user["username"] == ADMIN_USERNAME:
        if form_data.password != ADMIN_PASSWORD:
            raise HTTPException(status_code=403, detail="Hasło administratora nieprawidłowe")
    else:
        # DLA POZOSTAŁYCH SPRAWDZAMY HASH Z DB
        if not verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Błędne dane logowania")

    access_token = create_access_token(data={"sub": user["username"]},
                                       expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

# === PRZYKŁADOWY ENDPOINT: tylko dla zalogowanych ===
@app.get("/api/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"logged_in_as": current_user.username}

@app.get("/api/messages")
def get_messages(current_user: User = Depends(get_current_user)):
    if current_user.username != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Dostęp tylko dla administratora")

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, email, message FROM contact_messages")
        rows = c.fetchall()

    return [
        {"id": row[0], "name": row[1], "email": row[2], "message": row[3]}
        for row in rows
    ]

@app.delete("/api/messages/{id}")
def delete_message(id: int, current_user: User = Depends(get_current_user)):
    if current_user.username != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Dostęp tylko dla administratora")

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM contact_messages WHERE id = ?", (id,))
        conn.commit()

    return {"status": "deleted"}

@app.get("/register")
def register_page():
    return FileResponse(os.path.join("frontend", "register.html"))
