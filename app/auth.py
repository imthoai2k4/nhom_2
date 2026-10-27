"""
app/auth.py
Phân quyền đơn giản (demo) — không dùng JWT.
Dùng session cookie hoặc header X-Username / X-Password để xác thực.

Roles:
  admin → toàn quyền CRUD, xem báo cáo, dùng AI
  user  → chỉ xem thông tin hộ của mình, xem hóa đơn, dùng AI phân tích
"""
import os
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.database import get_db
from app import models

load_dotenv()

# Tài khoản admin mặc định từ .env (demo)
_ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin123")


def verify_credentials(username: str, password: str, db: Session) -> models.User:
    """
    Xác thực username/password.
    Ưu tiên: kiểm tra bảng users trong DB; fallback về admin mặc định từ .env.
    """
    # Tìm trong DB trước
    user = db.query(models.User).filter(
        models.User.username == username
    ).first()

    if user and user.password == password:
        return user

    # Fallback: admin mặc định
    if username == _ADMIN_USER and password == _ADMIN_PASS:
        # Trả về đối tượng giả không lưu DB
        fake_admin = models.User(
            id=0,
            username=_ADMIN_USER,
            password=_ADMIN_PASS,
            role="admin",
            full_name="Quản trị viên",
            household_id=None,
        )
        return fake_admin

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tên đăng nhập hoặc mật khẩu không đúng",
    )


def get_current_user(
    x_username: str = Header(default="admin", alias="X-Username"),
    x_password: str = Header(default="admin123", alias="X-Password"),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Dependency: lấy thông tin user hiện tại từ request headers.
    Frontend gửi header X-Username và X-Password theo mỗi request.

    Sử dụng trong router:
        @router.get("/...")
        def endpoint(current_user = Depends(get_current_user)):
            ...
    """
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


def get_household_filter(current_user: models.User) -> int | None:
    """
    Trả về household_id nếu user role=user (chỉ xem hộ của mình).
    Trả về None nếu admin (xem tất cả).
    """
    if current_user.role == "admin":
        return None
    return current_user.household_id
