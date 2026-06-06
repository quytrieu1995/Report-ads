"""Cấu hình engine SQLAlchemy — mặc định SQLite, có thể đổi qua DATABASE_URL."""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Thư mục data/ nằm cùng cấp với backend/
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE = f"sqlite:///{DATA_DIR / 'datahub.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE)

# SQLite cần check_same_thread=False cho FastAPI
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency FastAPI — yield session và đóng sau request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
