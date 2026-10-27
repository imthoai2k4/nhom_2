# KT1 — Hoàn thành ✅

**Ngày hoàn thành**: 2026-08-14  
**Giai đoạn**: KT1 — Phân tích & Thiết kế CSDL  
**Dự án**: Đề tài 48 — Hệ thống Quản lý Hóa đơn Điện nước có Tích hợp AI

---

## Tóm tắt giai đoạn KT1

> KT1 yêu cầu: *Dùng AI phân tích chỉ số, hóa đơn, thanh toán; thiết kế CSDL.*

AI (Antigravity) đã hỗ trợ:
- Phân tích nghiệp vụ: các loại chỉ số điện/nước, chu kỳ ghi, cấu trúc hóa đơn EVN/SAWACO
- Phân tích trạng thái thanh toán và workflow công nợ cho khu trọ Việt Nam
- Thiết kế CSDL **9 bảng** (v2), tối ưu cho SQLite, dễ chuyển PostgreSQL
- Xác định công thức tích tiền bậc thang điện EVN 2024

---

## Các file đã tạo

| File | Mô tả |
|------|-------|
| `main.py` | FastAPI entry point, mount static files, init DB, seed data |
| `requirements.txt` | Dependencies: FastAPI, SQLAlchemy, Gemini, pytest |
| `.env` / `.env.example` | Cấu hình API key và DB path |
| `start.bat` | Script cài deps + khởi động server 1 lệnh |
| `app/__init__.py` | Package init |
| `app/database.py` | SQLAlchemy engine, SessionLocal, `init_db()`, `get_db()` |
| `app/models.py` | **8 ORM models** đầy đủ quan hệ |
| `app/schemas.py` | Pydantic schemas (Base/Create/Update/Out) + validators |
| `app/auth.py` | Simple auth dùng header X-Username/X-Password |
| `app/seed.py` | Seed data: 4 hộ, 8 đồng hồ, chỉ số 3 tháng |
| `app/routers/__init__.py` | Package placeholder (KT2) |
| `app/services/__init__.py` | Package placeholder (KT2, KT3) |
| `tests/__init__.py` | Tests package (KT3) |
| `static/index.html` | HTML SPA shell |
| `static/css/style.css` | CSS dark mode, glassmorphism |
| `static/js/api.js` | Fetch wrapper với auto-auth headers |
| `static/js/app.js` | SPA router + Dashboard KT1 |

---

## Thiết kế CSDL — 8 bảng

```
USERS              → Tài khoản (admin / user)
HOUSEHOLDS         → Hộ/Phòng, quan hệ với USERS
METERS             → Đồng hồ điện/nước (electricity/water) của mỗi hộ
UTILITY_PRICES     → Đơn giá bậc thang + lịch sử (thêm ở v2)
READINGS           → Chỉ số ghi theo kỳ YYYY-MM, UNIQUE(meter_id, period)
INVOICES           → Hóa đơn tháng tổng hợp, UNIQUE(household_id, period)
INVOICE_ITEMS      → Chi tiết từng dòng hóa đơn, liên kết Reading + Price
PAYMENTS           → Lịch sử thanh toán (cash/transfer/other)
CONSUMPTION_ALERTS → Cảnh báo tiêu thụ (spike/negative/contradiction) (ẩ thêm ở v2)
```

---

## Công thức tính tiền (đã xác định tại KT1)

```
Tiêu thụ      = curr_reading - prev_reading

Điện (bậc thang EVN 2024):
  0–50 kWh   → 1.728 đ/kWh
  51–100 kWh → 1.786 đ/kWh
  101–200    → 2.074 đ/kWh
  201–300    → 2.612 đ/kWh
  301–400    → 2.919 đ/kWh
  >400       → 3.015 đ/kWh

Nước (flat rate) → đơn giá × tiêu thụ (SAWACO: ~5.973 đ/m³)
VAT              → 10% trên tổng trước thuế
Tổng hóa đơn    → tiền điện + tiền nước (đã gồm VAT)
```

---

## Dữ liệu seed mẫu

| Phòng | Profile tiêu thụ | Dùng để demo |
|-------|-----------------|--------------|
| Phòng 101 | Bình thường, ổn định (75 kWh/tháng) | Happy path |
| Phòng 102 | Tháng 7 tăng mạnh: 95→180 kWh | AI phát hiện bất thường |
| Phòng 201 | Thấp, ổn định (~40 kWh/tháng) | Hộ tiết kiệm |
| Phòng 202 | Chỉ có 1 kỳ (mới vào) | Edge case KT3 |

---

## Validation đã thiết lập trong schemas.py

- `curr_reading >= prev_reading` → `model_validator` Pydantic (sẽ test ở KT3)
- `curr_reading >= 0` → `ge=0` Pydantic field constraint
- `period` → regex `^\d{4}-(0[1-9]|1[0-2])$` validator
- `amount_paid > 0` → `gt=0`
- `UNIQUE(meter_id, period)` → SQLAlchemy `UniqueConstraint`
- `UNIQUE(household_id, period)` → SQLAlchemy `UniqueConstraint`
- `CHECK(curr_reading >= prev_reading)` → DB-level constraint

---

## Cách chạy KT1

```powershell
# 1. Điền GEMINI_API_KEY vào .env
# 2. Cài dependencies
pip install fastapi "uvicorn[standard]" sqlalchemy "pydantic>=2" python-dotenv google-generativeai python-multipart pytest

# 3. Khởi động server
python main.py

# 4. Mở trình duyệt
#    http://localhost:8000         → Dashboard
#    http://localhost:8000/docs    → Swagger UI
#    http://localhost:8000/api/health → Health check
```

---

## Bước tiếp theo → KT2

KT2 sẽ xây dựng:
- [ ] `app/routers/households.py` — CRUD hộ/phòng
- [ ] `app/routers/meters.py` — CRUD đồng hồ
- [ ] `app/routers/readings.py` — Nhập chỉ số + validation
- [ ] `app/routers/invoices.py` — Tự động tạo hóa đơn
- [ ] `app/routers/payments.py` — Ghi nhận thanh toán
- [ ] `app/routers/reports.py` — Thống kê, báo cáo
- [ ] `app/services/billing.py` — Tính tiền bậc thang + VAT
- [ ] Frontend CRUD pages đầy đủ

---

## Cập nhật v2 — Refactor theo thiết kế CSDL mới

**Ngày cập nhật**: 2026-08-14

### Thay đổi trong v2

| File | Thay đổi |
|------|----------|
| `app/models.py` | Rewrite — 9 bảng (thêm `UtilityPrice`, `ConsumptionAlert`), kiểu Integer/Numeric |
| `app/schemas.py` | Rewrite — dùng `int`/`Decimal`, `period: str` YYYY-MM, schemas mới |
| `app/seed.py` | Rewrite — thêm utility_prices bậc thang, invoice_items, alert mẫu |

### Lý do thay đổi
- **Kiểu tiền tệ**: `Float` → `Integer` (đồng) — tránh sai số số thực
- **Kiểu chỉ số**: `Float` → `Numeric(12,2)` / `Decimal`
- **Kỳ tháng**: `period_month + period_year` → `period CHAR(7)` ('2026-07')
- **Đơn giá**: tách ra bảng `utility_prices` riêng (bậc thang + lịch sử)
- **Ràng buộc**: thêm `UNIQUE(meter_id, period)`, `UNIQUE(household_id, period)`, CheckConstraints
- **Cảnh báo**: bảng `consumption_alerts` với 3 loại: spike/negative/contradiction
