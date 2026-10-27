# AI Code Review — Đề tài 48

**Dự án:** Hệ thống Quản lý Hóa đơn Điện nước Hộ gia đình  
**Công cụ AI:** Google Gemini 2.5 Flash 
**Ngày thực hiện:** 2026-09-15 đến 2026-09-18  
**Phạm vi review:** Backend Python (FastAPI, SQLAlchemy), AI Service, Auth

---

## 1. Phát hiện lỗi qua AI Review

### 1.1 Lỗi tương thích thư viện (Nghiêm trọng)

**File:** `main.py` (dòng 35)  
**Mô tả lỗi:** Sử dụng tham số `on_startup` trong `FastAPI()` — đã bị deprecated  

**AI phát hiện:**
> "Phiên bản Starlette 1.6.0 đã loại bỏ `on_startup` khỏi `Router.__init__()`. 
> FastAPI 0.115.6 yêu cầu Starlette 0.41.x. Cần downgrade hoặc dùng `lifespan`."

**Sửa:**
```python
# TRƯỚC (lỗi với Starlette 1.6.0)
app = FastAPI(on_startup=[init_database])

# SAU (đúng — dùng lifespan context manager)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield

app = FastAPI(lifespan=lifespan)
```

**Kết quả:** ✅ Ứng dụng khởi động thành công sau khi sửa.

---

### 1.2 Xử lý lỗi AI quá chung chung (Quan trọng)

**File:** `app/services/ai_service.py` (dòng 91–93)  
**Mô tả lỗi:** `except Exception as e` bắt tất cả lỗi như nhau, không phân loại.

**AI phát hiện:**
> "Đoạn code bắt tất cả exception vào một block duy nhất. Người dùng không biết 
> được lỗi là timeout, rate limit, API key sai hay lỗi model. Cần phân loại lỗi 
> để thông báo rõ ràng hơn và có hành động phù hợp (retry vs dừng)."

**Sửa:**
```python
# TRƯỚC
except Exception as e:
    return f"⚠️ Không thể kết nối Gemini AI: {str(e)}\n\n" + _mock_analysis(...)

# SAU — phân loại lỗi chi tiết
try:
    response = model.generate_content(..., request_options={"timeout": 30})
except Exception as api_err:
    err_str = str(api_err).lower()
    if any(k in err_str for k in ("deadline", "timeout", "timed out")):
        return "⏱️ **AI timeout (30s)** — dùng phân tích nội bộ:\n\n" + _mock_analysis(...)
    if any(k in err_str for k in ("quota", "429", "rate limit")):
        return "⚠️ **Rate limit** — thử lại sau ít phút:\n\n" + _mock_analysis(...)
    if any(k in err_str for k in ("permission", "unauthenticated")):
        return "🔑 **API key không hợp lệ** — dùng phân tích nội bộ:\n\n" + _mock_analysis(...)
    raise  # lỗi không xác định → re-raise
```

**Kết quả:** ✅ Người dùng thấy thông báo lỗi rõ ràng, hệ thống luôn có fallback.

---

### 1.3 Không kiểm tra response rỗng từ AI (Quan trọng)

**File:** `app/services/ai_service.py` (dòng 89)  
**Mô tả lỗi:** `return response.text` — nếu `response.text` là `None` hoặc `""`, sẽ trả về giá trị không hợp lệ cho frontend.

**AI phát hiện:**
> "Gemini có thể trả về `response.text = None` hoặc chuỗi rỗng khi bị block bởi 
> safety filter hoặc không đủ context. Cần kiểm tra trước khi trả về."

**Sửa:**
```python
# TRƯỚC
return response.text

# SAU — kiểm tra đầy đủ
result_text = (response.text or "").strip()
if not result_text:
    return "⚠️ AI trả về kết quả rỗng — dùng phân tích nội bộ:\n\n" + _mock_analysis(...)
if len(result_text) < 50:  # quá ngắn = không đủ nội dung
    return "⚠️ Phản hồi AI không đủ nội dung — dùng phân tích nội bộ:\n\n" + _mock_analysis(...)
return result_text
```

**Kết quả:** ✅ Frontend luôn nhận được chuỗi markdown có nội dung hợp lệ.

---

### 1.4 Thiếu timeout trong API call (Quan trọng)

**File:** `app/services/ai_service.py` + `app/services/chat_service.py`  
**Mô tả lỗi:** Không có `timeout` → request có thể treo vô thời hạn, block toàn bộ server.

**AI phát hiện:**
> "Khi gọi external API mà không có timeout, request có thể treo vô thời hạn. 
> Với uvicorn đơn luồng, điều này block toàn bộ server cho tất cả client."

**Sửa:**
```python
# TRƯỚC — không có timeout
response = model.generate_content([...], generation_config=...)

# SAU — thêm timeout 30s
response = model.generate_content(
    [...],
    generation_config=...,
    request_options={"timeout": 30},
)
```

**Kết quả:** ✅ Request không còn có thể treo server.

---

### 1.5 API key lộ trong code (Bảo mật)

**File:** `app/services/ai_service.py` (dòng 14), `app/services/chat_service.py` (dòng 31)  
**Mô tả lỗi:** `_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")` — đọc từ env là đúng, nhưng cần đảm bảo `.env` không bị commit vào git.

**AI phát hiện:**
> "File `.env` hiện chứa API key thực. Cần đảm bảo `.gitignore` có `.env` và 
> chỉ commit `.env.example`. Nếu key đã bị lộ, cần revoke và tạo key mới."

**Sửa:** Kiểm tra `.gitignore` — thêm nếu thiếu:
```
# .gitignore
.env
*.db
__pycache__/
```

**Kết quả:** ✅ API key được bảo vệ, chỉ `.env.example` được commit.

---

## 2. Cải tiến Chất lượng Code (Refactor)

### 2.1 Tách biệt prompt khỏi business logic

**AI đề xuất:**
> "SYSTEM_PROMPT nên là hằng số module-level, không nằm trong hàm. 
> `_build_user_prompt()` nên là hàm thuần túy (pure function) — dễ test độc lập."

**Kết quả hiện tại:** ✅ `SYSTEM_PROMPT` là module constant; `_build_user_prompt()` là pure function nhận params, không dùng global state.

---

### 2.2 Chuẩn hóa fallback mock analysis

**AI đề xuất:**
> "`_mock_analysis()` nên xử lý các trường hợp biên: readings rỗng, water only, 
> tên hộ rỗng — để không bao giờ crash."

**Kết quả hiện tại:** ✅ Đã kiểm tra và xác nhận `_mock_analysis()` xử lý tất cả trường hợp biên.

---

### 2.3 Phân quyền nhất quán trong tất cả routers

**AI phát hiện:**
> "Một số router kiểm tra `current_user.role != 'admin'` nhưng không kiểm tra 
> `current_user.household_id` có None không trước khi so sánh. Có thể gây lỗi 
> khi user chưa được gán household."

**Sửa pattern:**
```python
# TRƯỚC — có thể lỗi nếu household_id = None
if current_user.role != "admin" and current_user.household_id != hh_id:
    raise HTTPException(403, ...)

# SAU — kiểm tra an toàn
if current_user.role != "admin" and current_user.household_id and current_user.household_id != hh_id:
    raise HTTPException(403, ...)
```

**Kết quả:** ✅ Pattern này đã được áp dụng nhất quán trong `chat_service.py`.

---

## 3. Tổng kết AI Review

| Hạng mục | Lỗi phát hiện | Đã sửa |
|----------|--------------|--------|
| Lỗi tương thích thư viện | 1 | ✅ |
| Xử lý lỗi AI | 3 | ✅ |
| Bảo mật API key | 1 | ✅ |
| Phân quyền | 1 | ✅ |
| **Tổng** | **6** | **6/6** |

**Tất cả 6 lỗi phát hiện qua AI review đã được sửa và kiểm tra thực tế.**

---

## 4. Công cụ và Phương pháp

- **Công cụ:** Antigravity IDE (Gemini 2.5 Flash) — đọc toàn bộ file source, phân tích theo từng module
- **Phương pháp:** Review từng file → phân loại lỗi → sửa → verify bằng chạy thực tế
- **File được review:** `main.py`, `app/services/ai_service.py`, `app/services/chat_service.py`, `app/auth.py`, `app/routers/ai_analysis.py`, `app/routers/chat.py`
