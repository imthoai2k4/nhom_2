"""
app/services/alert_service.py
Phát hiện tiêu thụ bất thường sau khi nhập chỉ số.
Spike: tiêu thụ tăng > 50% so với trung bình 3 tháng trước.
Tính bằng Python (không dùng SQL window function — tương thích SQLite).
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from app import models


SPIKE_THRESHOLD = Decimal("0.50")   # 50%


def check_and_create_alert(db: Session, reading: models.Reading) -> models.ConsumptionAlert | None:
    """
    Sau khi insert reading mới, kiểm tra spike so với TB 3 kỳ trước.
    Nếu phát hiện → tạo ConsumptionAlert và trả về, ngược lại None.
    """
    # Lấy 3 readings gần nhất cùng meter, trước period này
    prev_readings = (
        db.query(models.Reading)
        .filter(
            models.Reading.meter_id == reading.meter_id,
            models.Reading.period < reading.period,
        )
        .order_by(models.Reading.period.desc())
        .limit(3)
        .all()
    )

    if len(prev_readings) < 1:
        return None   # Chưa đủ lịch sử

    avg = sum(r.consumption for r in prev_readings) / len(prev_readings)
    avg = Decimal(str(avg))

    if avg == 0:
        return None

    pct_change = ((reading.consumption - avg) / avg * 100).quantize(Decimal("0.01"))

    if pct_change <= SPIKE_THRESHOLD * 100:
        return None  # Không có spike

    # Lấy household_id qua meter
    meter = db.query(models.Meter).filter(models.Meter.id == reading.meter_id).first()
    if not meter:
        return None

    label = "điện" if meter.meter_type == "electricity" else "nước"
    alert = models.ConsumptionAlert(
        household_id=meter.household_id,
        meter_id=reading.meter_id,
        period=reading.period,
        alert_type="spike",
        current_consumption=reading.consumption,
        avg_consumption=avg,
        percent_change=pct_change,
        message=(
            f"Tiêu thụ {label} kỳ {reading.period} tăng {pct_change}% "
            f"so với trung bình {len(prev_readings)} kỳ trước ({avg:.2f}). Cần kiểm tra."
        ),
        is_resolved=False,
    )
    db.add(alert)
    return alert
