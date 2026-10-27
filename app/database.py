"""
app/database.py
Kết nối SQLite, tạo bảng và cung cấp session dependency cho FastAPI.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./utility_mgmt.db")

# SQLite cần check_same_thread=False để dùng với FastAPI (async context)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Đặt True để xem SQL queries khi debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Tạo tất cả bảng nếu chưa tồn tại."""
    # Import models để SQLAlchemy nhận diện metadata
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("[DB] Database initialized successfully.")


def get_db():
    """Dependency injection: cấp phát DB session cho mỗi request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
