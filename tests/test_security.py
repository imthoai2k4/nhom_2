"""
tests/test_security.py — Hash mật khẩu, legacy migration và rate limiter.
"""
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import models
from app.auth import verify_credentials
from app.security import (
    RateLimiter,
    hash_password,
    is_legacy_hash,
    verify_password,
)


def test_TC_SEC_001_hash_and_verify():
    stored = hash_password("matkhau123")
    assert stored.startswith("pbkdf2_sha256$")
    assert stored != "matkhau123"
    assert verify_password("matkhau123", stored) is True
    assert verify_password("sai", stored) is False


def test_TC_SEC_002_legacy_plaintext_verify():
    assert is_legacy_hash("admin123") is True
    assert verify_password("admin123", "admin123") is True
    assert verify_password("wrong", "admin123") is False


def test_TC_SEC_003_verify_credentials_migrates_plaintext():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(models.User(
        id=1, username="legacy", password="plain123",
        full_name="Legacy", role="admin",
    ))
    db.commit()

    user = verify_credentials("legacy", "plain123", db)
    assert user.id == 1
    db.refresh(user)
    assert user.password.startswith("pbkdf2_sha256$")
    assert verify_password("plain123", user.password) is True
    db.close()


def test_TC_SEC_004_rate_limiter_blocks_third_call():
    limiter = RateLimiter(limit=2, window_seconds=60)
    limiter.check("u1")
    limiter.check("u1")
    with pytest.raises(HTTPException) as exc:
        limiter.check("u1")
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_TC_SEC_005_rate_limiter_isolated_by_key():
    limiter = RateLimiter(limit=1, window_seconds=60)
    limiter.check("a")
    limiter.check("b")
