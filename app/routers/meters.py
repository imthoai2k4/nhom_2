"""app/routers/meters.py — CRUD đồng hồ điện/nước"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_admin
from app.schemas import MeterCreate, MeterUpdate, MeterOut
from app import models

router = APIRouter()


@router.get("", response_model=list[MeterOut])
def list_meters(
    household_id: Optional[int] = Query(None),
    meter_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(models.Meter)
    if household_id:
        q = q.filter(models.Meter.household_id == household_id)
    if meter_type:
        q = q.filter(models.Meter.meter_type == meter_type)
    return q.order_by(models.Meter.household_id, models.Meter.meter_type).all()


@router.get("/{mid}", response_model=MeterOut)
def get_meter(mid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    m = db.query(models.Meter).filter(models.Meter.id == mid).first()
    if not m:
        raise HTTPException(404, "Không tìm thấy đồng hồ")
    return m


@router.post("", response_model=MeterOut, status_code=201)
def create_meter(body: MeterCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if not db.query(models.Household).filter(models.Household.id == body.household_id).first():
        raise HTTPException(404, "Hộ/phòng không tồn tại")
    existing = db.query(models.Meter).filter(models.Meter.meter_number == body.meter_number).first()
    if existing:
        raise HTTPException(409, f"Số đồng hồ '{body.meter_number}' đã tồn tại")
    m = models.Meter(**body.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/{mid}", response_model=MeterOut)
def update_meter(mid: int, body: MeterUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    m = db.query(models.Meter).filter(models.Meter.id == mid).first()
    if not m:
        raise HTTPException(404, "Không tìm thấy đồng hồ")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{mid}")
def delete_meter(mid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    m = db.query(models.Meter).filter(models.Meter.id == mid).first()
    if not m:
        raise HTTPException(404, "Không tìm thấy đồng hồ")
    if db.query(models.Reading).filter(models.Reading.meter_id == mid).count():
        raise HTTPException(409, "Đồng hồ đã có chỉ số, không thể xóa. Hãy đặt is_active=false.")
    db.delete(m)
    db.commit()
    return {"message": f"Đã xóa đồng hồ '{m.meter_number}'"}
