"""app/routers/invoices.py — Tạo và xem hóa đơn (phân quyền admin/user)"""
from typing import Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_admin, get_household_filter
from app.schemas import InvoiceCreate, InvoiceStatusUpdate, InvoiceOut
from app import models
from app.services.billing import generate_invoice_items, get_active_prices
from app.routers.ai_analysis import clear_ai_cache

router = APIRouter()


def _parse_period_date(period: str) -> date:
    """'2026-07' → date(2026, 7, 1)"""
    y, m = period.split("-")
    return date(int(y), int(m), 1)


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    household_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Invoice)
    # User chỉ thấy hóa đơn hộ mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None:
        q = q.filter(models.Invoice.household_id == hh_filter)
    elif household_id:
        q = q.filter(models.Invoice.household_id == household_id)
    if period:
        q = q.filter(models.Invoice.period == period)
    if status:
        q = q.filter(models.Invoice.status == status)
    return q.order_by(models.Invoice.period.desc()).all()


@router.get("/{iid}", response_model=InvoiceOut)
def get_invoice(
    iid: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    inv = db.query(models.Invoice).filter(models.Invoice.id == iid).first()
    if not inv:
        raise HTTPException(404, "Không tìm thấy hóa đơn")
    # User chỉ xem hóa đơn hộ mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None and inv.household_id != hh_filter:
        raise HTTPException(403, "Bạn không có quyền xem hóa đơn này")
    return inv


def _do_generate(db: Session, household_id: int, period: str, creator_id: int) -> models.Invoice:
    """Core logic tạo hóa đơn từ readings trong kỳ."""
    # Kiểm tra hộ tồn tại
    hh = db.query(models.Household).filter(models.Household.id == household_id).first()
    if not hh:
        raise HTTPException(404, "Hộ/phòng không tồn tại")

    # Kiểm tra hóa đơn đã tồn tại
    dup = db.query(models.Invoice).filter(
        models.Invoice.household_id == household_id,
        models.Invoice.period == period,
    ).first()
    if dup:
        raise HTTPException(409, f"Hóa đơn kỳ {period} đã tồn tại cho hộ này")

    # Lấy meters của hộ
    meters = db.query(models.Meter).filter(
        models.Meter.household_id == household_id,
        models.Meter.is_active == True,
    ).all()

    elec_reading = water_reading = None
    for m in meters:
        r = db.query(models.Reading).filter(
            models.Reading.meter_id == m.id,
            models.Reading.period == period,
        ).first()
        if r and m.meter_type == "electricity":
            elec_reading = r
        elif r and m.meter_type == "water":
            water_reading = r

    if not elec_reading and not water_reading:
        raise HTTPException(400, f"Chưa có chỉ số kỳ {period} cho hộ này")

    period_date = _parse_period_date(period)
    if elec_reading and elec_reading.consumption > 0 and not get_active_prices(db, "electricity", period_date):
        raise HTTPException(400, f"Chưa có đơn giá điện áp dụng cho kỳ {period}")
    if water_reading and water_reading.consumption > 0 and not get_active_prices(db, "water", period_date):
        raise HTTPException(400, f"Chưa có đơn giá nước áp dụng cho kỳ {period}")
    items_data, elec_total, water_total = generate_invoice_items(
        db, elec_reading, water_reading, period_date
    )

    total = elec_total + water_total
    due = period_date.replace(day=15) + timedelta(days=30)  # hạn ~15 tháng sau

    inv = models.Invoice(
        household_id=household_id,
        period=period,
        electricity_amount=elec_total,
        water_amount=water_total,
        total_amount=total,
        status="unpaid",
        due_date=due,
        created_by=creator_id,
    )
    db.add(inv)
    db.flush()

    for it in items_data:
        item = models.InvoiceItem(invoice_id=inv.id, **{
            k: v for k, v in it.items()
        })
        db.add(item)

    return inv


@router.post("/generate", response_model=InvoiceOut, status_code=201)
def generate_invoice(
    body: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    try:
        inv = _do_generate(db, body.household_id, body.period, current_user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Hóa đơn kỳ {body.period} đã tồn tại hoặc dữ liệu liên kết không hợp lệ")
    except Exception:
        db.rollback()
        raise
    clear_ai_cache()
    db.refresh(inv)
    return inv


@router.post("/generate-all")
def generate_all_invoices(
    period: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Tạo hóa đơn cho tất cả hộ active trong kỳ (bỏ qua hộ đã có HD hoặc chưa có chỉ số)."""
    households = db.query(models.Household).filter(
        models.Household.status == "active"
    ).all()

    created, skipped = [], []
    for hh in households:
        try:
            with db.begin_nested():
                inv = _do_generate(db, hh.id, period, current_user.id)
            created.append(hh.name)
        except HTTPException as e:
            skipped.append({"name": hh.name, "reason": e.detail})
        except IntegrityError:
            skipped.append({"name": hh.name, "reason": f"Hóa đơn kỳ {period} đã tồn tại hoặc dữ liệu liên kết không hợp lệ"})

    db.commit()
    clear_ai_cache()
    return {"created": created, "skipped": skipped, "period": period}


@router.put("/{iid}/status", response_model=InvoiceOut)
def update_status(
    iid: int, body: InvoiceStatusUpdate,
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    inv = db.query(models.Invoice).filter(models.Invoice.id == iid).first()
    if not inv:
        raise HTTPException(404, "Không tìm thấy hóa đơn")
    inv.status = body.status
    db.commit()
    clear_ai_cache()
    db.refresh(inv)
    return inv


@router.delete("/{iid}")
def delete_invoice(iid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    inv = db.query(models.Invoice).filter(models.Invoice.id == iid).first()
    if not inv:
        raise HTTPException(404, "Không tìm thấy hóa đơn")
    if db.query(models.Payment).filter(models.Payment.invoice_id == iid).count():
        raise HTTPException(409, "Hóa đơn đã có thanh toán, không thể xóa")
    try:
        db.delete(inv)
        db.commit()
    except Exception:
        db.rollback()
        raise
    clear_ai_cache()
    return {"message": "Đã xóa hóa đơn"}
