# Test Report — UtilityAI

**Ngày chạy:** 2026-10-28  
**Lệnh:** `python -m pytest -q`  
**Kết quả:** **97 passed** (0 failed)

## 1. Tổng hợp theo file

| File | Số test | Nội dung |
|---|---:|---|
| `tests/test_ai.py` | 32 | Prompt, mock analysis, retry/fallback, metadata, giới hạn độ dài |
| `tests/test_chat_ai.py` | 7 | Chat general dùng AI, fallback, phân quyền context, prompt guard |
| `tests/test_crud.py` | 26 | Công thức tiêu thụ/hóa đơn/công nợ, intent, edge cases |
| `tests/test_api_ai.py` | 13 | API AI: quyền, validate months, cache, metadata, headers/CORS |
| `tests/test_billing.py` | 6 | Bậc thang EVN, VAT, nước |
| `tests/test_alerts.py` | 5 | Ngưỡng 49/50/51%, thiếu lịch sử, avg = 0 |
| `tests/test_security.py` | 5 | Hash/verify, legacy migration, rate limiter |
| `tests/test_seed_demo.py` | 3 | Dữ liệu demo 6 kỳ, idempotent, cộng đủ thanh toán/công nợ |
| **Tổng** | **97** | |

## 2. Nhóm theo mục tiêu

| Nhóm | Test tiêu biểu | Kết quả |
|---|---|---|
| AI output | TC-AI-013/014/023–027/032/033 | Pass |
| Ngưỡng cảnh báo | TC-AI-029/030, TC-ALERT-001–005 | Pass |
| API AI | TC-API-AI-001–010 | Pass |
| Chat AI | TC-CHAT-013–019 | Pass |
| Hóa đơn | TC-BILL-001–006, TC-CRUD-008 | Pass |
| Bảo mật | TC-SEC-001–005 | Pass |

## 3. Các lỗi đã từng phát hiện và test hồi quy

| Lỗi | Test hồi quy |
|---|---|
| Output AI bị cắt do `max_tokens` | TC-AI-013/014, TC-AI-027 |
| Thiếu mục/kết thúc giữa từ | TC-AI-023/024/032 |
| Fallback báo ngược chiều DESC | TC-AI-028/029 |
| Chat không gọi AI | TC-CHAT-013/019 |
| User không gán hộ thấy dữ liệu | TC-API-AI-005 |
| Cache không dùng lại | TC-API-AI-007 |
| Bậc thang sai giá | TC-BILL-002–005, TC-CRUD-008 |
| Plaintext password | TC-SEC-001–003 |

## 4. Ghi chú

- 23 warning là deprecation của Pydantic/Starlette, không phải test fail.
- Test AI dùng mock cho lớp client; test live được thực hiện thủ công với Qwen3.8-27B (xem `docs/manual-test-checklist.md`).
- Test API dùng SQLite in-memory + `StaticPool`, không ghi vào DB thật.
- Chạy lại sau mỗi thay đổi:

```powershell
python -m pytest -q
```
