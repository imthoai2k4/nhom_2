"""tests/test_seed_demo.py — Dữ liệu demo Phòng 101/102 phải đủ kỳ và idempotent."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models
from app.routers.payments import _debt_query
from app.seed_demo import ensure_demo_history


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _build_base_data(db):
    admin = models.User(
        username="admin", password="x", full_name="Admin", role="admin"
    )
    db.add(admin)
    db.flush()

    households = []
    for idx, name in enumerate(("Phòng 101", "Phòng 102"), start=1):
        hh = models.Household(
            name=name, owner_name=f"Chủ hộ {idx}", status="active",
            created_by=admin.id,
        )
        db.add(hh)
        db.flush()
        db.add_all([
            models.Meter(
                household_id=hh.id, meter_type="electricity",
                meter_number=f"EVN-{idx}", unit="kWh",
            ),
            models.Meter(
                household_id=hh.id, meter_type="water",
                meter_number=f"SAW-{idx}", unit="m3",
            ),
        ])
        households.append(hh)

    for tier, mn, mx, price in (
        (1, 0, 50, 1728),
        (2, 50, 100, 1786),
        (3, 100, 200, 2074),
        (4, 200, 300, 2612),
        (5, 300, 400, 2919),
        (6, 400, None, 3015),
    ):
        db.add(models.UtilityPrice(
            meter_type="electricity", tier=tier,
            min_unit=Decimal(str(mn)),
            max_unit=Decimal(str(mx)) if mx is not None else None,
            price_per_unit=price, effective_from=date(2024, 1, 1),
        ))
    db.add(models.UtilityPrice(
        meter_type="water", tier=1, min_unit=Decimal("0"),
        max_unit=None, price_per_unit=5973, effective_from=date(2024, 1, 1),
    ))
    db.commit()
    return households


def test_seed_demo_creates_full_history_for_both_households(db):
    _build_base_data(db)

    summary = ensure_demo_history(db)
    assert summary == {"readings": 24, "invoices": 8, "payments": 6}

    assert db.query(models.Reading).count() == 24
    assert db.query(models.Invoice).count() == 8
    assert db.query(models.InvoiceItem).count() == 28
    assert db.query(models.Payment).count() == 6

    for hh in db.query(models.Household).all():
        periods = {
            row[0]
            for row in db.query(models.Reading.period)
            .join(models.Meter)
            .filter(models.Meter.household_id == hh.id)
            .distinct()
        }
        assert periods == {
            "2026-05", "2026-06", "2026-07",
            "2026-08", "2026-09", "2026-10",
        }

        invoices = {
            inv.period: inv
            for inv in db.query(models.Invoice)
            .filter(models.Invoice.household_id == hh.id)
        }
        assert set(invoices) == {"2026-07", "2026-08", "2026-09", "2026-10"}
        for period in ("2026-07", "2026-08", "2026-09"):
            inv = invoices[period]
            paid = db.query(func.sum(models.Payment.amount_paid)).filter(
                models.Payment.invoice_id == inv.id
            ).scalar()
            assert inv.status == "paid"
            assert paid == inv.total_amount
        assert invoices["2026-10"].status == "unpaid"
        assert (
            db.query(func.sum(models.Payment.amount_paid))
            .filter(models.Payment.invoice_id == invoices["2026-10"].id)
            .scalar()
            or 0
        ) == 0


def test_seed_demo_is_idempotent(db):
    _build_base_data(db)
    ensure_demo_history(db)

    counts_before = (
        db.query(models.Reading).count(),
        db.query(models.Invoice).count(),
        db.query(models.InvoiceItem).count(),
        db.query(models.Payment).count(),
    )

    summary = ensure_demo_history(db)
    assert summary == {"readings": 0, "invoices": 0, "payments": 0}
    assert counts_before == (
        db.query(models.Reading).count(),
        db.query(models.Invoice).count(),
        db.query(models.InvoiceItem).count(),
        db.query(models.Payment).count(),
    )


def test_debt_report_sums_all_payments_per_household(db):
    """Nhiều hóa đơn/hộ: total_paid phải cộng đủ mọi payment, không chỉ hóa đơn đầu."""
    _build_base_data(db)
    ensure_demo_history(db)

    rows = {row.name: row for row in _debt_query(db).all()}
    assert rows["Phòng 101"].total_invoiced == 997732
    assert rows["Phòng 101"].total_paid == 767487  # T7+T8+T9, T10 còn nợ
    assert rows["Phòng 101"].total_invoiced - rows["Phòng 101"].total_paid == 230245
    assert rows["Phòng 102"].total_invoiced == 2011226
    assert rows["Phòng 102"].total_paid == 1619204
    assert rows["Phòng 102"].total_invoiced - rows["Phòng 102"].total_paid == 392022
