"""
app/database.py
Kết nối SQLite, tạo bảng và cung cấp session dependency cho FastAPI.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./utility_mgmt.db")

# Resolve relative SQLite paths from the project root, not the process CWD.
# This keeps API and frontend launch methods attached to the same database.
_db_url = make_url(DATABASE_URL)
if _db_url.drivername.startswith("sqlite") and _db_url.database not in (None, ":memory:"):
    _db_path = Path(_db_url.database)
    if not _db_path.is_absolute():
        _db_url = _db_url.set(database=str((Path(__file__).resolve().parent.parent / _db_path).resolve()))

# SQLite cần check_same_thread=False để dùng với FastAPI (async context)
engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False},
    echo=False,  # Đặt True để xem SQL queries khi debug
)


if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):
        """Bật FK + WAL để đọc/ghi ổn định hơn khi nhiều request."""
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
        except Exception:
            # Môi trường read-only (test/sandbox) vẫn cho phép đọc.
            pass

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
