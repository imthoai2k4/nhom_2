"""app/routers/households.py — CRUD hộ/phòng (phân quyền admin/user)"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_admin, get_household_filter
from app.schemas import HouseholdCreate, HouseholdUpdate, HouseholdOut
from app import models

router = APIRouter()


@router.get("", response_model=list[HouseholdOut])
def list_households(
    status: Optional[str] = Query(None, description="active | inactive"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Household)
    # User chỉ thấy hộ của mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None:
        q = q.filter(models.Household.id == hh_filter)
    if status:
        q = q.filter(models.Household.status == status)
    return q.order_by(models.Household.name).all()


@router.get("/{hid}", response_model=HouseholdOut)
def get_household(
    hid: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    h = db.query(models.Household).filter(models.Household.id == hid).first()
    if not h:
        raise HTTPException(404, "Không tìm thấy hộ/phòng")
    # User chỉ xem hộ của mình
    hh_filter = get_household_filter(current_user)
    if hh_filter is not None and h.id != hh_filter:
        raise HTTPException(403, "Bạn không có quyền xem thông tin hộ này")
    return h


@router.post("", response_model=HouseholdOut, status_code=201)
def create_household(
    body: HouseholdCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    h = models.Household(**body.model_dump(), created_by=current_user.id)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@router.put("/{hid}", response_model=HouseholdOut)
def update_household(
    hid: int, body: HouseholdUpdate,
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    h = db.query(models.Household).filter(models.Household.id == hid).first()
    if not h:
        raise HTTPException(404, "Không tìm thấy hộ/phòng")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(h, k, v)
    db.commit()
    db.refresh(h)
    return h


@router.delete("/{hid}")
def delete_household(hid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    h = db.query(models.Household).filter(models.Household.id == hid).first()
    if not h:
        raise HTTPException(404, "Không tìm thấy hộ/phòng")
    if db.query(models.Invoice).filter(models.Invoice.household_id == hid).count():
        raise HTTPException(409, "Hộ đã có hóa đơn, không thể xóa. Hãy đặt thành inactive.")
    db.delete(h)
    db.commit()
    return {"message": f"Đã xóa hộ '{h.name}'"}
