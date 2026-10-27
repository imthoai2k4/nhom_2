# KT2 Blueprint — CRUD & Debug Công thức

**Dự án**: Đề tài 48 — Hệ thống Quản lý Hóa đơn Điện nước  
**Giai đoạn**: KT2  
**Stack**: FastAPI + SQLAlchemy + SQLite + HTML/Vanilla JS + Simple Auth

---

## 1. Cấu trúc thư mục

```
d:\Duan_48\
├── main.py
├── app/
│   ├── models.py / schemas.py / auth.py / seed.py   (✅ v2)
│   ├── routers/           ← KT2 tạo mới
│   │   ├── auth.py        M1: Login/logout
│   │   ├── households.py  M2: CRUD hộ/phòng
│   │   ├── meters.py      M3: CRUD đồng hồ
│   │   ├── readings.py    M4: Nhập/sửa chỉ số
│   │   ├── prices.py      M5: Quản lý đơn giá
│   │   ├── invoices.py    M6: Tạo/xem hóa đơn
│   │   └── payments.py    M7: Thanh toán + công nợ
│   └── services/
│       ├── billing.py        Tính tiền bậc thang + VAT
│       └── alert_service.py  Phát hiện spike
│
├── static/js/pages/   ← KT2 tạo mới
│   ├── auth.js / households.js / meters.js
│   ├── readings.js / prices.js
│   ├── invoices.js / payments.js
│
└── tests/   (KT3)
```

---

## 2. Danh sách API REST

### M1 — Auth

| Method | URL | Quyền | Request | Response | Lỗi |
|--------|-----|-------|---------|----------|-----|
| POST | `/api/auth/login` | Public | `{username, password}` | `{success, role, username}` | 401 |
| POST | `/api/auth/logout` | Any | — | `{message}` | — |
| GET | `/api/auth/me` | Any | Header | `UserOut` | 401 |

### M2 — Hộ/Phòng

| Method | URL | Quyền | Request | Response | Lỗi |
|--------|-----|-------|---------|----------|-----|
| GET | `/api/households` | Any | `?status=active` | `List[HouseholdOut]` | — |
| GET | `/api/households/{id}` | Any | — | `HouseholdOut` | 404 |
| POST | `/api/households` | admin | `HouseholdCreate` | `HouseholdOut` | 422 |
| PUT | `/api/households/{id}` | admin | `HouseholdUpdate` | `HouseholdOut` | 404, 422 |
| DELETE | `/api/households/{id}` | admin | — | `{message}` | 404, 409 |

### M3 — Đồng hồ

| Method | URL | Quyền | Request | Response | Lỗi |
|--------|-----|-------|---------|----------|-----|
| GET | `/api/meters` | Any | `?household_id=&type=` | `List[MeterOut]` | — |
| GET | `/api/meters/{id}` | Any | — | `MeterOut` | 404 |
| POST | `/api/meters` | admin | `MeterCreate` | `MeterOut` | 409 trùng số |
| PUT | `/api/meters/{id}` | admin | `MeterUpdate` | `MeterOut` | 404 |
| DELETE | `/api/meters/{id}` | admin | — | `{message}` | 409 có readings |

### M4 — Chỉ số

| Method | URL | Quyền | Request | Response | Lỗi |
|--------|-----|-------|---------|----------|-----|
| GET | `/api/readings` | Any | `?meter_id=&period=&household_id=` | `List[ReadingOut]` | — |
| GET | `/api/readings/{id}` | Any | — | `ReadingOut` | 404 |
| GET | `/api/readings/last/{meter_id}` | Any | — | `ReadingOut` | 404 |
| POST | `/api/readings` | admin | `ReadingCreate` | `ReadingOut` | 409 trùng, 422 curr<prev |
| PUT | `/api/readings/{id}` | admin | `{curr_reading}` | `ReadingOut` | 404, 422, 409 đã có HD |
| GET | `/api/readings/history/{household_id}` | Any | `?months=6` | lịch sử + avg | — |

### M5 — Đơn giá

| Method | URL | Quyền | Request | Response | Lỗi |
|--------|-----|-------|---------|----------|-----|
| GET | `/api/prices` | Any | `?meter_type=&active=true` | `List[UtilityPriceOut]` | — |
| POST | `/api/prices` | admin | `UtilityPriceCreate` | `UtilityPriceOut` | 409 trùng |
| PUT | `/api/prices/{id}` | admin | `{effective_to}` | `UtilityPriceOut` | 404 |

### M6 — Hóa đơn

| Method | URL | Quyền | Request | Response | Lỗi |
|--------|-----|-------|---------|----------|-----|
| GET | `/api/invoices` | Any | `?household_id=&period=&status=` | `List[InvoiceOut]` | — |
| GET | `/api/invoices/{id}` | Any | — | `InvoiceOut + items` | 404 |
| POST | `/api/invoices/generate` | admin | `{household_id, period}` | `InvoiceOut` | 409 tồn tại, 400 thiếu readings |
| POST | `/api/invoices/generate-all` | admin | `{period}` | `List[InvoiceOut]` | — |
| PUT | `/api/invoices/{id}/status` | admin | `InvoiceStatusUpdate` | `InvoiceOut` | 404 |
| DELETE | `/api/invoices/{id}` | admin | — | `{message}` | 409 có payment |

### M7 — Thanh toán & Công nợ

| Method | URL | Quyền | Request | Response | Lỗi |
|--------|-----|-------|---------|----------|-----|
| GET | `/api/payments` | Any | `?invoice_id=` | `List[PaymentOut]` | — |
| POST | `/api/payments` | admin | `PaymentCreate` | `PaymentOut` | 400 vượt tổng |
| GET | `/api/reports/debt` | Any | `?household_id=` | `List[DebtReport]` | — |
| GET | `/api/reports/revenue` | admin | `?period=` | `MonthlyRevenueReport` | — |
| GET | `/api/reports/summary` | admin | — | `SystemSummary` | — |

---

## 3. Màn hình Frontend

### P1 — Login (`auth.js`)
- Form username + password
- POST `/api/auth/login` → lưu role + credentials vào `localStorage`
- Redirect Dashboard nếu thành công, lỗi inline nếu sai

### P2 — Hộ/Phòng (`households.js`)
- Bảng: Tên, Địa chỉ, Chủ hộ, SĐT, Trạng thái, Actions
- Filter: status dropdown | Button **Thêm hộ** → Modal form
- Mỗi dòng: Sửa (modal), Xóa (confirm), Xem đồng hồ
- Badge màu theo status (active=xanh, inactive=xám)

### P3 — Đồng hồ (`meters.js`)
- Filter theo hộ (dropdown), loại (điện/nước)
- Bảng: Số đồng hồ, Loại (⚡/💧), Đơn vị, Ngày lắp
- Thêm/Sửa qua modal

### P4 — Nhập Chỉ số (`readings.js`)
- **Form nhập**: chọn hộ → chọn đồng hồ → nhập kỳ YYYY-MM + chỉ số mới
  - Auto-fetch chỉ số kỳ trước (GET `/last/{meter_id}`)
  - Preview realtime: tiêu thụ = curr - prev
  - Validation inline: curr < prev → input đỏ + tooltip
- **Bảng lịch sử**: filter hộ/kỳ, sparkline mini tiêu thụ

### P5 — Đơn giá (`prices.js`)
- Tab Điện: bảng 6 bậc (bậc, từ-đến kWh, giá/kWh, kỳ áp dụng)
- Tab Nước: flat-rate hiện tại
- Admin: Thêm bậc mới / đóng bậc cũ (set effective_to)

### P6 — Hóa đơn (`invoices.js`)
- Filter: hộ, kỳ, trạng thái
- Bảng: Hộ, Kỳ, Điện, Nước, Tổng, Trạng thái (badge màu), Hạn TT
- Button **Tạo HĐ** (chọn hộ + kỳ) hoặc **Tạo tất cả** (chỉ nhập kỳ)
- Click dòng → Modal chi tiết: invoice_items + danh sách payments

### P7 — Thanh toán & Công nợ (`payments.js`)
- **Tab Ghi nhận**: chọn hóa đơn → nhập số tiền + phương thức
  - Hiển thị "còn nợ = total - đã trả"
  - Cảnh báo vàng nếu nhập > còn nợ
- **Tab Công nợ**: bảng tổng hợp theo hộ, sort theo công nợ giảm dần

---

## 4. Quy tắc Validation

### Backend (2 lớp)

| Field | Rule | Layer | HTTP |
|-------|------|-------|------|
| `period` | regex `^\d{4}-(0[1-9]\|1[0-2])$` | Pydantic | 422 |
| `curr_reading` | `>= prev_reading` | Pydantic model_validator | 422 |
| `curr_reading` | `>= 0` | Pydantic ge=0 | 422 |
| `amount_paid` | `> 0` | Pydantic gt=0 | 422 |
| `amount_paid` | `<= (total - đã trả)` | Service | 400 |
| `(meter_id, period)` | unique | DB UNIQUE | 409 |
| `(household_id, period)` | unique | DB UNIQUE | 409 |
| Xóa hộ | không có invoice | Service | 409 |
| Sửa reading | chưa có invoice | Service | 409 |
| Xóa invoice | chưa có payment | Service | 409 |

### Frontend (realtime JS)

| Tình huống | Phản hồi UI |
|-----------|-------------|
| curr < prev | Input đỏ + tooltip lỗi |
| curr < 0 | Input đỏ ngay |
| period sai format | Hint "Nhập dạng YYYY-MM" |
| amount > còn nợ | Input vàng + cảnh báo |
| Lỗi 409 từ server | Toast error: "Đã tồn tại trong kỳ này" |
| Lỗi 422 từ server | Highlight field tương ứng |

---

## 5. Thứ tự triển khai

```
Bước 1  services/billing.py
        Không phụ thuộc gì — phải có trước invoices
        Hàm: calc_electricity(consumption, prices) → items + total
        Hàm: calc_water(consumption, price) → item + total

Bước 2  routers/auth.py + pages/auth.js
        Độc lập — test login ngay

Bước 3  routers/households.py + pages/households.js
        Phụ thuộc: auth

Bước 4  routers/meters.py + pages/meters.js
        Phụ thuộc: households

Bước 5  routers/prices.py + pages/prices.js
        Độc lập — nhưng phải có trước invoices

Bước 6  routers/readings.py + pages/readings.js
        Phụ thuộc: meters, prices
        + services/alert_service.py (kiểm tra spike sau nhập)

Bước 7  routers/invoices.py + pages/invoices.js
        Phụ thuộc: households, readings, billing.py, prices
        Logic: generate_invoice() → gọi billing.py → insert items

Bước 8  routers/payments.py + pages/payments.js
        Phụ thuộc: invoices
        Logic sau insert: cập nhật invoice.status (partial/paid)

Bước 9  Bỏ comment include_router trong main.py

Bước 10 Cập nhật app.js: đăng ký 7 pages mới vào SPA router
```

---

## 6. Phân công AI vs Lập trình viên

### AI sinh tốt — tin cậy cao

| Phần | Prompt mẫu |
|------|-----------|
| CRUD boilerplate 5 endpoints | "Viết FastAPI router CRUD Household theo schema HouseholdCreate/Out, dùng get_db dependency" |
| Pydantic → SQLAlchemy filter | "Viết hàm filter readings theo household_id và period" |
| HTML table + modal form | "Tạo JS page households.js dùng API wrapper đã có, style từ style.css" |
| Error handler 404/409/422 | "Thêm HTTPException handler chuẩn FastAPI cho router" |
| SQL aggregate (debt report) | "Viết SQLAlchemy query tính công nợ theo hộ" |

### AI sinh được — LTV phải kiểm tra kỹ

| Phần | Rủi ro |
|------|--------|
| `billing.py` bậc thang | Sai biên (≤50 hay <50?), sai làm tròn Integer |
| `generate_invoice()` | Logic nhiều bước, dễ bỏ sót edge case |
| Cập nhật status sau payment | Điều kiện partial/paid phải chính xác |
| `alert_service.py` tính TB | SQLite không có window function → tính bằng Python |
| Cascade delete | Kiểm tra thứ tự xóa không phá quan hệ |

### LTV phải tự kiểm tra thủ công

| Phần | Lý do |
|------|-------|
| Tính tiền 78 kWh = ? | Đối chiếu hóa đơn EVN thật: 50×1728 + 28×1786 = 136.408đ → VAT → 150.049đ |
| Tính tiền 180 kWh (Phòng 102) | Nhiều bậc, phải tính từng khoảng rồi cộng |
| Invoice.status sau nhiều payments | Test: TT 2 lần, lần 3 đủ tổng → phải thành "paid" |
| Quyết định VAT: per-item hay tổng | Ảnh hưởng làm tròn — chọn per-item rồi cố định |

---

## Đề xuất bổ sung

**1. GET `/api/readings/last/{meter_id}`** — trả chỉ số mới nhất để pre-fill form nhập.

**2. POST `/api/invoices/generate-all`** — tạo hóa đơn 1 lần cho tất cả hộ active trong kỳ.

**3. Auto-update invoice.status** — sau mỗi POST payment, service tính lại `SUM(paid)` và tự cập nhật status thay vì để admin tự PUT.

**4. Soft delete** — xóa hộ/đồng hồ chỉ set `is_active=False`, không xóa vật lý để bảo toàn lịch sử.

**5. Pagination chuẩn** — tất cả GET list trả `{items, total, page, size, pages}` thay vì list thô.

**6. Thêm index DB** — `readings(period)`, `invoices(status, period)` cho query nhanh hơn khi dữ liệu lớn.
