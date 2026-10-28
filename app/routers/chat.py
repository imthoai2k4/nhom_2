"""
app/routers/chat.py — API cho cửa sổ chat AI.

Endpoints:
  GET    /api/chat/sessions                 — danh sách phiên của user hiện tại
  POST   /api/chat/sessions                 — tạo phiên mới
  GET    /api/chat/sessions/{sid}           — chi tiết phiên + messages
  DELETE /api/chat/sessions/{sid}           — xóa phiên
  POST   /api/chat/message                  — gửi 1 message, nhận reply
"""
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app import models
from app.services.chat_service import process_message, detect_intent
from app.security import chat_rate_limiter
from app.schemas import (
    ChatSessionOut, ChatMessageOut, ChatRequest, ChatResponse,
)


router = APIRouter()


# ── Sessions ────────────────────────────────────────────────────────────────
@router.get("/sessions", response_model=List[ChatSessionOut])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.ChatSession)
    if current_user.role != "admin" and current_user.id:
        q = q.filter(models.ChatSession.user_id == current_user.id)
    return q.order_by(models.ChatSession.updated_at.desc()).limit(50).all()


@router.post("/sessions", response_model=ChatSessionOut, status_code=201)
def create_session(
    title: Optional[str] = "Hội thoại mới",
    context_hh: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # user thường chỉ ghim được hộ của mình
    if current_user.role != "admin" and context_hh and context_hh != current_user.household_id:
        raise HTTPException(403, "Bạn không thể ghim hộ không thuộc quyền của mình")
    s = models.ChatSession(
        user_id=current_user.id or 0,
        title=title or "Hội thoại mới",
        context_hh=context_hh,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("/sessions/{sid}")
def get_session(
    sid: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    s = db.query(models.ChatSession).filter(models.ChatSession.id == sid).first()
    if not s:
        raise HTTPException(404, "Không tìm thấy phiên chat")
    if current_user.role != "admin" and s.user_id != current_user.id:
        raise HTTPException(403, "Bạn không có quyền xem phiên chat này")
    msgs = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == sid)
        .order_by(models.ChatMessage.created_at)
        .all()
    )
    return {
        "session": {
            "id": s.id,
            "user_id": s.user_id,
            "title": s.title,
            "context_hh": s.context_hh,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        },
        "messages": [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "intent": m.intent,
                "ref_data": m.ref_data,
                "created_at": m.created_at,
            }
            for m in msgs
        ],
    }


@router.delete("/sessions/{sid}")
def delete_session(
    sid: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    s = db.query(models.ChatSession).filter(models.ChatSession.id == sid).first()
    if not s:
        raise HTTPException(404, "Không tìm thấy phiên chat")
    if current_user.role != "admin" and s.user_id != current_user.id:
        raise HTTPException(403, "Bạn không có quyền xóa phiên chat này")
    db.delete(s)
    db.commit()
    return {"message": "Đã xóa phiên chat"}


@router.put("/sessions/{sid}/title")
def rename_session(
    sid: int,
    title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    s = db.query(models.ChatSession).filter(models.ChatSession.id == sid).first()
    if not s:
        raise HTTPException(404, "Không tìm thấy phiên chat")
    if current_user.role != "admin" and s.user_id != current_user.id:
        raise HTTPException(403, "Không có quyền")
    s.title = title.strip() or "Hội thoại"
    db.commit()
    db.refresh(s)
    return {"id": s.id, "title": s.title}


# ── Message ─────────────────────────────────────────────────────────────────
@router.post("/message", response_model=ChatResponse)
def send_message(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Gửi 1 message, nhận reply. Tự tạo session nếu chưa có."""
    chat_rate_limiter.check(f"user:{current_user.id or current_user.username}")

    if not body.message or not body.message.strip():
        raise HTTPException(400, "Tin nhắn trống")

    # Lấy / tạo session
    if body.session_id:
        session = db.query(models.ChatSession).filter(
            models.ChatSession.id == body.session_id
        ).first()
        if not session:
            raise HTTPException(404, "Phiên chat không tồn tại")
        if current_user.role != "admin" and session.user_id != current_user.id:
            raise HTTPException(403, "Không có quyền gửi vào phiên này")
    else:
        session = models.ChatSession(
            user_id=current_user.id or 0,
            title=body.message[:60].strip() or "Hội thoại mới",
            context_hh=body.context_hh,
        )
        db.add(session)
        db.flush()

    # ghim context nếu có
    if body.context_hh and not session.context_hh:
        if current_user.role != "admin" and body.context_hh != current_user.household_id:
            raise HTTPException(403, "Không thể ghim hộ không thuộc quyền")
        session.context_hh = body.context_hh

    # lưu tin nhắn user
    user_msg = models.ChatMessage(
        session_id=session.id,
        role="user",
        content=body.message.strip(),
    )
    db.add(user_msg)
    db.flush()

    # detect intent và xử lý
    intent = detect_intent(body.message)
    reply, intent, ref_data = process_message(
        db=db,
        user=current_user,
        text=body.message,
        context_hh=session.context_hh,
    )

    # lưu tin nhắn assistant
    ref_json = json.dumps(ref_data, ensure_ascii=False, default=str) if ref_data else None
    asst_msg = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply,
        intent=intent,
        ref_data=ref_json,
    )
    db.add(asst_msg)

    # tự cập nhật tiêu đề session từ câu đầu tiên
    if session.title == "Hội thoại mới":
        session.title = body.message[:60].strip() or "Hội thoại"

    db.commit()
    db.refresh(user_msg)
    db.refresh(asst_msg)
    db.refresh(session)

    ref_data_dict = None
    if ref_json:
        try:
            ref_data_dict = json.loads(ref_json)
        except Exception:
            ref_data_dict = None

    return ChatResponse(
        session_id=session.id,
        user_message=ChatMessageOut.model_validate(user_msg),
        assistant_message=ChatMessageOut.model_validate(asst_msg),
        intent=intent,
        ref_data=ref_data_dict,
    )
