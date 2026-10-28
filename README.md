# UtilityAI — Quản lý Hóa đơn Điện nước Hộ gia đình tích hợp AI

Hệ thống quản lý hộ/phòng, đồng hồ, chỉ số, hóa đơn, thanh toán, công nợ và phân tích tiêu thụ bằng AI (Qwen3.8-27B qua API chuẩn OpenAI).

## Tính năng

- Đăng nhập, phân quyền Admin / User theo hộ.
- CRUD hộ/phòng, đồng hồ, chỉ số, đơn giá bậc thang EVN + nước.
- Tính hóa đơn, VAT, thanh toán một phần/toàn bộ, báo cáo công nợ.
- Cảnh báo tiêu thụ tăng > 50% so với trung bình 3 kỳ.
- **Phân tích AI**: nhận xét 5 mục (tổng quan, biến động, cảnh báo, gợi ý, chi phí), retry/fallback, log token/thời gian.
- **Chat AI**: câu hỏi tự do dùng model; tra cứu có cấu trúc vẫn rule-based; context lọc theo quyền.
- Cache kết quả AI 5 phút + cooldown UI 10 giây để tránh rate limit.
- Bảo mật cơ bản: hash mật khẩu PBKDF2, CORS allowlist, rate limit, security headers.

## Stack

- Backend: FastAPI 0.115, SQLAlchemy 2, SQLite (WAL)
- Frontend: HTML/CSS/Vanilla JS (SPA)
- AI: OpenAI-compatible API, model `qwen3.8-27b`
- Test: pytest

## Cấu trúc

```
app/
  routers/        API (auth, households, meters, readings, prices, invoices, payments, ai, chat)
  services/       ai_client, ai_service, chat_service, billing, alert_service, prompt_loader
  models.py       SQLAlchemy models
  schemas.py      Pydantic schemas
  auth.py         xác thực + phân quyền
static/           giao diện SPA
tests/            test AI, API, billing, alert, chat, security
prompts/          prompt tách khỏi code (v3)
docs/             báo cáo, manual test, minh chứng
deploy/           nginx, systemd, logrotate
tools/            backup DB, prompt experiments, design doc
```

## Chạy nhanh

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# điền AI_API_KEY vào .env

python main.py
```

Mở http://localhost:8000.

### Tài khoản demo

| Vai trò | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Hộ 101 | `ho101` | `ho101` |
| Hộ 102 | `ho102` | `ho102` |
| Hộ 201 | `ho201` | `ho201` |
| Hộ 202 | `ho202` | `ho202` |

> Đổi mật khẩu trước khi triển khai thật.

## Cấu hình `.env`

```env
AI_API_KEY=...
AI_BASE_URL=https://discovery-api.intern-ai.org.cn/v1
AI_MODEL=qwen3.8-27b
AI_TIMEOUT=30
AI_MAX_TOKENS=4096

DATABASE_URL=sqlite:///./utility_mgmt.db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
SEED_DEMO_DATA=1
```

- `AI_CACHE_TTL` (mặc định 300 giây)
- `AI_RATE_LIMIT` / `CHAT_RATE_LIMIT` (request/phút)
- `ENABLE_HSTS=1` khi chạy HTTPS

## Test

```powershell
python -m pytest -q
```

Kết quả hiện tại: **94 passed**. Chi tiết: [docs/test-report.md](docs/test-report.md).

## API chính

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/auth/login` | Đăng nhập |
| GET | `/api/households` | Danh sách hộ |
| POST | `/api/readings` | Nhập chỉ số |
| POST | `/api/invoices/generate` | Tạo hóa đơn |
| POST | `/api/payments` | Ghi thanh toán |
| POST | `/api/ai/analyze` | Phân tích AI |
| POST | `/api/chat/message` | Chat AI |

Swagger: http://localhost:8000/docs

## Tài liệu

- [MUC_CON_THIEU.md](MUC_CON_THIEU.md) — checklist P0/P1/P2
- [TIEN_DO.md](TIEN_DO.md) — tiến độ
- [docs/manual-test-checklist.md](docs/manual-test-checklist.md) — kiểm thử tay
- [docs/demo-script.md](docs/demo-script.md) — kịch bản demo 7 phút
- [docs/test-report.md](docs/test-report.md) — báo cáo test
- [docs/prompt-experiments.md](docs/prompt-experiments.md) — thực nghiệm prompt + transcript
- [docs/ai-review/README.md](docs/ai-review/README.md) — minh chứng AI code review
- [docs/venv-check.md](docs/venv-check.md) — kiểm tra dependency/venv
- [docs/UtilityAI_Slide.pptx](docs/UtilityAI_Slide.pptx) — slide báo cáo cuối kỳ
- [deploy/README.md](deploy/README.md) — triển khai production

## Hạn chế

- Auth demo dùng header `X-Username`/`X-Password`; production nên chuyển JWT/session + HTTPS.
- SQLite phù hợp demo nhỏ; nhiều người dùng nên chuyển PostgreSQL.
- AI có thể sai/không đủ dữ liệu; hệ thống có fallback nội bộ và cảnh báo trên UI.
