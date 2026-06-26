from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

DELETE_DIRS = [
    ROOT / "__pycache__",
    ROOT / "uploads",
    ROOT / "backend" / "__pycache__",
    ROOT / "backend" / "database" / "__pycache__",
    ROOT / "backend" / "face_recognition" / "__pycache__",
    ROOT / "backend" / "services" / "__pycache__",
    ROOT / "frontend" / "__pycache__",
    ROOT / "frontend" / "modules" / "__pycache__",
    ROOT / "frontend" / "utils" / "__pycache__",
]

for folder in DELETE_DIRS:
    if folder.exists():
        shutil.rmtree(folder)
        print(f"Deleted folder: {folder}")

for pyc_file in ROOT.rglob("*.pyc"):
    pyc_file.unlink()
    print(f"Deleted pyc: {pyc_file}")

for model_zip in (ROOT / "data" / "insightface" / "models").glob("*.zip"):
    model_zip.unlink()
    print(f"Deleted model zip: {model_zip}")

env_file = ROOT / ".env"
if env_file.exists():
    env_file.unlink()
    print("Deleted .env file")

print("Submission cleanup completed.")