"""app/routers/readings.py — Nhập/sửa/tra cứu chỉ số (phân quyền admin/user)"""
from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_admin, get_household_filter
from app.schemas import ReadingCreate, ReadingOut
from app import models
from app.services.alert_service import check_and_create_alert

router = APIRouter()


@router.get("", response_model=list[ReadingOut])
def list_readings(
    meter_id: Optional[int] = Query(None),
    household_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Reading).join(models.Meter)
    # User chỉ thấy chỉ số hộ mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None:
        q = q.filter(models.Meter.household_id == hh_filter)
    elif household_id:
        q = q.filter(models.Meter.household_id == household_id)
    if meter_id:
        q = q.filter(models.Reading.meter_id == meter_id)
    if period:
        q = q.filter(models.Reading.period == period)
    return q.order_by(models.Reading.period.desc()).all()


@router.get("/last/{meter_id}", response_model=ReadingOut)
def get_last_reading(
    meter_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Chỉ số mới nhất của đồng hồ — dùng để pre-fill form nhập."""
    meter = db.query(models.Meter).filter(models.Meter.id == meter_id).first()
    if not meter:
        raise HTTPException(404, "Không tìm thấy đồng hồ")
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None and meter.household_id != hh_filter:
        raise HTTPException(403, "Bạn không có quyền xem chỉ số của đồng hồ này")

    r = (
        db.query(models.Reading)
        .filter(models.Reading.meter_id == meter_id)
        .order_by(models.Reading.period.desc())
        .first()
    )
    if not r:
        raise HTTPException(404, "Chưa có chỉ số cho đồng hồ này")
    return r


@router.get("/history/{household_id}")
def get_history(
    household_id: int,
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # User chỉ xem lịch sử hộ mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None and household_id != hh_filter:
        from fastapi import HTTPException as HE
        raise HE(status_code=403, detail="Bạn không có quyền xem lịch sử hộ này")
    """Lịch sử tiêu thụ theo hộ — dùng cho AI input."""
    rows = (
        db.query(models.Reading, models.Meter)
        .join(models.Meter)
        .filter(models.Meter.household_id == household_id)
        .order_by(models.Reading.period.desc())
        .limit(months * 2)  # *2 vì có điện + nước
        .all()
    )
    return [
        {
            "period": r.period,
            "meter_type": m.meter_type,
            "consumption": float(r.consumption),
            "unit": m.unit,
        }
        for r, m in rows
    ]


@router.get("/{rid}", response_model=ReadingOut)
def get_reading(
    rid: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    r = db.query(models.Reading).filter(models.Reading.id == rid).first()
    if not r:
        raise HTTPException(404, "Không tìm thấy chỉ số")
    meter = db.query(models.Meter).filter(models.Meter.id == r.meter_id).first()
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None and meter and meter.household_id != hh_filter:
        raise HTTPException(403, "Bạn không có quyền xem chỉ số này")
    return r


@router.post("", response_model=ReadingOut, status_code=201)
def create_reading(
    body: ReadingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    # Kiểm tra đồng hồ tồn tại
    meter = db.query(models.Meter).filter(models.Meter.id == body.meter_id).first()
    if not meter:
        raise HTTPException(404, "Đồng hồ không tồn tại")

    # Kiểm tra trùng kỳ
    dup = db.query(models.Reading).filter(
        models.Reading.meter_id == body.meter_id,
        models.Reading.period == body.period,
    ).first()
    if dup:
        raise HTTPException(409, f"Đã có chỉ số cho đồng hồ này trong kỳ {body.period}")

    consumption = body.curr_reading - body.prev_reading
    r = models.Reading(
        meter_id=body.meter_id,
        period=body.period,
        prev_reading=body.prev_reading,
        curr_reading=body.curr_reading,
        consumption=consumption,
        recorded_by=current_user.id,
    )
    db.add(r)
    db.flush()

    # Kiểm tra spike (không chặn nếu lỗi)
    try:
        check_and_create_alert(db, r)
    except Exception:
        pass

    db.commit()
    db.refresh(r)
    return r


@router.put("/{rid}", response_model=ReadingOut)
def update_reading(
    rid: int,
    curr_reading: Decimal,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    r = db.query(models.Reading).filter(models.Reading.id == rid).first()
    if not r:
        raise HTTPException(404, "Không tìm thấy chỉ số")

    # Không cho sửa nếu đã có hóa đơn
    has_invoice = db.query(models.InvoiceItem).filter(
        models.InvoiceItem.reading_id == rid
    ).first()
    if has_invoice:
        raise HTTPException(409, "Chỉ số này đã được tính vào hóa đơn, không thể sửa")

    if curr_reading < r.prev_reading:
        raise HTTPException(422, "Chỉ số mới không được nhỏ hơn chỉ số kỳ trước")
    if curr_reading < 0:
        raise HTTPException(422, "Chỉ số không được âm")

    r.curr_reading = curr_reading
    r.consumption = curr_reading - r.prev_reading
    db.commit()
    db.refresh(r)
    return r
