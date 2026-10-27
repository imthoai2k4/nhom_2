"""
app/models.py  — v2 (cập nhật theo thiết kế CSDL mới)

Thay đổi so với v1:
  - Tiền tệ dùng Integer (đơn vị: đồng) thay Float → tránh sai số
  - Chỉ số dùng Numeric(12,2) thay Float
  - period CHAR(7) 'YYYY-MM' thay period_month + period_year riêng
  - Thêm bảng UtilityPrice (đơn giá bậc thang + lịch sử)
  - Thêm bảng ConsumptionAlert (cảnh báo tiêu thụ)
  - UNIQUE(meter_id, period) trên readings
  - UNIQUE(household_id, period) trên invoices
  - InvoiceItem thêm price_id FK, vat_rate, snapshot unit_price Integer
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Date,
    DateTime, ForeignKey, Numeric,
    UniqueConstraint, CheckConstraint,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base


# ─────────────────────────────────────────────────────────────
# 1. USERS
# ─────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    password      = Column(String(128), nullable=False)   # plain-text demo
    full_name     = Column(String(100), nullable=True)
    role          = Column(SAEnum("admin", "user", name="user_role"),
                           nullable=False, default="user")
    household_id  = Column(Integer, ForeignKey("households.id"), nullable=True)
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    # Relations
    household     = relationship("Household", back_populates="user_account",
                                 foreign_keys=[household_id])
    households    = relationship("Household", back_populates="manager",
                                 foreign_keys="Household.created_by")
    readings_rec  = relationship("Reading",  back_populates="recorder",
                                 foreign_keys="Reading.recorded_by")
    payments_rec  = relationship("Payment",  back_populates="recorder",
                                 foreign_keys="Payment.recorded_by")
    invoices_cr   = relationship("Invoice",  back_populates="creator",
                                 foreign_keys="Invoice.created_by")
    chat_sessions = relationship("ChatSession", back_populates="owner",
                                 foreign_keys="ChatSession.user_id",
                                 cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
# 2. HOUSEHOLDS
# ─────────────────────────────────────────────────────────────
class Household(Base):
    __tablename__ = "households"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)
    address     = Column(String(200), nullable=True)
    owner_name  = Column(String(100), nullable=True)
    phone       = Column(String(20),  nullable=True)
    status      = Column(SAEnum("active", "inactive", name="household_status"),
                         nullable=False, default="active")
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow,
                         onupdate=datetime.utcnow, nullable=False)

    # Relations
    manager      = relationship("User",     back_populates="households",
                                foreign_keys=[created_by])
    user_account = relationship("User",     back_populates="household",
                                foreign_keys="User.household_id",
                                uselist=False)
    meters       = relationship("Meter",    back_populates="household",
                                cascade="all, delete-orphan")
    invoices     = relationship("Invoice",  back_populates="household",
                                cascade="all, delete-orphan")
    alerts       = relationship("ConsumptionAlert", back_populates="household",
                                cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
# 3. METERS
# ─────────────────────────────────────────────────────────────
class Meter(Base):
    __tablename__ = "meters"

    id            = Column(Integer, primary_key=True, index=True)
    household_id  = Column(Integer, ForeignKey("households.id"), nullable=False,
                           index=True)
    meter_type    = Column(SAEnum("electricity", "water", name="meter_type"),
                           nullable=False)
    meter_number  = Column(String(50), unique=True, nullable=False)
    unit          = Column(String(10), nullable=False)        # 'kWh' | 'm3'
    installed_at  = Column(Date, nullable=True)
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    household = relationship("Household", back_populates="meters")
    readings  = relationship("Reading",  back_populates="meter",
                             cascade="all, delete-orphan")
    alerts    = relationship("ConsumptionAlert", back_populates="meter",
                             cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
# 4. UTILITY PRICES  (đơn giá bậc thang + lịch sử)
# ─────────────────────────────────────────────────────────────
class UtilityPrice(Base):
    """
    Đơn giá điện bậc thang hoặc nước flat-rate.
    Điện: nhiều row với tier 1..6, min_unit/max_unit xác định khoảng.
    Nước: 1 row với tier=1, max_unit=NULL.
    Lưu lịch sử: effective_from / effective_to (NULL = đang áp dụng).
    price_per_unit: đơn vị ĐỒNG (Integer), tránh sai số float.
    """
    __tablename__ = "utility_prices"
    __table_args__ = (
        UniqueConstraint("meter_type", "tier", "effective_from",
                         name="uq_price_type_tier_date"),
        CheckConstraint("price_per_unit > 0", name="ck_price_positive"),
        CheckConstraint("tier >= 1",          name="ck_tier_ge_1"),
        CheckConstraint("min_unit >= 0",      name="ck_min_unit_ge_0"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    meter_type      = Column(SAEnum("electricity", "water", name="price_meter_type"),
                             nullable=False)
    tier            = Column(Integer, nullable=False)
    min_unit        = Column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    max_unit        = Column(Numeric(10, 2), nullable=True)   # NULL = vô hạn
    price_per_unit  = Column(Integer, nullable=False)          # đồng/kWh hoặc đồng/m³
    effective_from  = Column(Date, nullable=False)
    effective_to    = Column(Date, nullable=True)              # NULL = đang dùng
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    invoice_items   = relationship("InvoiceItem", back_populates="price")


# ─────────────────────────────────────────────────────────────
# 5. READINGS  (chỉ số đồng hồ theo kỳ)
# ─────────────────────────────────────────────────────────────
class Reading(Base):
    """
    Một đồng hồ chỉ được ghi 1 lần trong 1 kỳ (UNIQUE meter_id, period).
    Dùng Numeric(12,2) để tránh sai số — SQLAlchemy trả về Decimal.
    consumption luôn = curr_reading - prev_reading.
    """
    __tablename__ = "readings"
    __table_args__ = (
        UniqueConstraint("meter_id", "period", name="uq_reading_meter_period"),
        CheckConstraint("prev_reading >= 0",             name="ck_prev_ge_0"),
        CheckConstraint("curr_reading >= prev_reading",  name="ck_curr_ge_prev"),
        CheckConstraint("consumption >= 0",              name="ck_consumption_ge_0"),
    )

    id            = Column(Integer, primary_key=True, index=True)
    meter_id      = Column(Integer, ForeignKey("meters.id"), nullable=False,
                           index=True)
    period        = Column(String(7), nullable=False, index=True)  # 'YYYY-MM'
    prev_reading  = Column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    curr_reading  = Column(Numeric(12, 2), nullable=False)
    consumption   = Column(Numeric(12, 2), nullable=False)         # = curr - prev
    recorded_by   = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)

    # Relations
    meter         = relationship("Meter",  back_populates="readings")
    recorder      = relationship("User",   back_populates="readings_rec",
                                 foreign_keys=[recorded_by])
    invoice_items = relationship("InvoiceItem", back_populates="reading")


# ─────────────────────────────────────────────────────────────
# 6. INVOICES
# ─────────────────────────────────────────────────────────────
class Invoice(Base):
    """
    Hóa đơn tháng. Tất cả cột tiền dùng Integer (đơn vị: đồng).
    UNIQUE(household_id, period) — mỗi hộ 1 hóa đơn/tháng.
    """
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("household_id", "period", name="uq_invoice_household_period"),
    )

    id                  = Column(Integer, primary_key=True, index=True)
    household_id        = Column(Integer, ForeignKey("households.id"),
                                 nullable=False, index=True)
    period              = Column(String(7), nullable=False, index=True)  # 'YYYY-MM'
    electricity_amount  = Column(Integer, nullable=False, default=0)  # đồng (đã VAT)
    water_amount        = Column(Integer, nullable=False, default=0)  # đồng (đã VAT)
    total_amount        = Column(Integer, nullable=False, default=0)  # = elec + water
    status              = Column(
        SAEnum("unpaid", "partial", "paid", name="invoice_status"),
        nullable=False, default="unpaid")
    due_date            = Column(Date, nullable=True)
    created_by          = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow,
                                 onupdate=datetime.utcnow, nullable=False)

    # Relations
    household = relationship("Household",   back_populates="invoices")
    creator   = relationship("User",        back_populates="invoices_cr",
                             foreign_keys=[created_by])
    items     = relationship("InvoiceItem", back_populates="invoice",
                             cascade="all, delete-orphan")
    payments  = relationship("Payment",     back_populates="invoice",
                             cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
# 7. INVOICE ITEMS
# ─────────────────────────────────────────────────────────────
class InvoiceItem(Base):
    """
    Chi tiết từng dòng hóa đơn (1 bậc điện = 1 dòng).
    Snapshot unit_price (Integer) để lịch sử không đổi dù giá thay đổi.
    """
    __tablename__ = "invoice_items"

    id          = Column(Integer, primary_key=True, index=True)
    invoice_id  = Column(Integer, ForeignKey("invoices.id"), nullable=False,
                         index=True)
    reading_id  = Column(Integer, ForeignKey("readings.id"), nullable=True)
    price_id    = Column(Integer, ForeignKey("utility_prices.id"), nullable=True)
    description = Column(String(200), nullable=True)
    consumption = Column(Numeric(12, 2), nullable=False)
    unit_price  = Column(Integer, nullable=False)       # snapshot đơn giá (đồng)
    subtotal    = Column(Integer, nullable=False)        # trước VAT
    vat_rate    = Column(Numeric(5, 4), nullable=False, default=Decimal("0.1"))
    vat_amount  = Column(Integer, nullable=False, default=0)
    total       = Column(Integer, nullable=False)        # sau VAT

    # Relations
    invoice = relationship("Invoice",      back_populates="items")
    reading = relationship("Reading",      back_populates="invoice_items")
    price   = relationship("UtilityPrice", back_populates="invoice_items")


# ─────────────────────────────────────────────────────────────
# 8. PAYMENTS
# ─────────────────────────────────────────────────────────────
class Payment(Base):
    """amount_paid dùng Integer (đồng)."""
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_paid > 0", name="ck_payment_positive"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    invoice_id  = Column(Integer, ForeignKey("invoices.id"), nullable=False,
                         index=True)
    amount_paid = Column(Integer, nullable=False)          # đồng
    paid_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    method      = Column(
        SAEnum("cash", "transfer", "other", name="payment_method"),
        nullable=False, default="cash")
    note        = Column(Text, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    invoice  = relationship("Invoice", back_populates="payments")
    recorder = relationship("User",    back_populates="payments_rec",
                            foreign_keys=[recorded_by])


# ─────────────────────────────────────────────────────────────
# 9. CONSUMPTION ALERTS
# ─────────────────────────────────────────────────────────────
class ConsumptionAlert(Base):
    """
    Cảnh báo tiêu thụ bất thường:
      spike        — tăng >50% so với TB 3 tháng trước
      negative     — chỉ số âm (lỗi nhập liệu)
      contradiction— curr < prev (mâu thuẫn)
    """
    __tablename__ = "consumption_alerts"

    id                  = Column(Integer, primary_key=True, index=True)
    household_id        = Column(Integer, ForeignKey("households.id"),
                                 nullable=False, index=True)
    meter_id            = Column(Integer, ForeignKey("meters.id"),
                                 nullable=False)
    period              = Column(String(7), nullable=False)   # 'YYYY-MM'
    alert_type          = Column(
        SAEnum("spike", "negative", "contradiction", name="alert_type"),
        nullable=False)
    current_consumption = Column(Numeric(12, 2), nullable=False)
    avg_consumption     = Column(Numeric(12, 2), nullable=True)
    percent_change      = Column(Numeric(6, 2),  nullable=True)
    message             = Column(Text, nullable=False)
    is_resolved         = Column(Boolean, nullable=False, default=False)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    household = relationship("Household", back_populates="alerts")
    meter     = relationship("Meter",     back_populates="alerts")


# ─────────────────────────────────────────────────────────────
# 10. CHAT SESSIONS  (lưu lịch sử hội thoại AI)
# ─────────────────────────────────────────────────────────────
class ChatSession(Base):
    """
    Mỗi phiên chat là 1 cuộc hội thoại giữa user và AI.
    Phân quyền: user thường chỉ thấy session của mình; admin thấy tất cả.
    """
    __tablename__ = "chat_sessions"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title        = Column(String(200), nullable=False, default="Hội thoại mới")
    context_hh   = Column(Integer, ForeignKey("households.id"), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=False)

    # Relations
    owner        = relationship("User",  back_populates="chat_sessions",
                                foreign_keys=[user_id])
    household    = relationship("Household", foreign_keys=[context_hh])
    messages     = relationship("ChatMessage", back_populates="session",
                                cascade="all, delete-orphan",
                                order_by="ChatMessage.created_at")


# ─────────────────────────────────────────────────────────────
# 11. CHAT MESSAGES
# ─────────────────────────────────────────────────────────────
class ChatMessage(Base):
    """
    Một tin nhắn trong phiên chat.
    role: 'user' | 'assistant' | 'system'
    data: lưu JSON dữ liệu tham chiếu (vd: id hộ, id hóa đơn) để frontend mở link.
    """
    __tablename__ = "chat_messages"

    id           = Column(Integer, primary_key=True, index=True)
    session_id   = Column(Integer, ForeignKey("chat_sessions.id"),
                          nullable=False, index=True)
    role         = Column(SAEnum("user", "assistant", "system", name="chat_role"),
                          nullable=False)
    content      = Column(Text, nullable=False)
    intent       = Column(String(50), nullable=True)   # 'lookup_household', 'invoice', ...
    ref_data     = Column(Text, nullable=True)         # JSON string
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False,
                          index=True)

    # Relations
    session      = relationship("ChatSession", back_populates="messages")
