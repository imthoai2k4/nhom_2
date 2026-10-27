"""app/routers/prices.py — Quản lý đơn giá"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_admin
from app.schemas import UtilityPriceCreate, UtilityPriceOut
from app import models
from datetime import date

router = APIRouter()


@router.get("", response_model=list[UtilityPriceOut])
def list_prices(
    meter_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(models.UtilityPrice)
    if meter_type:
        q = q.filter(models.UtilityPrice.meter_type == meter_type)
    if active_only:
        today = date.today()
        q = q.filter(
            models.UtilityPrice.effective_from <= today,
            (models.UtilityPrice.effective_to == None) |
            (models.UtilityPrice.effective_to >= today),
        )
    return q.order_by(models.UtilityPrice.meter_type, models.UtilityPrice.tier).all()


@router.post("", response_model=UtilityPriceOut, status_code=201)
def create_price(body: UtilityPriceCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    dup = db.query(models.UtilityPrice).filter(
        models.UtilityPrice.meter_type == body.meter_type,
        models.UtilityPrice.tier == body.tier,
        models.UtilityPrice.effective_from == body.effective_from,
    ).first()
    if dup:
        raise HTTPException(409, "Đã có đơn giá cho bậc và ngày áp dụng này")
    p = models.UtilityPrice(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{pid}", response_model=UtilityPriceOut)
def close_price(pid: int, effective_to: date, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Đóng đơn giá (set effective_to) — không sửa giá, tạo bản ghi mới thay thế."""
    p = db.query(models.UtilityPrice).filter(models.UtilityPrice.id == pid).first()
    if not p:
        raise HTTPException(404, "Không tìm thấy đơn giá")
    p.effective_to = effective_to
    db.commit()
    db.refresh(p)
    return p
