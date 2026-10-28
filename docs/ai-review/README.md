# Minh chứng AI Code Review

**Công cụ:** Google Gemini 2.5 Flash (giai đoạn review), sau đó dự án chuyển sang Qwen3.8-27B.  
**Tài liệu gốc:** [../../ai_code_review.md](../../ai_code_review.md)  
**Bản ghi:** [transcript.md](transcript.md)

> Ghi chú: phiên chat gốc không được lưu tự động; `transcript.md` là bản ghi chuẩn hóa từ
> nội dung review đã thực hiện, kèm prompt đã dùng và kết luận từng lỗi. Không bao gồm API key.

## Bảng issue → file → mức độ → trạng thái

| # | Lỗi | File | Mức độ | Trạng thái | Bằng chứng |
|---|---|---|---|---|---|
| 1 | `on_startup` deprecated, lỗi Starlette | `main.py` | Nghiêm trọng | Đã sửa | `lifespan` context manager trong `main.py` |
| 2 | Bắt tất cả lỗi AI chung chung | `app/services/ai_service.py` | Quan trọng | Đã sửa | `AIError.kind` + `_error_fallback` |
| 3 | Không kiểm tra response rỗng/ngắn | `app/services/ai_service.py` | Quan trọng | Đã sửa | `_is_complete` + fallback |
| 4 | Thiếu timeout khi gọi API | `app/services/ai_client.py` | Quan trọng | Đã sửa | `timeout=cfg.timeout` (30s) |
| 5 | Nguy cơ lộ API key | `.env`, `.gitignore` | Bảo mật | Đã sửa | `.env` bị ignore; chỉ commit `.env.example` |
| 6 | Phân quyền không nhất quán | `app/auth.py` + routers | Bảo mật | Đã sửa | `get_household_filter` 403 nếu user không có hộ |

## Commit liên quan

- `25db1c9` — P0-01: kiểm tra output/fallback/logging.
- `a94723d` — P0-02: sửa chiều so sánh fallback.
- `6bce444` — P0-03: chat AI + context phân quyền + prompt guard.
- `3427fe5` — chuyển provider sang OpenAI-compatible Qwen3.8-27B.
- Các thay đổi P1/P2 (hash password, rate limit, test API…) nằm trong working tree/commit tiếp theo.

## Kết luận

- 6/6 lỗi review đã được xử lý.
- Các test hồi quy tương ứng nằm trong `tests/test_ai.py`, `tests/test_chat_ai.py`, `tests/test_api_ai.py`, `tests/test_security.py`.
