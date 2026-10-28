"""
app/auth.py
Phân quyền đơn giản (demo) — không dùng JWT.
Dùng session cookie hoặc header X-Username / X-Password để xác thực.

Roles:
  admin → toàn quyền CRUD, xem báo cáo, dùng AI
  user  → chỉ xem thông tin hộ của mình, xem hóa đơn, dùng AI phân tích
"""
import os
from datetime import datetime
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.database import get_db
from app import models
from app.security import hash_password, is_legacy_hash, verify_password

load_dotenv()

# Tài khoản admin mặc định từ .env (demo)
_ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin123")


def verify_credentials(username: str, password: str, db: Session) -> models.User:
    """
    Xác thực username/password.
    Ưu tiên: kiểm tra bảng users trong DB; fallback về admin mặc định từ .env.
    """
    u_norm = (username or "").strip()
    p_norm = (password or "").strip()

    # Tìm trong DB trước (hỗ trợ không phân biệt hoa thường cho username)
    user = db.query(models.User).filter(
        models.User.username.ilike(u_norm)
    ).first()

    if user and user.is_active and verify_password(p_norm, user.password):
        # Tự nâng cấp mật khẩu plaintext cũ lên PBKDF2 khi đăng nhập.
        if is_legacy_hash(user.password):
            try:
                user.password = hash_password(p_norm)
                db.commit()
            except Exception:
                # DB read-only/locked: vẫn cho đăng nhập, lần sau thử lại.
                db.rollback()
        return user

    # Fallback: admin mặc định từ .env
    if u_norm.lower() == _ADMIN_USER.lower() and p_norm == _ADMIN_PASS:
        # Trả về đối tượng giả không lưu DB
        fake_admin = models.User(
            id=0,
            username=_ADMIN_USER,
            password=_ADMIN_PASS,
            role="admin",
            full_name="Quản trị viên",
            household_id=None,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return fake_admin

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tên đăng nhập hoặc mật khẩu không đúng",
    )


def get_current_user(
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
    x_password: Optional[str] = Header(default=None, alias="X-Password"),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Dependency: lấy thông tin user hiện tại từ request headers.
    Frontend gửi header X-Username và X-Password theo mỗi request.

    Thiếu header → 401 (không còn fallback admin mặc định, tránh lộ dữ liệu
    khi frontend chưa đăng nhập).

    Sử dụng trong router:
        @router.get("/...")
        def endpoint(current_user = Depends(get_current_user)):
            ...
    """
    if not x_username or not x_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập để tiếp tục",
            headers={"WWW-Authenticate": "X-Username"},
        )
    return verify_credentials(x_username, x_password, db)


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency: yêu cầu quyền admin.
    Dùng cho các endpoint nhạy cảm: xóa dữ liệu, thêm user,...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ quản trị viên mới có quyền thực hiện thao tác này",
        )
    return current_user


def require_household_scope(current_user: models.User) -> int:
    """User phải được gắn hộ; nếu không → 403 (tránh coi như admin)."""
    if current_user.role != "admin" and current_user.household_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản chưa được gắn hộ/phòng. Vui lòng liên hệ quản trị viên.",
        )
    return current_user.household_id


def get_household_filter(current_user: models.User) -> int | None:
    """
    Trả về household_id nếu user role=user (chỉ xem hộ của mình).
    Trả về None nếu admin (xem tất cả).
    User chưa được gắn hộ → 403, tránh bị coi như admin.
    """
    if current_user.role == "admin":
        return None
    return require_household_scope(current_user)
