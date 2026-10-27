"""app/routers/auth.py — Login / logout / me"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import verify_credentials, get_current_user
from app.schemas import LoginRequest, LoginResponse, UserOut
from app import models

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = verify_credentials(body.username, body.password, db)
        return LoginResponse(
            success=True, role=user.role,
            username=user.username,
            household_id=user.household_id,
            message=f"Đăng nhập thành công với quyền {user.role}",
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Tên đăng nhập hoặc mật khẩu không đúng")


@router.post("/logout")
def logout():
    return {"message": "Đăng xuất thành công"}


@router.get("/me", response_model=UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
