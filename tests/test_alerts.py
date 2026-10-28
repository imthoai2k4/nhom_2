"""
tests/test_alerts.py — Test thật cho alert_service.check_and_create_alert.

Ngưỡng nghiệp vụ: tăng > 50% so với trung bình tối đa 3 kỳ trước.
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import models
from app.services.alert_service import check_and_create_alert


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    hh = models.Household(id=1, name="Phòng 101", status="active")
    session.add(hh)
    session.flush()

    meter = models.Meter(
        id=1, household_id=1, meter_type="electricity",
        meter_number="E101", unit="kWh",
    )
    session.add(meter)
    session.flush()

    # 3 kỳ trước, trung bình = 100 kWh
    for i, period in enumerate(("2026-04", "2026-05", "2026-06")):
        session.add(models.Reading(
            meter_id=1, period=period,
            prev_reading=Decimal("0"), curr_reading=Decimal("100"),
            consumption=Decimal("100"), recorded_by=99,
        ))
    session.commit()
    yield session
    session.close()


def _new_reading(consumption: Decimal, period: str = "2026-07"):
    return models.Reading(
        meter_id=1, period=period,
        prev_reading=Decimal("0"), curr_reading=consumption,
        consumption=consumption, recorded_by=99,
    )


def test_TC_ALERT_001_below_threshold_49(db):
    assert check_and_create_alert(db, _new_reading(Decimal("149"))) is None
    assert db.query(models.ConsumptionAlert).count() == 0


def test_TC_ALERT_002_boundary_50_no_alert(db):
    # Code dùng ">" 50%, nên đúng 50% chưa tạo alert.
    assert check_and_create_alert(db, _new_reading(Decimal("150"))) is None
    assert db.query(models.ConsumptionAlert).count() == 0


def test_TC_ALERT_003_above_threshold_51(db):
    alert = check_and_create_alert(db, _new_reading(Decimal("151")))
    assert alert is not None
    assert alert.alert_type == "spike"
    assert alert.percent_change == Decimal("51.00")
    assert alert.is_resolved is False
    assert "tăng" in alert.message.lower()
    assert db.query(models.ConsumptionAlert).count() == 1


def test_TC_ALERT_004_no_history_no_alert(db):
    db.query(models.Reading).delete()
    db.commit()
    assert check_and_create_alert(db, _new_reading(Decimal("200"))) is None


def test_TC_ALERT_005_average_zero_no_alert(db):
    db.query(models.Reading).delete()
    db.commit()
    for period in ("2026-04", "2026-05", "2026-06"):
        db.add(models.Reading(
            meter_id=1, period=period,
            prev_reading=Decimal("0"), curr_reading=Decimal("0"),
            consumption=Decimal("0"), recorded_by=99,
        ))
    db.commit()
    assert check_and_create_alert(db, _new_reading(Decimal("100"))) is None
