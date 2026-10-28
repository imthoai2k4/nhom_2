"""
app/security.py — Hash mật khẩu, rate limit và tiện ích bảo mật.

- Password: PBKDF2-SHA256 (chuẩn thư viện, không cần dependency ngoài).
- Legacy: vẫn xác thực được mật khẩu plaintext cũ và tự nâng cấp khi đăng nhập.
- RateLimiter: giới hạn theo key (user/IP) trong cửa sổ thời gian.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time

from fastapi import HTTPException, status

_PBKDF2_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    """Tạo hash PBKDF2-SHA256 có salt ngẫu nhiên."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def is_legacy_hash(stored: str) -> bool:
    """True nếu mật khẩu đang lưu dạng plaintext cũ."""
    return not str(stored or "").startswith("pbkdf2_sha256$")


def verify_password(password: str, stored: str) -> bool:
    """So khớp mật khẩu với hash PBKDF2 hoặc plaintext legacy."""
    if not stored:
        return False

    if not is_legacy_hash(stored):
        try:
            _, iterations, salt, expected = str(stored).split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            )
            return hmac.compare_digest(digest.hex(), expected)
        except (TypeError, ValueError):
            return False

    # Legacy plaintext (demo cũ) — vẫn cho đăng nhập, sẽ được rehash sau.
    return hmac.compare_digest(str(stored), str(password))


class RateLimiter:
    """Rate limiter in-memory, đủ dùng cho demo một tiến trình."""

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = max(1, int(limit))
        self.window = max(1, int(window_seconds))
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.time()
        with self._lock:
            bucket = [t for t in self._hits.get(key, []) if now - t < self.window]
            if len(bucket) >= self.limit:
                retry_after = max(1, int(self.window - (now - bucket[0])) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)
            self._hits[key] = bucket


ai_rate_limiter = RateLimiter(int(os.getenv("AI_RATE_LIMIT", "30")), 60)
chat_rate_limiter = RateLimiter(int(os.getenv("CHAT_RATE_LIMIT", "60")), 60)
