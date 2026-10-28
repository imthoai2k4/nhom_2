"""
app/seed_demo.py — Bổ sung lịch sử demo cho Phòng 101 & Phòng 102.

Mục tiêu:
  - 6 kỳ liên tiếp (2026-05 → 2026-10) cho cả đồng hồ điện và nước.
  - Hóa đơn tháng 7, 8, 9 đã thanh toán đủ.
  - Hóa đơn tháng 10 chưa thanh toán (công nợ để AI/dashboard phân tích).
  - Dữ liệu đủ dài để AI so sánh xu hướng, chi phí và bất thường.

Hàm `ensure_demo_history()` chạy lặp lại an toàn (idempotent):
chỉ thêm bản ghi còn thiếu, không sửa/xóa dữ liệu người dùng đã nhập.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.services.billing import generate_invoice_items

# ── Cấu hình dữ liệu demo ────────────────────────────────────────────────────
DEMO_HOUSEHOLDS = ("Phòng 101", "Phòng 102")

# (period, prev, curr) — consumption = curr - prev
# Phòng 101: ổn định ~75–81 kWh/tháng, nước 14–17 m³.
# Phòng 102: spike 180 kWh tháng 7 rồi giảm dần 160 → 142 → 118 kWh.
DEMO_READINGS = {
    "Phòng 101": {
        "electricity": [
            ("2026-05", "1000", "1075"),
            ("2026-06", "1075", "1150"),
            ("2026-07", "1150", "1228"),
            ("2026-08", "1228", "1309"),
            ("2026-09", "1309", "1385"),
            ("2026-10", "1385", "1457"),
        ],
        "water": [
            ("2026-05", "200", "215"),
            ("2026-06", "215", "230"),
            ("2026-07", "230", "246"),
            ("2026-08", "246", "263"),
            ("2026-09", "263", "278"),
            ("2026-10", "278", "292"),
        ],
    },
    "Phòng 102": {
        "electricity": [
            ("2026-05", "2000", "2095"),
            ("2026-06", "2095", "2190"),
            ("2026-07", "2190", "2370"),
            ("2026-08", "2370", "2530"),
            ("2026-09", "2530", "2672"),
            ("2026-10", "2672", "2790"),
        ],
        "water": [
            ("2026-05", "400", "420"),
            ("2026-06", "420", "440"),
            ("2026-07", "440", "475"),
            ("2026-08", "475", "507"),
            ("2026-09", "507", "535"),
            ("2026-10", "535", "559"),
        ],
    },
}

PAID_PERIODS = ("2026-07", "2026-08", "2026-09")
UNPAID_PERIOD = "2026-10"
INVOICE_PERIODS = PAID_PERIODS + (UNPAID_PERIOD,)

# Ngày thanh toán và hình thức khác nhau để lịch sử trông tự nhiên.
PAYMENT_INFO = {
    "Phòng 101": {
        "2026-07": (datetime(2026, 8, 21, 10, 15), "transfer"),
        "2026-08": (datetime(2026, 9, 9, 18, 5), "cash"),
        "2026-09": (datetime(2026, 10, 8, 10, 30), "transfer"),
    },
    "Phòng 102": {
        "2026-07": (datetime(2026, 8, 12, 8, 45), "transfer"),
        "2026-08": (datetime(2026, 9, 12, 19, 20), "cash"),
        "2026-09": (datetime(2026, 10, 12, 14, 10), "transfer"),
    },
}


def _period_date(period: str) -> date:
    year, month = (int(part) for part in period.split("-"))
    return date(year, month, 1)


def _due_date(period: str) -> date:
    """Hạn thanh toán: ngày 15 của tháng kế tiếp."""
    year, month = (int(part) for part in period.split("-"))
    if month == 12:
        return date(year + 1, 1, 15)
    return date(year, month + 1, 15)


def _get_admin_id(db: Session) -> int | None:
    admin = (
        db.query(models.User)
        .filter(models.User.role == "admin")
        .order_by(models.User.id)
        .first()
    )
    return admin.id if admin else None


def _ensure_readings(db: Session, household: models.Household) -> int:
    """Thêm các kỳ còn thiếu cho 2 đồng hồ của hộ. Trả về số reading đã thêm."""
    meters = {
        meter.meter_type: meter
        for meter in db.query(models.Meter)
        .filter(models.Meter.household_id == household.id)
        .all()
    }
    added = 0
    for meter_type, rows in DEMO_READINGS.get(household.name, {}).items():
        meter = meters.get(meter_type)
        if meter is None:
            print(f"[DEMO] Bỏ qua {household.name}/{meter_type}: chưa có đồng hồ.")
            continue
        for period, prev_raw, curr_raw in rows:
            exists = (
                db.query(models.Reading.id)
                .filter(
                    models.Reading.meter_id == meter.id,
                    models.Reading.period == period,
                )
                .first()
            )
            if exists:
                continue
            prev_reading = Decimal(prev_raw)
            curr_reading = Decimal(curr_raw)
            db.add(
                models.Reading(
                    meter_id=meter.id,
                    period=period,
                    prev_reading=prev_reading,
                    curr_reading=curr_reading,
                    consumption=curr_reading - prev_reading,
                    recorded_by=_get_admin_id(db),
                )
            )
            added += 1
    db.flush()
    return added


def _reading_for(
    db: Session, household_id: int, meter_type: str, period: str
) -> models.Reading | None:
    return (
        db.query(models.Reading)
        .join(models.Meter)
        .filter(
            models.Meter.household_id == household_id,
            models.Meter.meter_type == meter_type,
            models.Reading.period == period,
        )
        .first()
    )


def _ensure_invoices(db: Session, household: models.Household) -> int:
    """Tạo hóa đơn còn thiếu cho 4 kỳ, tính tiền bằng billing.py."""
    creator_id = _get_admin_id(db)
    added = 0
    for period in INVOICE_PERIODS:
        exists = (
            db.query(models.Invoice.id)
            .filter(
                models.Invoice.household_id == household.id,
                models.Invoice.period == period,
            )
            .first()
        )
        if exists:
            continue

        elec_reading = _reading_for(db, household.id, "electricity", period)
        water_reading = _reading_for(db, household.id, "water", period)
        if not elec_reading and not water_reading:
            print(f"[DEMO] Bỏ qua hóa đơn {household.name} {period}: chưa có chỉ số.")
            continue

        items_data, elec_total, water_total = generate_invoice_items(
            db, elec_reading, water_reading, _period_date(period)
        )
        invoice = models.Invoice(
            household_id=household.id,
            period=period,
            electricity_amount=elec_total,
            water_amount=water_total,
            total_amount=elec_total + water_total,
            status="unpaid",
            due_date=_due_date(period),
            created_by=creator_id,
        )
        db.add(invoice)
        db.flush()

        for item_data in items_data:
            db.add(models.InvoiceItem(invoice_id=invoice.id, **item_data))
        added += 1
    db.flush()
    return added


def _ensure_payments(db: Session, household: models.Household) -> int:
    """Thanh toán đủ các hóa đơn T7–T9; giữ T10 chưa thanh toán."""
    recorder_id = _get_admin_id(db)
    added = 0
    for period in PAID_PERIODS:
        invoice = (
            db.query(models.Invoice)
            .filter(
                models.Invoice.household_id == household.id,
                models.Invoice.period == period,
            )
            .first()
        )
        if not invoice:
            continue

        paid = (
            db.query(func.coalesce(func.sum(models.Payment.amount_paid), 0))
            .filter(models.Payment.invoice_id == invoice.id)
            .scalar()
            or 0
        )
        remaining = invoice.total_amount - paid
        if remaining > 0:
            paid_at, method = PAYMENT_INFO[household.name][period]
            db.add(
                models.Payment(
                    invoice_id=invoice.id,
                    amount_paid=remaining,
                    paid_at=paid_at,
                    method=method,
                    note=f"Thanh toán hóa đơn kỳ {period}",
                    recorded_by=recorder_id,
                )
            )
            added += 1
        invoice.status = "paid"

    # Hóa đơn tháng 10 phải còn nợ (chỉ đặt lại nếu chưa có thanh toán nào).
    october = (
        db.query(models.Invoice)
        .filter(
            models.Invoice.household_id == household.id,
            models.Invoice.period == UNPAID_PERIOD,
        )
        .first()
    )
    if october:
        paid = (
            db.query(func.coalesce(func.sum(models.Payment.amount_paid), 0))
            .filter(models.Payment.invoice_id == october.id)
            .scalar()
            or 0
        )
        if paid == 0:
            october.status = "unpaid"
    db.flush()
    return added


def ensure_demo_history(db: Session) -> dict[str, int]:
    """
    Bổ sung dữ liệu mẫu còn thiếu cho Phòng 101/102.

    Idempotent: gọi nhiều lần không tạo bản ghi trùng. Trả về số bản ghi
    đã thêm trong lần chạy này để dễ kiểm thử/log.
    """
    summary = {"readings": 0, "invoices": 0, "payments": 0}
    households = (
        db.query(models.Household)
        .filter(models.Household.name.in_(DEMO_HOUSEHOLDS))
        .order_by(models.Household.id)
        .all()
    )
    found_names = {household.name for household in households}
    missing = set(DEMO_HOUSEHOLDS) - found_names
    if missing:
        print(f"[DEMO] Không tìm thấy hộ: {', '.join(sorted(missing))} — bỏ qua.")
    if not households:
        return summary

    for household in households:
        summary["readings"] += _ensure_readings(db, household)
        summary["invoices"] += _ensure_invoices(db, household)
        summary["payments"] += _ensure_payments(db, household)

    db.commit()

    if any(summary.values()):
        print(
            "[DEMO] Bổ sung dữ liệu Phòng 101/102: "
            f"{summary['readings']} chỉ số, {summary['invoices']} hóa đơn, "
            f"{summary['payments']} thanh toán."
        )
    return summary
