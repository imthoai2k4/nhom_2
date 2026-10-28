"""
app/routers/ai_analysis.py — API phân tích AI tiêu thụ điện nước

Endpoints:
  POST /api/ai/analyze   — Phân tích tiêu thụ cho 1 hộ (AI chuẩn OpenAI)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.auth import get_current_user, get_household_filter
from app import models
from app.services.ai_service import analyze_consumption_detailed

router = APIRouter()


class AIAnalyzeRequest(BaseModel):
    household_id: int
    months: int = 6  # Số tháng lịch sử để phân tích


class AIAnalyzeResponse(BaseModel):
    household_id: int
    household_name: str
    analysis: str
    data_points: int  # Số điểm dữ liệu đã phân tích
    source: str = "internal"      # "ai" nếu gọi model, "internal" nếu fallback
    model: str = ""
    finish_reason: str = ""
    truncated: bool = False


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

    # Lấy lịch sử tiêu thụ
    readings_rows = (
        db.query(models.Reading, models.Meter)
        .join(models.Meter)
        .filter(models.Meter.household_id == body.household_id)
        .order_by(models.Reading.period.desc())
        .limit(body.months * 2)
        .all()
    )

    readings = [
        {
            "period": r.period,
            "meter_type": m.meter_type,
            "consumption": float(r.consumption),
            "unit": m.unit,
        }
        for r, m in readings_rows
    ]

    # Lấy hóa đơn
    invoices_rows = (
        db.query(models.Invoice)
        .filter(models.Invoice.household_id == body.household_id)
        .order_by(models.Invoice.period.desc())
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

    # Gọi AI phân tích
    analysis = await analyze_consumption_detailed(
        household_name=hh.name,
        readings=readings,
        invoices=invoices,
    )

    return AIAnalyzeResponse(
        household_id=hh.id,
        household_name=hh.name,
        analysis=analysis.text,
        data_points=len(readings),
        source=analysis.source,
        model=analysis.model,
        finish_reason=analysis.finish_reason,
        truncated=analysis.truncated,
    )
