# AI Review Transcript (chuẩn hóa)

**Công cụ:** Google Gemini 2.5 Flash  
**Phạm vi:** `main.py`, `app/services/ai_service.py`, `app/services/chat_service.py`, `app/auth.py`, `app/routers/ai_analysis.py`, `app/routers/chat.py`  
**Ngày:** 2026-09-15 → 2026-09-18

## Prompt đã dùng

```text
Bạn là senior Python reviewer cho dự án FastAPI + SQLAlchemy + AI.
Hãy review các file sau theo thứ tự:
1. Lỗi tương thích thư viện / runtime.
2. Xử lý lỗi khi gọi AI (timeout, rate limit, response rỗng).
3. Bảo mật API key và phân quyền dữ liệu.
4. Đề xuất refactor làm rõ trách nhiệm.

Với mỗi lỗi, trả về: file, mô tả, mức độ, đoạn code trước/sau.
Không bịa file hoặc dòng nếu không có trong ngữ cảnh.
```

## Kết quả tóm tắt

### 1. `on_startup` deprecated

> “Starlette mới đã bỏ `on_startup`; FastAPI 0.115 nên dùng `lifespan`.”

**Sửa:** chuyển sang `@asynccontextmanager lifespan(app)` trong `main.py`.

### 2. Bắt tất cả lỗi AI chung chung

> “`except Exception` gộp timeout, 429, key sai, lỗi model vào một thông báo.
> Cần phân loại để người dùng biết retry hay dừng.”

**Sửa:** `AIError(kind=...)` + `_error_fallback` theo từng loại.

### 3. Không kiểm tra response rỗng

> “Gemini có thể trả `None`/chuỗi rỗng khi bị safety filter. Cần kiểm tra trước khi trả UI.”

**Sửa:** kiểm tra rỗng, độ dài, 5 mục, kết thúc câu; retry/fallback.

### 4. Thiếu timeout

> “Gọi external API không timeout có thể treo worker.”

**Sửa:** `OpenAI(timeout=30)`, `AsyncOpenAI(timeout=30)` trong `ai_client.py`.

### 5. API key trong `.env`

> “Đảm bảo `.env` nằm trong `.gitignore`, chỉ commit `.env.example`; nếu lộ thì revoke.”

**Sửa:** `.env` bị ignore; key cũ đã xóa; dùng `AI_API_KEY`.

### 6. Phân quyền không nhất quán

> “Một số router so sánh `current_user.household_id` mà không kiểm tra `None`,
> user chưa gán hộ có thể thấy dữ liệu mọi hộ.”

**Sửa:** `get_household_filter` trả 403 nếu user không có hộ; chat có guard tương tự.

## Ghi chú

- Đây là bản ghi chuẩn hóa từ nội dung review đã thực hiện; không phải raw chat nguyên văn.
- Không có API key trong tài liệu.
- Các đoạn code Before/After đầy đủ nằm trong [../../ai_code_review.md](../../ai_code_review.md).
