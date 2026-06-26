import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DB_HOST = os.getenv("FACEAI_DB_HOST", "127.0.0.1")

try:
    DB_PORT = int(os.getenv("FACEAI_DB_PORT", "3306"))
except ValueError:
    DB_PORT = 3306

DB_USER = os.getenv("FACEAI_DB_USER", "root")
DB_PASSWORD = os.getenv("FACEAI_DB_PASSWORD", "")
DB_NAME = os.getenv("FACEAI_DB_NAME", "sbsteqgf_faceai")

UPLOAD_DIR = BASE_DIR / "uploads"
USERS_DIR = UPLOAD_DIR / "users"
ADMINS_DIR = UPLOAD_DIR / "admins"
REGISTERED_DIR = UPLOAD_DIR / "registered"
ATTENDANCE_LOGS_DIR = UPLOAD_DIR / "attendance_logs"
ENROLLMENTS_DIR = UPLOAD_DIR / "enrollments"

for folder in [UPLOAD_DIR, USERS_DIR, ADMINS_DIR, REGISTERED_DIR, ATTENDANCE_LOGS_DIR, ENROLLMENTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

YOLO_FACE_MODEL_FILE = DATA_DIR / "yolov8n-face-lindevs.pt"
RECOGNIZER_FILE = DATA_DIR / "face_model.yml"

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is missing. Add it to your .env file.")

if JWT_SECRET_KEY in ["change-this-secret-key", "secret", "123456", "password"]:
    raise RuntimeError("Unsafe JWT_SECRET_KEY. Generate a strong random secret.")

if len(JWT_SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters long.")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
except ValueError:
    ACCESS_TOKEN_EXPIRE_MINUTES = 1440

WEBAUTHN_RP_ID = os.getenv("WEBAUTHN_RP_ID", "localhost")
WEBAUTHN_ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "http://localhost:8501")

# CORS allowed origins for Streamlit frontend.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if origin.strip()
]
CAPTCHA_EXPIRE_MINUTES = 3

COSINE_SIMILARITY_THRESHOLD = 0.55