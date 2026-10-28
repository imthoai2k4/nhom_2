"""app/routers/payments.py — Thanh toán + công nợ + báo cáo (phân quyền admin/user)"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_admin, get_household_filter
from app.schemas import PaymentCreate, PaymentOut
from app import models
from app.routers.ai_analysis import clear_ai_cache

router = APIRouter()


def _update_invoice_status(db: Session, invoice: models.Invoice):
    """Tự động cập nhật trạng thái hóa đơn sau thanh toán."""
    total_paid = db.query(func.sum(models.Payment.amount_paid)).filter(
        models.Payment.invoice_id == invoice.id
    ).scalar() or 0
    if total_paid >= invoice.total_amount:
        invoice.status = "paid"
    elif total_paid > 0:
        invoice.status = "partial"
    else:
        invoice.status = "unpaid"


@router.get("", response_model=list[PaymentOut])
def list_payments(
    invoice_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Payment)
    # User chỉ thấy thanh toán của hộ mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None:
        q = q.join(models.Invoice).filter(models.Invoice.household_id == hh_filter)
    if invoice_id:
        q = q.filter(models.Payment.invoice_id == invoice_id)
    return q.order_by(models.Payment.paid_at.desc()).all()


@router.post("", response_model=PaymentOut, status_code=201)
def create_payment(
    body: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    inv = db.query(models.Invoice).filter(models.Invoice.id == body.invoice_id).first()
    if not inv:
        raise HTTPException(404, "Hóa đơn không tồn tại")
    if inv.status == "paid":
        raise HTTPException(400, "Hóa đơn đã thanh toán đủ")

    # Kiểm tra không vượt tổng
    paid_so_far = db.query(func.sum(models.Payment.amount_paid)).filter(
        models.Payment.invoice_id == body.invoice_id
    ).scalar() or 0
    remaining = inv.total_amount - paid_so_far
    if body.amount_paid > remaining:
        raise HTTPException(400, f"Số tiền vượt quá số còn nợ ({remaining:,}đ)")

    p = models.Payment(
        invoice_id=body.invoice_id,
        amount_paid=body.amount_paid,
        method=body.method,
        note=body.note,
        recorded_by=current_user.id,
    )
    db.add(p)
    db.flush()
    _update_invoice_status(db, inv)
    db.commit()
    clear_ai_cache()
    db.refresh(p)
    return p


# ── Báo cáo ─────────────────────────────────────────────────────────────────

@router.get("/reports/debt")
def debt_report(
    household_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Công nợ theo hộ: tổng hóa đơn, đã trả, còn nợ."""
    q = (
        db.query(
            models.Household.id,
            models.Household.name,
            models.Household.owner_name,
            func.coalesce(func.sum(models.Invoice.total_amount), 0).label("total_invoiced"),
            func.coalesce(
                db.query(func.sum(models.Payment.amount_paid))
                .filter(models.Payment.invoice_id == models.Invoice.id)
                .correlate(models.Invoice)
                .scalar_subquery(), 0
            ).label("total_paid"),
        )
        .outerjoin(models.Invoice, models.Invoice.household_id == models.Household.id)
        .group_by(models.Household.id)
    )
    # User chỉ thấy công nợ hộ mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None:
        q = q.filter(models.Household.id == hh_filter)
    elif household_id:
        q = q.filter(models.Household.id == household_id)

    rows = q.all()
    return [
        {
            "household_id": r.id,
            "household_name": r.name,
            "owner_name": r.owner_name,
            "total_invoiced": r.total_invoiced,
            "total_paid": r.total_paid or 0,
            "outstanding_debt": r.total_invoiced - (r.total_paid or 0),
        }
        for r in rows
    ]


@router.get("/reports/summary")
def summary_report(db: Session = Depends(get_db), _=Depends(require_admin)):
    """Tổng quan hệ thống."""
    total_hh = db.query(models.Household).count()
    active_hh = db.query(models.Household).filter(models.Household.status == "active").count()
    total_inv = db.query(models.Invoice).count()
    unpaid_inv = db.query(models.Invoice).filter(models.Invoice.status == "unpaid").count()
    total_rev = db.query(func.sum(models.Invoice.total_amount)).scalar() or 0
    total_paid = db.query(func.sum(models.Payment.amount_paid)).scalar() or 0
    unresolved = db.query(models.ConsumptionAlert).filter(
        models.ConsumptionAlert.is_resolved == False
    ).count()

    return {
        "total_households": total_hh,
        "active_households": active_hh,
        "total_invoices": total_inv,
        "unpaid_invoices": unpaid_inv,
        "total_revenue": total_rev,
        "total_paid": total_paid,
        "outstanding_debt": total_rev - total_paid,
        "unresolved_alerts": unresolved,
    }


@router.get("/reports/alerts")
def alerts_report(
    household_id: Optional[int] = Query(None),
    resolved: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Danh sách cảnh báo tiêu thụ."""
    q = db.query(models.ConsumptionAlert)
    # User chỉ thấy cảnh báo hộ mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None:
        q = q.filter(models.ConsumptionAlert.household_id == hh_filter)
    elif household_id:
        q = q.filter(models.ConsumptionAlert.household_id == household_id)
    if resolved is not None:
        q = q.filter(models.ConsumptionAlert.is_resolved == resolved)
    alerts = q.order_by(models.ConsumptionAlert.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "household_id": a.household_id,
            "meter_id": a.meter_id,
            "period": a.period,
            "alert_type": a.alert_type,
            "current_consumption": float(a.current_consumption),
            "avg_consumption": float(a.avg_consumption) if a.avg_consumption else None,
            "percent_change": float(a.percent_change) if a.percent_change else None,
            "message": a.message,
            "is_resolved": a.is_resolved,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


@router.put("/reports/alerts/{aid}/resolve")
def resolve_alert(aid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    a = db.query(models.ConsumptionAlert).filter(models.ConsumptionAlert.id == aid).first()
    if not a:
        raise HTTPException(404, "Không tìm thấy cảnh báo")
    a.is_resolved = True
    db.commit()
    clear_ai_cache()
    return {"message": "Đã đánh dấu xử lý"}
