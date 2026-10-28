"""
app/routers/ai_analysis.py — API phân tích AI tiêu thụ điện nước

Endpoints:
  POST /api/ai/analyze   — Phân tích tiêu thụ cho 1 hộ (AI chuẩn OpenAI)
"""
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, get_household_filter
from app import models
from app.services.ai_service import analyze_consumption_detailed
from app.security import ai_rate_limiter

router = APIRouter()

# Cache kết quả AI theo (household_id, months) để tránh 429 khi demo.
_CACHE_TTL = int(os.getenv("AI_CACHE_TTL", "300"))
_CACHE: dict[tuple[int, int], tuple[float, dict]] = {}
_CACHE_LOCK = threading.Lock()


def clear_ai_cache() -> None:
    """Xóa cache AI (dùng cho test hoặc khi dữ liệu thay đổi)."""
    with _CACHE_LOCK:
        _CACHE.clear()


class AIAnalyzeRequest(BaseModel):
    household_id: int
    months: int = Field(6, ge=1, le=12, description="Số kỳ gần nhất, 1–12")


class AIAnalyzeResponse(BaseModel):
    household_id: int
    household_name: str
    analysis: str
    data_points: int  # Số kỳ đã phân tích
    source: str = "internal"      # "ai" nếu gọi model, "internal" nếu fallback
    model: str = ""
    finish_reason: str = ""
    truncated: bool = False
    period_from: Optional[str] = None
    period_to: Optional[str] = None
    prompt_version: str = ""
    analyzed_at: str = ""
    cached: bool = False


@router.post("/analyze", response_model=AIAnalyzeResponse)
async def analyze_household(
    body: AIAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Phân tích tiêu thụ điện nước của hộ bằng AI (chuẩn OpenAI).
    - Admin: phân tích bất kỳ hộ nào
    - User: chỉ phân tích hộ của mình
    """
    ai_rate_limiter.check(f"user:{current_user.id or current_user.username}")

    # Kiểm tra quyền truy cập
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None and body.household_id != hh_filter:
        raise HTTPException(403, "Bạn chỉ có thể phân tích hộ của mình")

    # Lấy thông tin hộ
    hh = db.query(models.Household).filter(
        models.Household.id == body.household_id
    ).first()
    if not hh:
        raise HTTPException(404, "Không tìm thấy hộ/phòng")

    # Cache theo hộ + số kỳ
    cache_key = (hh.id, body.months)
    now = time.time()
    with _CACHE_LOCK:
        cached_entry = _CACHE.get(cache_key)
        if cached_entry and now - cached_entry[0] < _CACHE_TTL:
            cached_data = dict(cached_entry[1])
            cached_data["cached"] = True
            return AIAnalyzeResponse(**cached_data)

    # Lấy N kỳ gần nhất (không phụ thuộc số đồng hồ của hộ).
    period_rows = (
        db.query(models.Reading.period)
        .join(models.Meter)
        .filter(models.Meter.household_id == body.household_id)
        .distinct()
        .order_by(models.Reading.period.desc())
        .limit(body.months)
        .all()
    )
    periods = [p[0] for p in period_rows]  # DESC: mới nhất trước

    if periods:
        readings_rows = (
            db.query(models.Reading, models.Meter)
            .join(models.Meter)
            .filter(
                models.Meter.household_id == body.household_id,
                models.Reading.period.in_(periods),
            )
            .order_by(models.Reading.period.asc(), models.Meter.meter_type)
            .all()
        )
    else:
        readings_rows = []

    readings = [
        {
            "period": r.period,
            "meter_type": m.meter_type,
            "consumption": float(r.consumption),
            "unit": m.unit,
        }
        for r, m in readings_rows
    ]

    # Hóa đơn trong cùng cửa sổ kỳ (nếu có)
    invoice_query = db.query(models.Invoice).filter(
        models.Invoice.household_id == body.household_id
    )
    if periods:
        invoice_query = invoice_query.filter(models.Invoice.period.in_(periods))
    invoices_rows = (
        invoice_query.order_by(models.Invoice.period.desc())
        .limit(body.months)
        .all()
    )

    invoices = [
        {
            "period": inv.period,
            "electricity_amount": inv.electricity_amount,
            "water_amount": inv.water_amount,
            "total_amount": inv.total_amount,
            "status": inv.status,
        }
        for inv in invoices_rows
    ]

    # Cảnh báo nghiệp vụ chưa xử lý để AI đối chiếu
    alerts_rows = (
        db.query(models.ConsumptionAlert)
        .filter(
            models.ConsumptionAlert.household_id == body.household_id,
            models.ConsumptionAlert.is_resolved == False,
        )
        .order_by(models.ConsumptionAlert.created_at.desc())
        .limit(3)
        .all()
    )
    alerts = [
        {
            "period": a.period,
            "message": a.message,
            "percent_change": float(a.percent_change) if a.percent_change is not None else None,
        }
        for a in alerts_rows
    ]

    # Gọi AI phân tích
    analysis = await analyze_consumption_detailed(
        household_name=hh.name,
        readings=readings,
        invoices=invoices,
        alerts=alerts,
    )

    response = AIAnalyzeResponse(
        household_id=hh.id,
        household_name=hh.name,
        analysis=analysis.text,
        data_points=len(periods),
        source=analysis.source,
        model=analysis.model,
        finish_reason=analysis.finish_reason,
        truncated=analysis.truncated,
        period_from=periods[-1] if periods else None,
        period_to=periods[0] if periods else None,
        prompt_version=analysis.prompt_version,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        cached=False,
    )

    with _CACHE_LOCK:
        _CACHE[cache_key] = (time.time(), response.model_dump())

    return response
