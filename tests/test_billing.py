"""
tests/test_billing.py — Test thật cho billing.py (bậc thang EVN + VAT + nước).

Dùng đúng giá seed:
  1.728 / 1.786 / 2.074 / 2.612 / 2.919 / 3.015 đ/kWh
  Nước 5.973 đ/m³, VAT 10%.
"""
from decimal import Decimal
from types import SimpleNamespace

from app.services.billing import calc_electricity, calc_water


def _prices():
    tiers = [
        (1, 0, 50, 1728),
        (2, 50, 100, 1786),
        (3, 100, 200, 2074),
        (4, 200, 300, 2612),
        (5, 300, 400, 2919),
        (6, 400, None, 3015),
    ]
    return [
        SimpleNamespace(
            id=i,
            tier=tier,
            min_unit=Decimal(str(mn)),
            max_unit=Decimal(str(mx)) if mx is not None else None,
            price_per_unit=Decimal(str(ppu)),
        )
        for i, (tier, mn, mx, ppu) in enumerate(tiers, start=1)
    ]


def test_TC_BILL_001_zero_consumption():
    assert calc_electricity(Decimal("0"), _prices()) == []


def test_TC_BILL_002_tier_1_boundary_50():
    items = calc_electricity(Decimal("50"), _prices())
    assert len(items) == 1
    assert items[0]["subtotal"] == 86400          # 50 × 1.728
    assert items[0]["vat_amount"] == 8640         # 10%
    assert items[0]["total"] == 95040


def test_TC_BILL_003_cross_to_tier_2_at_51():
    items = calc_electricity(Decimal("51"), _prices())
    assert len(items) == 2
    assert items[0]["consumption"] == 50
    assert items[1]["consumption"] == 1
    assert sum(i["subtotal"] for i in items) == 88186   # 86.400 + 1.786
    assert sum(i["total"] for i in items) == 97005      # VAT 8.819


def test_TC_BILL_004_cross_to_tier_3_at_101():
    items = calc_electricity(Decimal("101"), _prices())
    assert len(items) == 3
    assert items[2]["consumption"] == 1
    assert sum(i["subtotal"] for i in items) == 177774
    assert sum(i["total"] for i in items) == 195551


def test_TC_BILL_005_full_five_tiers_400():
    items = calc_electricity(Decimal("400"), _prices())
    assert len(items) == 5
    assert sum(i["subtotal"] for i in items) == 936200
    assert sum(i["total"] for i in items) == 1029820


def test_TC_BILL_006_water_flat_rate():
    price = SimpleNamespace(id=99, price_per_unit=Decimal("5973"))
    item = calc_water(Decimal("10"), price)
    assert item["subtotal"] == 59730
    assert item["vat_amount"] == 5973
    assert item["total"] == 65703
