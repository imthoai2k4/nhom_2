"""
app/schemas.py  — v2

Đồng bộ với models.py v2:
  - Tiền tệ: int (đồng)
  - Chỉ số:  Decimal (từ Numeric(12,2))
  - period:  str 'YYYY-MM' thay period_month/year
  - Thêm UtilityPrice schemas
  - Thêm ConsumptionAlert schemas
  - Validator: curr_reading >= prev_reading
  - Validator: period format YYYY-MM
"""
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Helpers ──────────────────────────────────────────────────────────────────
_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validate_period(v: str) -> str:
    if not _PERIOD_RE.match(v):
        raise ValueError("period phải có dạng YYYY-MM (VD: '2026-07')")
    return v


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="admin123")


class LoginResponse(BaseModel):
    success: bool
    role: str
    username: str
    household_id: Optional[int] = None
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username:  str = Field(..., min_length=3, max_length=50)
    password:  str = Field(..., min_length=4)
    full_name: Optional[str] = None
    role:      Literal["admin", "user"] = "user"


class UserOut(BaseModel):
    id:         int
    username:   str
    full_name:  Optional[str]
    role:       str
    is_active:  bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# HOUSEHOLD
# ─────────────────────────────────────────────────────────────────────────────
class HouseholdCreate(BaseModel):
    name:       str  = Field(..., min_length=1, max_length=100, example="Phòng 101")
    address:    Optional[str] = None
    owner_name: Optional[str] = None
    phone:      Optional[str] = None
    status:     Literal["active", "inactive"] = "active"


class HouseholdUpdate(BaseModel):
    name:       Optional[str] = None
    address:    Optional[str] = None
    owner_name: Optional[str] = None
    phone:      Optional[str] = None
    status:     Optional[Literal["active", "inactive"]] = None


class HouseholdOut(BaseModel):
    id:         int
    name:       str
    address:    Optional[str]
    owner_name: Optional[str]
    phone:      Optional[str]
    status:     str
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# METER
# ─────────────────────────────────────────────────────────────────────────────
class MeterCreate(BaseModel):
    household_id: int
    meter_type:   Literal["electricity", "water"]
    meter_number: str   = Field(..., min_length=1, max_length=50, example="EVN-2026-001")
    unit:         str   = Field(..., example="kWh")
    installed_at: Optional[date] = None


class MeterUpdate(BaseModel):
    meter_number: Optional[str]  = None
    installed_at: Optional[date] = None
    is_active:    Optional[bool] = None


class MeterOut(BaseModel):
    id:           int
    household_id: int
    meter_type:   str
    meter_number: str
    unit:         str
    installed_at: Optional[date]
    is_active:    bool
    created_at:   datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY PRICE
# ─────────────────────────────────────────────────────────────────────────────
class UtilityPriceCreate(BaseModel):
    meter_type:     Literal["electricity", "water"]
    tier:           int         = Field(..., ge=1)
    min_unit:       Decimal     = Field(..., ge=0, example=Decimal("0"))
    max_unit:       Optional[Decimal] = None
    price_per_unit: int         = Field(..., gt=0, example=1728,
                                        description="Đồng/kWh hoặc đồng/m³")
    effective_from: date
    effective_to:   Optional[date] = None


class UtilityPriceOut(BaseModel):
    id:             int
    meter_type:     str
    tier:           int
    min_unit:       Decimal
    max_unit:       Optional[Decimal]
    price_per_unit: int
    effective_from: date
    effective_to:   Optional[date]
    created_at:     datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# READING
# ─────────────────────────────────────────────────────────────────────────────
class ReadingCreate(BaseModel):
    meter_id:     int
    period:       str     = Field(..., example="2026-07",
                                  description="Kỳ tháng dạng YYYY-MM")
    prev_reading: Decimal = Field(..., ge=0, example=Decimal("1150.00"))
    curr_reading: Decimal = Field(..., ge=0, example=Decimal("1228.00"))

    @field_validator("period")
    @classmethod
    def check_period(cls, v: str) -> str:
        return validate_period(v)

    @model_validator(mode="after")
    def curr_ge_prev(self):
        if self.curr_reading < self.prev_reading:
            raise ValueError(
                f"Chỉ số hiện tại ({self.curr_reading}) không được nhỏ hơn "
                f"chỉ số kỳ trước ({self.prev_reading})"
            )
        return self


class ReadingOut(BaseModel):
    id:           int
    meter_id:     int
    period:       str
    prev_reading: Decimal
    curr_reading: Decimal
    consumption:  Decimal
    recorded_by:  Optional[int]
    created_at:   datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE ITEM
# ─────────────────────────────────────────────────────────────────────────────
class InvoiceItemOut(BaseModel):
    id:          int
    reading_id:  Optional[int]
    price_id:    Optional[int]
    description: Optional[str]
    consumption: Decimal
    unit_price:  int
    subtotal:    int
    vat_rate:    Decimal
    vat_amount:  int
    total:       int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE
# ─────────────────────────────────────────────────────────────────────────────
class InvoiceCreate(BaseModel):
    """Tạo hóa đơn — hệ thống tự lấy readings trong kỳ để tính."""
    household_id: int
    period:       str = Field(..., example="2026-07")

    @field_validator("period")
    @classmethod
    def check_period(cls, v: str) -> str:
        return validate_period(v)


class InvoiceStatusUpdate(BaseModel):
    status: Literal["unpaid", "partial", "paid"]


class InvoiceOut(BaseModel):
    id:                  int
    household_id:        int
    period:              str
    electricity_amount:  int
    water_amount:        int
    total_amount:        int
    status:              str
    due_date:            Optional[date]
    created_at:          datetime
    items:               List[InvoiceItemOut] = []

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT
# ─────────────────────────────────────────────────────────────────────────────
class PaymentCreate(BaseModel):
    invoice_id:  int
    amount_paid: int  = Field(..., gt=0, description="Số tiền thanh toán (đồng)")
    method:      Literal["cash", "transfer", "other"] = "cash"
    note:        Optional[str] = None


class PaymentOut(BaseModel):
    id:          int
    invoice_id:  int
    amount_paid: int
    paid_at:     datetime
    method:      str
    note:        Optional[str]
    recorded_by: Optional[int]
    created_at:  datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# CONSUMPTION ALERT
# ─────────────────────────────────────────────────────────────────────────────
class ConsumptionAlertOut(BaseModel):
    id:                  int
    household_id:        int
    meter_id:            int
    period:              str
    alert_type:          str
    current_consumption: Decimal
    avg_consumption:     Optional[Decimal]
    percent_change:      Optional[Decimal]
    message:             str
    is_resolved:         bool
    created_at:          datetime

    class Config:
        from_attributes = True


class AlertResolve(BaseModel):
    is_resolved: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────────────────────────────────────
class DebtReport(BaseModel):
    household_id:     int
    household_name:   str
    owner_name:       Optional[str]
    total_invoiced:   int
    total_paid:       int
    outstanding_debt: int


class MonthlyRevenueReport(BaseModel):
    period:              str
    total_households:    int
    total_invoiced:      int
    total_collected:     int
    total_outstanding:   int
    collection_rate_pct: float


class SystemSummary(BaseModel):
    total_households:  int
    active_households: int
    total_invoices:    int
    unpaid_invoices:   int
    total_revenue:     int
    outstanding_debt:  int
    unresolved_alerts: int


# ─────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────
class ChatSessionCreate(BaseModel):
    title: Optional[str] = "Hội thoại mới"
    context_hh: Optional[int] = None


class ChatSessionOut(BaseModel):
    id: int
    user_id: int
    title: str
    context_hh: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    intent: Optional[str] = None
    ref_data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    session_id: Optional[int] = None          # None = tạo session mới
    message: str
    context_hh: Optional[int] = None          # optional: ghim hộ đang trao đổi


class ChatResponse(BaseModel):
    session_id: int
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    intent: str
    ref_data: Optional[dict] = None           # dữ liệu tham chiếu cho frontend
