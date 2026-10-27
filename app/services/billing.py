"""
app/services/billing.py
Tính tiền điện (bậc thang) + nước + VAT.
Trả về list InvoiceItem dict để insert vào DB.
Dùng Decimal/int xuyên suốt — không dùng float.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from sqlalchemy.orm import Session
from app import models


VAT_RATE = Decimal("0.10")


def _round_vnd(amount: Decimal) -> int:
    """Làm tròn đến đồng (int), không có xu."""
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def get_active_prices(db: Session, meter_type: str, on_date: date = None):
    """Lấy danh sách đơn giá đang áp dụng, sắp xếp theo bậc."""
    if on_date is None:
        on_date = date.today()
    return (
        db.query(models.UtilityPrice)
        .filter(
            models.UtilityPrice.meter_type == meter_type,
            models.UtilityPrice.effective_from <= on_date,
            (models.UtilityPrice.effective_to == None) |
            (models.UtilityPrice.effective_to >= on_date),
        )
        .order_by(models.UtilityPrice.tier)
        .all()
    )


def calc_electricity(consumption: Decimal, prices: list) -> list[dict]:
    """
    Tính tiền điện bậc thang.
    Trả về list dict mỗi bậc: {description, consumption, unit_price,
                                subtotal, vat_amount, total, price_id}
    """
    items = []
    remaining = consumption

    for p in prices:
        if remaining <= 0:
            break

        min_u = p.min_unit
        max_u = p.max_unit  # None = vô hạn

        if max_u is not None:
            tier_capacity = max_u - min_u
        else:
            tier_capacity = remaining

        used = min(remaining, tier_capacity)
        if used <= 0:
            continue

        subtotal = _round_vnd(used * p.price_per_unit)
        vat = _round_vnd(Decimal(subtotal) * VAT_RATE)
        total = subtotal + vat

        desc_range = f"{int(min_u)}–{int(max_u)} kWh" if max_u else f">{int(min_u)} kWh"
        items.append({
            "price_id": p.id,
            "description": f"Điện bậc {p.tier} ({desc_range})",
            "consumption": used,
            "unit_price": p.price_per_unit,
            "subtotal": subtotal,
            "vat_rate": VAT_RATE,
            "vat_amount": vat,
            "total": total,
        })
        remaining -= used

    return items


def calc_water(consumption: Decimal, price: models.UtilityPrice) -> dict:
    """Tính tiền nước (flat-rate)."""
    subtotal = _round_vnd(consumption * price.price_per_unit)
    vat = _round_vnd(Decimal(subtotal) * VAT_RATE)
    return {
        "price_id": price.id,
        "description": f"Nước ({consumption} m³)",
        "consumption": consumption,
        "unit_price": price.price_per_unit,
        "subtotal": subtotal,
        "vat_rate": VAT_RATE,
        "vat_amount": vat,
        "total": subtotal + vat,
    }


def generate_invoice_items(
    db: Session,
    electricity_reading: models.Reading | None,
    water_reading: models.Reading | None,
    period_date: date = None,
) -> tuple[list[dict], int, int]:
    """
    Tính toàn bộ items cho một hóa đơn.
    Trả về: (items_list, electricity_total, water_total)
    """
    if period_date is None:
        period_date = date.today()

    items = []
    elec_total = 0
    water_total = 0

    if electricity_reading and electricity_reading.consumption > 0:
        elec_prices = get_active_prices(db, "electricity", period_date)
        elec_items = calc_electricity(electricity_reading.consumption, elec_prices)
        for it in elec_items:
            it["reading_id"] = electricity_reading.id
        items.extend(elec_items)
        elec_total = sum(i["total"] for i in elec_items)

    if water_reading and water_reading.consumption > 0:
        water_prices = get_active_prices(db, "water", period_date)
        if water_prices:
            w_item = calc_water(water_reading.consumption, water_prices[0])
            w_item["reading_id"] = water_reading.id
            items.append(w_item)
            water_total = w_item["total"]

    return items, elec_total, water_total
