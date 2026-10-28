"""
app/seed.py  — v3

Đồng bộ với models.py v3 (User có household_id FK):
  - period dạng 'YYYY-MM'
  - Tiền dùng Integer (đồng)
  - Chỉ số dùng Decimal
  - Thêm bảng utility_prices (bậc thang điện EVN 2024 + nước)
  - Thêm consumption_alert mẫu (Phòng 102 spike tháng 7)
  - Tạo tài khoản user cho từng hộ (ho101/ho101, ho102/ho102,...)
"""
from datetime import date, datetime
from decimal import Decimal
from app import models
from app.security import hash_password


def seed_if_empty(db):
    if db.query(models.Household).count() > 0:
        print("[SEED] Data already exists, skipping.")
        return

    print("[SEED] Creating sample data...")

    # ── 1. Users ─────────────────────────────────────────────
    admin = models.User(username="admin", password=hash_password("admin123"),
                        full_name="Nguyễn Văn Quản Lý", role="admin")
    db.add(admin)
    db.flush()

    # ── 2. Households ─────────────────────────────────────────
    hh_data = [
        ("Phòng 101", "Trần Thị Bình",  "0901234567"),
        ("Phòng 102", "Lê Văn Cường",   "0912345678"),
        ("Phòng 201", "Phạm Thị Dung",  "0923456789"),
        ("Phòng 202", "Hoàng Văn Em",   "0934567890"),
    ]
    households = []
    for name, owner, phone in hh_data:
        h = models.Household(
            name=name, address="Số 12 Nguyễn Trãi, Q.1, TP.HCM",
            owner_name=owner, phone=phone,
            status="active", created_by=admin.id,
        )
        db.add(h)
        households.append(h)
    db.flush()

    # ── 2b. User accounts cho từng hộ ─────────────────────────
    user_accounts = [
        ("ho101", "ho101", "Trần Thị Bình",  households[0]),
        ("ho102", "ho102", "Lê Văn Cường",   households[1]),
        ("ho201", "ho201", "Phạm Thị Dung",  households[2]),
        ("ho202", "ho202", "Hoàng Văn Em",   households[3]),
    ]
    for uname, pwd, fname, hh in user_accounts:
        u = models.User(
            username=uname, password=hash_password(pwd),
            full_name=fname, role="user",
            household_id=hh.id,
        )
        db.add(u)
    db.flush()

    # ── 3. Meters ─────────────────────────────────────────────
    meters = {}   # { household.id: {electricity: Meter, water: Meter} }
    for i, h in enumerate(households):
        em = models.Meter(
            household_id=h.id, meter_type="electricity",
            meter_number=f"EVN-2026-{i+1:03d}", unit="kWh",
            installed_at=date(2026, 1, 1),
        )
        wm = models.Meter(
            household_id=h.id, meter_type="water",
            meter_number=f"SAW-2026-{i+1:03d}", unit="m3",
            installed_at=date(2026, 1, 1),
        )
        db.add_all([em, wm])
        meters[h.id] = {"electricity": em, "water": wm}
    db.flush()

    # ── 4. Utility Prices ─────────────────────────────────────
    # Điện bậc thang EVN 2024 (đơn vị: đồng/kWh)
    elec_tiers = [
        (1,   0,    50,  1728),
        (2,  50,   100,  1786),
        (3, 100,   200,  2074),
        (4, 200,   300,  2612),
        (5, 300,   400,  2919),
        (6, 400,  None,  3015),
    ]
    prices = {}  # { (meter_type, tier): UtilityPrice }
    for tier, mn, mx, ppu in elec_tiers:
        p = models.UtilityPrice(
            meter_type="electricity", tier=tier,
            min_unit=Decimal(str(mn)),
            max_unit=Decimal(str(mx)) if mx else None,
            price_per_unit=ppu,
            effective_from=date(2024, 1, 1),
        )
        db.add(p)
        prices[("electricity", tier)] = p

    # Nước flat-rate (SAWACO, đơn vị: đồng/m³)
    wp = models.UtilityPrice(
        meter_type="water", tier=1,
        min_unit=Decimal("0"), max_unit=None,
        price_per_unit=5973,
        effective_from=date(2024, 1, 1),
    )
    db.add(wp)
    prices[("water", 1)] = wp
    db.flush()

    # ── 5. Readings ───────────────────────────────────────────
    # Profile tiêu thụ theo hộ:
    #   H1 (101): bình thường, ổn định
    #   H2 (102): tháng 7 SPIKE (95 → 180 kWh điện)
    #   H3 (201): thấp, ổn định
    #   H4 (202): mới vào, chỉ có tháng 7
    profiles = {
        0: [  # Phòng 101
            ("2026-05", 1000, 1075,  75,  200,  215, 15),
            ("2026-06", 1075, 1150,  75,  215,  230, 15),
            ("2026-07", 1150, 1228,  78,  230,  246, 16),
        ],
        1: [  # Phòng 102 — spike tháng 7
            ("2026-05", 2000, 2095,  95,  400,  420, 20),
            ("2026-06", 2095, 2190,  95,  420,  440, 20),
            ("2026-07", 2190, 2370, 180,  440,  475, 35),  # SPIKE
        ],
        2: [  # Phòng 201 — tiêu thụ thấp
            ("2026-05",  500,  540,  40,  100,  108,  8),
            ("2026-06",  540,  578,  38,  108,  116,  8),
            ("2026-07",  578,  620,  42,  116,  124,  8),
        ],
        3: [  # Phòng 202 — mới vào
            ("2026-07",    0,   85,  85,    0,   12, 12),
        ],
    }

    readings_map = {}  # { (meter_id, period): Reading }
    for h_idx, h in enumerate(households):
        em = meters[h.id]["electricity"]
        wm = meters[h.id]["water"]
        for period, ep, ec, ec_c, wp_, wc, wc_c in profiles.get(h_idx, []):
            re_ = models.Reading(
                meter_id=em.id, period=period,
                prev_reading=Decimal(str(ep)),
                curr_reading=Decimal(str(ec)),
                consumption=Decimal(str(ec_c)),
                recorded_by=admin.id,
            )
            rw = models.Reading(
                meter_id=wm.id, period=period,
                prev_reading=Decimal(str(wp_)),
                curr_reading=Decimal(str(wc)),
                consumption=Decimal(str(wc_c)),
                recorded_by=admin.id,
            )
            db.add_all([re_, rw])
            readings_map[(em.id, period)] = re_
            readings_map[(wm.id, period)] = rw
    db.flush()

    # ── 6. Invoice + Items cho Phòng 101 tháng 7 ─────────────
    # Điện: 78 kWh → bậc 1 (50 kWh × 1728) + bậc 2 (28 kWh × 1786)
    #   bậc 1: subtotal=86400, vat=8640,  total=95040
    #   bậc 2: subtotal=50008, vat=5001,  total=55009
    #   tổng điện = 150049
    # Nước: 16 m³ × 5973 = 95568, vat=9557, total=105125
    # Grand total = 255174

    inv_101_07 = models.Invoice(
        household_id=households[0].id,
        period="2026-07",
        electricity_amount=150049,
        water_amount=105125,
        total_amount=255174,
        status="partial",
        due_date=date(2026, 8, 15),
        created_by=admin.id,
    )
    db.add(inv_101_07)
    db.flush()

    em_101 = meters[households[0].id]["electricity"]
    wm_101 = meters[households[0].id]["water"]
    r_elec = readings_map.get((em_101.id, "2026-07"))
    r_water = readings_map.get((wm_101.id, "2026-07"))

    items_101 = [
        models.InvoiceItem(
            invoice_id=inv_101_07.id,
            reading_id=r_elec.id if r_elec else None,
            price_id=prices[("electricity", 1)].id,
            description="Điện bậc 1 (0–50 kWh)",
            consumption=Decimal("50.00"),
            unit_price=1728, subtotal=86400,
            vat_rate=Decimal("0.1"), vat_amount=8640, total=95040,
        ),
        models.InvoiceItem(
            invoice_id=inv_101_07.id,
            reading_id=r_elec.id if r_elec else None,
            price_id=prices[("electricity", 2)].id,
            description="Điện bậc 2 (50–100 kWh, dùng 28 kWh)",
            consumption=Decimal("28.00"),
            unit_price=1786, subtotal=50008,
            vat_rate=Decimal("0.1"), vat_amount=5001, total=55009,
        ),
        models.InvoiceItem(
            invoice_id=inv_101_07.id,
            reading_id=r_water.id if r_water else None,
            price_id=prices[("water", 1)].id,
            description="Nước (16 m³)",
            consumption=Decimal("16.00"),
            unit_price=5973, subtotal=95568,
            vat_rate=Decimal("0.1"), vat_amount=9557, total=105125,
        ),
    ]
    db.add_all(items_101)

    # ── 7. Payment mẫu (trả 1 phần) ──────────────────────────
    pay1 = models.Payment(
        invoice_id=inv_101_07.id,
        amount_paid=100000,
        method="cash",
        note="Trả trước tiền mặt",
        recorded_by=admin.id,
    )
    db.add(pay1)

    # ── 8. Consumption Alert mẫu ──────────────────────────────
    em_102 = meters[households[1].id]["electricity"]
    alert = models.ConsumptionAlert(
        household_id=households[1].id,
        meter_id=em_102.id,
        period="2026-07",
        alert_type="spike",
        current_consumption=Decimal("180.00"),
        avg_consumption=Decimal("95.00"),
        percent_change=Decimal("89.47"),
        message="Tiêu thụ điện tháng 7 tăng 89.47% so với trung bình 2 tháng trước (95 kWh). Cần kiểm tra.",
        is_resolved=False,
    )
    db.add(alert)

    db.commit()
    print("[SEED] Done: 4 households | 8 meters | 7+1 price tiers | readings 3 months | 1 invoice | 1 spike alert")
    print("[SEED] Accounts:")
    print("  admin/admin123 (admin)")
    print("  ho101/ho101 (Phong 101)")
    print("  ho102/ho102 (Phong 102)")
    print("  ho201/ho201 (Phong 201)")
    print("  ho202/ho202 (Phong 202)")

