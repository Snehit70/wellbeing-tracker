"""SQLAlchemy database setup for Flask backend"""
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path

# Use the new db object from Flask-SQLAlchemy
db = SQLAlchemy()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "wellbeing.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"
