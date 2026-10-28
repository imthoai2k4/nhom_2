# MỤC CÒN THIẾU — KẾ HOẠCH BỔ SUNG TRƯỚC KHI TRIỂN KHAI

**Dự án:** Hệ thống Quản lý Hóa đơn Điện nước Hộ gia đình có tích hợp AI (Đề tài 48)  
**Ngày lập:** 2026-10-28  
**Căn cứ:** 10 tiêu chí trong ảnh yêu cầu, [de_tai_48.md](de_tai_48.md), [TIEN_DO.md](TIEN_DO.md), kết quả kiểm thử thực tế  
**Trạng thái hiện tại:** [TIEN_DO.md](TIEN_DO.md) ghi “10/10” nhưng thực tế **3 đạt đầy đủ – 6 đạt một phần – 1 chưa đạt**.

> Đây là checklist công việc, không phải báo cáo nghiệm thu. Mỗi mục đều có mã việc, tiêu chí nghiệm thu và test tương ứng để có thể theo dõi tiến độ.

---

## 0. Tóm tắt điều hành

| Nhóm | Số việc | Nội dung chính | Ước lượng |
|---|---:|---|---|
| **P0 — Blocker** | 3 | Output AI bị cắt cụt; fallback báo ngược xu hướng; chat “AI” không gọi AI | 0,5–1 ngày |
| **P1 — Bắt buộc trước khi nộp/demo** | 10 | Validate input, đồng bộ ngưỡng, phân biệt nguồn kết quả, test API, bảo mật, tài liệu | 1–1,5 ngày |
| **P2 — Hoàn thiện hồ sơ** | 8 | Tách prompt, minh chứng 3 vòng, README, slide, nâng cấp SDK, backup | 1 ngày |
| **DEP — Checklist triển khai** | 12 | Secrets, HTTPS, CORS, process manager, logging, rollback, demo data | 0,5 ngày |
| **Tổng** | **33** | | **3–4 ngày** |

**Điều kiện tối thiểu để Go-live/demo:**

- [ ] Toàn bộ P0 pass, có test hồi quy.
- [ ] P1-01 → P1-10 pass (tối thiểu P1-01 → P1-08).
- [ ] Chạy đủ ma trận test ở mục 5, không còn test fail.
- [ ] Hoàn tất DEP-01 → DEP-10.
- [ ] Diễn tập demo 2 lần trên DB sạch.

---

## 1. Bảng đối chiếu 10 tiêu chí

| # | Tiêu chí | Trạng thái | Phần còn thiếu | Mã việc |
|---|---|---|---|---|
| 1 | Tích hợp AI vào hệ thống, phục vụ nghiệp vụ | ✅ Đạt | Trang Phân tích AI + `POST /api/ai/analyze` hoạt động; chat chưa dùng model | P0-03 |
| 2 | Kết nối API/model đúng cách, bảo vệ API key | ✅ Đạt | Chờ điền `AI_API_KEY` và test live 3/6/12 tháng | DEP-01 |
| 3 | Thiết kế prompt có hệ thống | ⚠️ Một phần | Prompt còn trong `.py`; thiếu quy tắc dữ liệu thiếu/âm/trùng; thiếu schema output; chưa giới hạn độ dài | P1-01, P2-01 |
| 4 | Tối ưu prompt qua ≥3 vòng | ✅ Đạt | Có tài liệu 3 vòng; thiếu log/script/ảnh tái lập; tài liệu nói “ngưỡng 20%” nhưng code không có | P1-02, P2-02 |
| 5 | Dùng dữ liệu hệ thống + kiểm soát quyền | ⚠️ Một phần | Thiếu ngưỡng cảnh báo/alert/payment trong prompt; `limit(months*2)` sai khi hộ có ≠2 đồng hồ; lỗ hổng user không gán hộ | P1-02, P1-05, P1-09 |
| 6 | Hiển thị kết quả AI rõ ràng | ❌ Chưa đạt | Chưa verify output đủ 5 mục với Qwen; UI vẫn luôn “Hoàn tất” kể cả fallback | P0-01, P1-03, P1-04 |
| 7 | Xử lý lỗi và giới hạn AI | ⚠️ Một phần | Thiếu check `finish_reason=MAX_TOKENS`; thiếu validate format; `months` không có `ge/le`; không giới hạn prompt; không retry/cache | P0-01, P1-01, P1-04, P1-10 |
| 8 | Kiểm thử chức năng quản lý và AI | ⚠️ Một phần | Không test API thật; không test billing/alert; 8 test “tính hóa đơn” chỉ tính inline; không có manual checklist | P1-06, P2-04 |
| 9 | AI review code + cải thiện chất lượng | ⚠️ Một phần | Doc nói đã thêm timeout chat nhưng chưa; thiếu transcript/ảnh; còn plaintext password, CORS `*` | P1-07, P1-08, P2-03 |
| 10 | Tích hợp AI với trải nghiệm người dùng | ⚠️ Một phần | Trang AI tốt; chat “Trợ lý AI” rule-based, trả lời kém với câu tự nhiên | P0-03, P1-03 |

---

## 2. P0 — Blocker, phải xử lý trước khi demo

### P0-01 — Output AI bị cắt cụt giữa câu

**Hiện trạng (trước chuyển đổi):** code Gemini cũ đặt `max_output_tokens=1024`. Gemini 2.5 Flash dùng gần hết ngân sách cho token “thinking”, nên phần trả lời chỉ còn vài chục token.

**Cập nhật 2026-10-28:** đã chuyển sang API chuẩn OpenAI (Qwen3.8-27B), đặt `max_tokens=4096`, retry 1 lần với 8192 nếu `finish_reason=length`, fallback nếu vẫn bị cắt. Chưa verify live vì chưa có `AI_API_KEY`.

**Bằng chứng (trước chuyển đổi):**

| Lần gọi | Độ dài | Kết thúc |
|---|---:|---|
| 3 tháng | 102 ký tự | “…Trong kỳ 2026-07, Phòng” |
| 6 tháng | 122 ký tự | “…mức tiêu thụ điện và nước khá” |
| 12 tháng | 71 ký tự | “…tiêu thụ ⚡ 78.0” |

Thử cùng prompt: `max_output_tokens=1024` → `finish_reason=2` (MAX_TOKENS), 116 ký tự; `max_output_tokens=4096` → `finish_reason=1` (STOP), 839 ký tự đầy đủ.

**Việc cần làm:**

- [x] Tăng `max_tokens` lên 4096.
- [x] Đọc `response.choices[0].finish_reason`; nếu `length` thì retry 1 lần với 8192, sau đó fallback.
- [ ] Thay điều kiện `len(text) < 50` bằng kiểm tra đủ 5 mục output (📊/📈/⚠️/💡/💰) và độ dài tối thiểu hợp lý.
- [ ] Ghi log `finish_reason`, `usage`, thời gian gọi để phục vụ điều tra.
- [x] Không trả kết quả nửa câu cho UI; nếu không đủ thì dùng fallback và ghi rõ nguồn.

**File:** [ai_service.py](app/services/ai_service.py#L74-L148)

**Nghiệm thu:**
- 10 lần gọi liên tiếp với 3/6/12 tháng đều trả đủ 5 mục, không cắt giữa câu.
- UI hiển thị đủ nội dung, không có dấu hiệu kết thúc giữa từ.
- Khi model trả `MAX_TOKENS`, hệ thống không gắn badge “Hoàn tất”.

**Test:** unit test mock `finish_reason=length` (đã có TC-AI-013/014); integration test 12 tháng sau khi có key.

**Ước lượng:** 2–3 giờ.

---

### P0-02 — Fallback báo ngược xu hướng tiêu thụ

**Hiện trạng:** [ai_analysis.py:56–62](app/routers/ai_analysis.py#L56-L62) trả readings theo `period DESC` (mới nhất trước), nhưng [_mock_analysis](app/services/ai_service.py#L178-L186) so sánh `consumptions[-1]` với `[-2]` — tức 2 tháng cũ nhất.

**Bằng chứng:** 2026-07 = 78 kWh, 2026-06 = 75 kWh, 2026-05 = 65 kWh. Xu hướng đúng là **tăng +4,0%**, nhưng fallback in ra “✅ Giảm 13.3% so với tháng trước”.

**Việc cần làm:**

- [ ] Sắp xếp readings theo `period` tăng dần trước khi tính biến động.
- [ ] Hoặc dùng `elec_readings[0]`/`[1]` nếu giữ nguyên thứ tự DESC, nhưng phải ghi rõ giả định trong code.
- [ ] Sửa test helper [test_ai.py:19–37](tests/test_ai.py#L19-L37) để tạo dữ liệu theo cả ASC và DESC.
- [ ] Thêm test hồi quy: input 78/75/65 phải ra “tăng”, không được ra “giảm”.

**File:** [ai_service.py](app/services/ai_service.py#L160-L202), [test_ai.py](tests/test_ai.py)

**Nghiệm thu:** fallback với dữ liệu thật báo đúng chiều; không còn trường hợp “Giảm x%” khi tháng mới nhất cao hơn tháng trước.

**Ước lượng:** 1–2 giờ.

---

### P0-03 — Chat “Trợ lý AI” không gọi AI

**Hiện trạng:** [chat_service.py](app/services/chat_service.py) đã đổi `_genai_generate` → `_ai_generate` (OpenAI) nhưng **vẫn chưa được gọi ở đâu**. Toàn bộ [process_message](app/services/chat_service.py#L586-L613) là if/else intent → truy vấn DB.

**Bằng chứng:** không có call site của `_ai_generate`; câu hỏi tự nhiên “Theo bạn tháng nào nhà tôi dùng điện nhiều nhất và vì sao?” trả về “🤔 Mình chưa rõ bạn muốn hỏi gì…”.

**Việc cần làm — chọn 1 trong 3 hướng:**

- [ ] **Hướng A (khuyến nghị):** Nối `_ai_generate` vào nhánh `general`:
  - Thêm system prompt riêng cho chat (vai trò, phạm vi dữ liệu, không bịa số).
  - Dùng timeout 30s đã cấu hình trong `ai_client` (không cần `request_options`).
  - Kiểm tra `finish_reason`, response rỗng, độ dài.
  - Trả `None` khi lỗi để fallback rule-based, **không** trả chuỗi lỗi như nội dung trả lời.
  - Chặn prompt injection: không đưa toàn bộ DB vào prompt; chỉ đưa dữ liệu đã lọc theo quyền.
- [ ] **Hướng B:** Đổi nhãn UI từ “Trợ lý AI” thành “Trợ lý tra cứu”, bỏ chữ AI trong [index.html:111–113](static/index.html#L111-L113) và [chat.js:34](static/js/pages/chat.js#L34); cập nhật báo cáo để không overclaim.
- [ ] **Hướng C:** Hybrid — rule-based cho câu hỏi có cấu trúc, LLM chỉ cho `general`; hiển thị badge “AI” khi thực sự gọi model.

**Nghiệm thu:**
- Nếu A/C: câu hỏi tự do nhận câu trả lời từ model; có fallback khi timeout/429; không lộ dữ liệu hộ khác.
- Nếu B: không còn nhãn “AI” trong chat; báo cáo ghi đúng “chat tra cứu rule-based”.

**Ước lượng:** 3–4 giờ (A), 0,5 giờ (B).

---

## 3. P1 — Bắt buộc trước khi nộp/demo

### P1-01 — Validate input và giới hạn dữ liệu AI

**Hiện trạng:** [ai_analysis.py:20–22](app/routers/ai_analysis.py#L20-L22) khai báo `months: int = 6` không có ràng buộc. Đã thử `months=0` → HTTP 200, `data_points=0`.

**Việc cần làm:**

- [ ] `months: int = Field(6, ge=1, le=12)`.
- [ ] Giới hạn số readings/invoices đưa vào prompt (ví dụ 24 readings, 12 invoices).
- [ ] Giới hạn độ dài prompt (ví dụ 6.000 ký tự); nếu vượt thì cắt bớt kỳ cũ và ghi chú.
- [ ] Trả 422 với `months` âm/0/lớn hơn 12.
- [ ] Test các giá trị 0, -1, 13, 100000.

**Nghiệm thu:** `months=0` và `months=13` trả 422; `months=100000` không treo server.

**Ước lượng:** 1–2 giờ.

---

### P1-02 — Đồng bộ ngưỡng cảnh báo và đưa ngưỡng vào prompt

**Hiện trạng:** [alert_service.py:12](app/services/alert_service.py#L12) dùng `SPIKE_THRESHOLD = 50%`; fallback dùng 20%; `SYSTEM_PROMPT` không nêu ngưỡng nào. [prompt_optimization.md:107](prompt_optimization.md#L107) nói V3 “thêm cảnh báo ngưỡng 20%” nhưng code không có.

**Việc cần làm:**

- [ ] Chọn một ngưỡng nghiệp vụ duy nhất (đề xuất 50% theo `alert_service`, hoặc 20% nếu muốn nhạy hơn).
- [ ] Đưa ngưỡng vào user prompt: “Ngưỡng cảnh báo: tăng > X% so với trung bình 3 kỳ”.
- [ ] Đưa danh sách `ConsumptionAlert` chưa xử lý của hộ vào prompt để AI đối chiếu.
- [ ] Đồng bộ fallback và test theo cùng ngưỡng.
- [ ] Sửa lại tài liệu `prompt_optimization.md` cho khớp code.

**Nghiệm thu:** AI và cảnh báo nghiệp vụ chỉ ra cùng kỳ bất thường với cùng ngưỡng; không còn 3 ngưỡng khác nhau.

**Ước lượng:** 2 giờ.

---

### P1-03 — Phân biệt kết quả AI thật và fallback trên UI

**Hiện trạng:** [ai.js:126–131](static/js/pages/ai.js#L126-L131) luôn gắn “Qwen3.8-27B” + “✅ Hoàn tất”, kể cả khi `analysis` bắt đầu bằng “⚠️ … Sử dụng phân tích nội bộ”.

**Việc cần làm:**

- [ ] Thêm `source: "ai" | "internal"` và `prompt_version` vào `AIAnalyzeResponse`.
- [ ] Backend trả `source` theo nhánh thực tế (kể cả timeout/429/rỗng).
- [ ] UI đổi badge: “Qwen3.8-27B” khi `source=ai`; “Phân tích nội bộ” khi `internal`.
- [ ] Không hiển thị “Hoàn tất” nếu kết quả không đủ 5 mục.
- [ ] Hiển thị thời điểm phân tích và khoảng kỳ đã dùng.

**Nghiệm thu:** fallback hiển thị rõ nguồn, không gây hiểu nhầm là model AI.

**Ước lượng:** 2 giờ.

---

### P1-04 — Validate format output và retry/fallback

**Hiện trạng:** chỉ kiểm tra `len < 50`; không kiểm tra 5 mục; không kiểm tra kết thúc câu.

**Việc cần làm:**

- [ ] Kiểm tra sự hiện diện của 5 marker: `📊`, `📈`, `⚠️`, `💡`, `💰`.
- [ ] Nếu thiếu marker → retry 1 lần với prompt nhắc format; nếu vẫn thiếu → fallback.
- [ ] Kiểm tra câu kết thúc bằng dấu câu/ký tự hợp lệ; nếu kết thúc giữa từ → coi là lỗi.
- [ ] Giới hạn độ dài output (ví dụ 4.000 ký tự) để tránh UI vỡ.

**Nghiệm thu:** không còn output nửa câu hoặc thiếu mục được hiển thị là thành công.

**Ước lượng:** 2 giờ.

---

### P1-05 — Vá lỗ hổng phân quyền khi user không có hộ

**Hiện trạng:** [auth.py:100–107](app/auth.py#L100-L107) trả `None` cho user không có `household_id`. [ai_analysis.py:44–46](app/routers/ai_analysis.py#L44-L46) coi `None` là admin → user này phân tích được mọi hộ. Các handler chat cũng có pattern tương tự.

**Việc cần làm:**

- [ ] Nếu `current_user.role != "admin"` và `household_id is None` → 403 ở mọi endpoint AI/chat.
- [ ] Tách hàm `require_household_scope` dùng chung.
- [ ] Thêm test: user không gán hộ gọi `/api/ai/analyze` → 403.
- [ ] Rà lại toàn bộ router dùng `get_household_filter`.

**Nghiệm thu:** không còn đường vòng nào để user thường đọc dữ liệu hộ khác.

**Ước lượng:** 2 giờ.

---

### P1-06 — Bổ sung test thực chất

**Hiện trạng:** 47 test pass nhưng:
- Không có `TestClient`/HTTP test.
- Không test [billing.py](app/services/billing.py) và [alert_service.py](app/services/alert_service.py).
- 8 test “tính hóa đơn” trong [test_crud.py:29–33](tests/test_crud.py#L29-L33) chỉ tính `curr - prev` inline, không gọi code thật.
- `test_TC_CRUD_008` dùng giá 1.806đ/kWh cho 100 kWh, trong khi seed thật là 1.728đ cho 0–50 kWh — test vẫn pass dù công thức bậc thang sai.
- Không có manual test checklist.

**Việc cần làm:**

- [ ] Thêm `tests/test_api_ai.py` dùng `TestClient`:
  - admin 200; user đúng hộ 200; user sai hộ 403; hộ không tồn tại 404.
  - `months=0/13` → 422.
  - không có key → fallback + `source=internal`.
  - `finish_reason=MAX_TOKENS` → retry/fallback.
- [ ] Thêm `tests/test_billing.py`:
  - 0 kWh, 50 kWh, 51 kWh, 101 kWh, 400 kWh; kiểm tra ranh giới bậc thang và VAT.
  - Dùng đúng giá seed: 1.728 / 1.786 / 2.074 / 2.612 / 2.919 / 3.015.
- [ ] Thêm `tests/test_alerts.py`:
  - 49% không tạo alert; 50% biên; 51% tạo alert; thiếu lịch sử → không tạo.
- [ ] Thêm regression test cho P0-02 (DESC) và P0-01 (MAX_TOKENS).
- [ ] Tạo `docs/manual-test-checklist.md` với các bước demo.

**Nghiệm thu:** tất cả test pass; các test mới fail nếu revert lỗi P0.

**Ước lượng:** 4–5 giờ.

---

### P1-07 — Đồng bộ tài liệu với code

**Hiện trạng:**
- [TIEN_DO.md](TIEN_DO.md) đã cập nhật 47 test; còn dòng trạng thái “10/10” đã được sửa thành trạng thái thật.
- [ai_code_review.md](ai_code_review.md) nói đã thêm timeout cho chat; hiện timeout 30s nằm trong `ai_client` (đã đúng hướng).
- [prompt_optimization.md:107](prompt_optimization.md#L107) nói có ngưỡng 20%, code không có.

**Việc cần làm:**

- [ ] Cập nhật TIEN_DO theo trạng thái thật, thêm mục “Đang bổ sung”.
- [ ] Sửa ai_code_review hoặc thực sự thêm timeout cho `_genai_generate`.
- [ ] Sửa prompt_optimization cho khớp prompt production.
- [ ] Thêm changelog ngắn ở cuối mỗi tài liệu.

**Nghiệm thu:** không còn tuyên bố sai trong hồ sơ.

**Ước lượng:** 1 giờ.

---

### P1-08 — Bảo mật cơ bản

**Hiện trạng:** [models.py:34](app/models.py#L34) lưu mật khẩu plaintext; [main.py:42–47](main.py#L42-L47) CORS `*`; auth gửi `X-Username`/`X-Password` mỗi request; chưa có rate limit.

**Việc cần làm:**

- [ ] Hash mật khẩu bằng `passlib[bcrypt]`; migrate seed và tài khoản hiện có.
- [ ] CORS: chỉ cho origin của frontend (khi deploy).
- [ ] Thêm rate limit cho `/api/ai/analyze` và `/api/chat/message` (slowapi hoặc in-memory).
- [ ] Thêm security headers cơ bản (X-Content-Type-Options, X-Frame-Options, Referrer-Policy).
- [ ] Với production: chuyển sang token/session (JWT hoặc cookie HttpOnly), không gửi mật khẩu mỗi request; bắt buộc HTTPS.
- [ ] Kiểm tra không log key/password.

**Nghiệm thu:** không còn plaintext password; CORS không còn `*` ở môi trường deploy; có rate limit.

**Ước lượng:** 3–4 giờ.

---

### P1-09 — Chọn dữ liệu theo kỳ thay vì `limit(months*2)`

**Hiện trạng:** [ai_analysis.py:56–62](app/routers/ai_analysis.py#L56-L62) và [readings.py:75–82](app/routers/readings.py#L75-L82) dùng `limit(months * 2)`, giả định mỗi hộ đúng 2 đồng hồ. Hộ có 1 đồng hồ sẽ lấy thừa kỳ; hộ có >2 đồng hồ sẽ thiếu kỳ.

**Việc cần làm:**

- [ ] Lọc theo cửa sổ kỳ: `period >= kỳ_bắt_đầu` thay vì limit cứng.
- [ ] Sắp xếp theo `period ASC, meter_type` để prompt ổn định.
- [ ] `data_points` đếm theo kỳ, không đếm readings.
- [ ] UI hiển thị “N kỳ · M đồng hồ”.

**Nghiệm thu:** hộ 1 đồng hồ và hộ 3 đồng hồ đều nhận đúng số kỳ yêu cầu.

**Ước lượng:** 1–2 giờ.

---

### P1-10 — Xử lý rate limit free tier (5 request/phút)

**Hiện trạng:** chưa có cache/cooldown; bấm “Phân tích ngay” liên tục rất dễ 429; fallback lại đang sai chiều (P0-02).

**Việc cần làm:**

- [ ] Cache kết quả theo `(household_id, months)` trong 5 phút.
- [ ] Cooldown nút 10 giây; hiển thị “vừa phân tích, thử lại sau X giây”.
- [ ] Đọc `retry_delay` từ lỗi 429 nếu có; thông báo thời gian chờ.
- [ ] Cân nhắc dùng key trả phí hoặc model nhẹ hơn cho demo.

**Nghiệm thu:** 6 lần bấm liên tiếp không hiện lỗi 429; kết quả cache được dùng lại.

**Ước lượng:** 2 giờ.

---

## 4. P2 — Hoàn thiện hồ sơ và chất lượng

### P2-01 — Tách prompt ra khỏi code

- [ ] Tạo `prompts/consumption_system_v3.txt` và `prompts/consumption_user_template.txt`.
- [ ] Loader đọc file, cache trong bộ nhớ; fallback về hằng số nếu thiếu file.
- [ ] Ghi `prompt_version` vào response/log.
- [ ] **Nghiệm thu:** đổi prompt không cần sửa `.py`; test vẫn pass.

### P2-02 — Minh chứng 3 vòng tối ưu prompt

- [ ] Viết `tools/prompt_experiments.py` chạy cùng một bộ dữ liệu qua V1/V2/V3.
- [ ] Xuất `docs/prompt-experiments.csv` (version, model, độ dài, thời gian, điểm, ghi chú).
- [ ] Lưu ảnh/transcript 3 lần chạy thật.
- [ ] **Nghiệm thu:** có thể tái lập bảng so sánh 3/10 → 9/10.

### P2-03 — Minh chứng AI code review

- [ ] Lưu prompt + response gốc của AI review vào `docs/ai-review/`.
- [ ] Bảng issue → file → mức độ → trạng thái sửa → commit.
- [ ] **Nghiệm thu:** mỗi lỗi trong [ai_code_review.md](ai_code_review.md) có bằng chứng và diff tương ứng.

### P2-04 — README, hướng dẫn chạy, test report

- [ ] `README.md`: yêu cầu, cài đặt, `.env`, seed, chạy, tài khoản demo.
- [ ] `docs/manual-test-checklist.md`: các bước kiểm thử tay.
- [ ] `docs/test-report.md`: 42+ test, bảng pass/fail, test mới.
- [ ] **Nghiệm thu:** người khác clone và chạy được trong <10 phút.

### P2-05 — Slide/báo cáo cuối kỳ

- [ ] Slide 10–12 trang: bài toán, kiến trúc, demo AI, kết quả test, hạn chế.
- [ ] Kịch bản demo 5–7 phút, có phương án dự phòng khi mất mạng/429.
- [ ] **Nghiệm thu:** demo trơn 2 lần liên tiếp.

### P2-06 — Chuẩn hóa SDK OpenAI

- [x] Đã bỏ `google-generativeai`, thêm `openai>=1.66.0` vào [requirements.txt](requirements.txt).
- [ ] Pin phiên bản; tạo `requirements.lock` hoặc `pip freeze`.
- [ ] Test trên venv sạch.
- [ ] **Nghiệm thu:** `pip install -r requirements.txt` chạy được, không còn cảnh báo SDK deprecated.

### P2-07 — Backup, migration, dữ liệu

- [ ] Script backup `utility_mgmt.db` trước khi deploy.
- [ ] Bật WAL cho SQLite hoặc chuyển PostgreSQL nếu nhiều người dùng.
- [ ] Tách seed demo khỏi production; không seed khi DB đã có dữ liệu thật.
- [ ] **Nghiệm thu:** restore được từ backup; seed không ghi đè dữ liệu.

### P2-08 — Cấu hình production

- [ ] `uvicorn --workers 2` (hoặc Gunicorn) sau reverse proxy Nginx/Caddy.
- [ ] HTTPS bắt buộc; HSTS.
- [ ] Log rotating; log level theo môi trường.
- [ ] Healthcheck `/api/health` cho process manager.
- [ ] **Nghiệm thu:** deploy được sau restart máy; healthcheck xanh.

---

## 5. Ma trận test cần bổ sung

| ID | Kịch bản | Loại | Kỳ vọng |
|---|---|---|---|
| AI-API-01 | Admin phân tích hộ bất kỳ | Đúng | 200, đủ 5 mục |
| AI-API-02 | User phân tích hộ của mình | Đúng | 200 |
| AI-API-03 | User phân tích hộ khác | Sai | 403 |
| AI-API-04 | Hộ không tồn tại | Sai | 404 |
| AI-API-05 | `months=0`, `13`, `-1` | Biên | 422 |
| AI-API-06 | Không có API key | Biên | Fallback, `source=internal` |
| AI-API-07 | `finish_reason=MAX_TOKENS` | Sai | Retry/fallback, không “Hoàn tất” |
| AI-API-08 | Rate limit 429 | Sai | Thông báo rõ, không crash |
| AI-API-09 | Timeout 30s | Sai | Fallback trong <35s |
| AI-API-10 | 12 tháng dữ liệu | Biên | Trả đủ, không cắt |
| UNIT-BILL-01 | 0 kWh | Biên | 0 đồng |
| UNIT-BILL-02 | 50 kWh | Biên | Hết bậc 1 (50 × 1.728) |
| UNIT-BILL-03 | 51 kWh | Biên | Sang bậc 2 (1 kWh × 1.786) |
| UNIT-BILL-04 | 101 kWh | Biên | Sang bậc 3 |
| UNIT-BILL-05 | 400+ kWh | Biên | Đủ bậc, VAT đúng |
| UNIT-ALERT-01 | Tăng 49% | Biên | Không alert |
| UNIT-ALERT-02 | Tăng 50% | Biên | Theo quy ước |
| UNIT-ALERT-03 | Tăng 51% | Đúng | Có alert |
| CHAT-01 | Câu hỏi tự do | Đúng | LLM trả lời hoặc fallback rõ |
| CHAT-02 | User hỏi hộ khác | Sai | 403/không lộ dữ liệu |
| SEC-01 | Response/log không chứa key | Bảo mật | Không lộ |
| SEC-02 | CORS origin lạ | Bảo mật | Bị chặn |
| E2E-01 | Nhập chỉ số → hóa đơn → AI | End-to-end | Đúng số, AI đọc đúng |

---

## 6. Checklist triển khai (deployment)

| ID | Hạng mục | Hiện trạng | Việc cần làm | Trạng thái |
|---|---|---|---|---|
| DEP-01 | Secrets | `.env` có key thật, đã gitignore | Rotate key trước khi nộp; chỉ giữ `.env.example`; không đưa `.env` vào zip | ☐ |
| DEP-02 | Cấu hình | `DATABASE_URL`, `ADMIN_PASSWORD` mặc định | Đổi mật khẩu admin; tách config dev/prod | ☐ |
| DEP-03 | Database | SQLite 1 file | Backup trước deploy; bật WAL; test restore | ☐ |
| DEP-04 | Chạy nền | `start.bat`/uvicorn reload | Dùng process manager (NSSM/systemd) hoặc `--workers`; tắt reload ở prod | ☐ |
| DEP-05 | HTTPS | Chưa có | Reverse proxy + certificate; chặn HTTP | ☐ |
| DEP-06 | Auth | Gửi username/password mỗi request | Chuyển token/session; tối thiểu bắt buộc HTTPS | ☐ |
| DEP-07 | CORS | `*` | Allowlist domain frontend | ☐ |
| DEP-08 | Logging | Log mặc định | Log AI latency/429/lỗi; không log key/password | ☐ |
| DEP-09 | Healthcheck | `/api/health` có | Cấu hình monitor 30s/lần | ☐ |
| DEP-10 | Rollback | Chưa có | Giữ bản DB + code trước deploy; kịch bản rollback 1 lệnh | ☐ |
| DEP-11 | Demo data | Seed tự động | Script reset DB sạch + seed trước demo | ☐ |
| DEP-12 | Dependencies | requirements chưa lock | `pip freeze` hoặc lock file; test trên venv sạch | ☐ |

---

## 7. Kế hoạch thực hiện đề xuất

### Ngày 1 — Chặn lỗi nghiêm trọng

- [ ] P0-01: tăng token + check `finish_reason` + validate 5 mục.
- [ ] P0-02: sửa chiều so sánh fallback + test hồi quy.
- [ ] P0-03: chọn hướng A/B/C và triển khai.
- [ ] Chạy lại toàn bộ test; ghi kết quả.

### Ngày 2 — Đúng yêu cầu và đủ test

- [ ] P1-01 → P1-05.
- [ ] P1-06: test API, billing, alert, regression.
- [ ] P1-09, P1-10.
- [ ] P1-07, P1-08.

### Ngày 3 — Hồ sơ và diễn tập

- [ ] P2-01 → P2-06.
- [ ] DEP-01 → DEP-12.
- [ ] Diễn tập demo 2 lần trên DB sạch.
- [ ] Cập nhật TIEN_DO + báo cáo.

---

## 8. Definition of Done

Một mục chỉ được coi là xong khi:

- [ ] Code đã sửa và chạy được trên môi trường sạch.
- [ ] Có test tự động hoặc bước manual tương ứng, đã chạy pass.
- [ ] Không tạo regression ở 47 test cũ.
- [ ] Tài liệu/hồ sơ liên quan đã cập nhật.
- [ ] Có bằng chứng (log, ảnh, commit) lưu trong `docs/`.

---

## 9. Rủi ro và cách giảm thiểu

| Rủi ro | Ảnh hưởng | Giảm thiểu |
|---|---|---|
| Free tier 5 request/phút | Demo bị 429, fallback sai | P1-10 cache/cooldown; key trả phí; kịch bản demo ít gọi |
| SQLite khóa khi ghi đồng thời | 500 khi nhiều người dùng | WAL; khóa ghi; cân nhắc PostgreSQL |
| AI bịa số / bỏ qua dữ liệu | Sai nhận xét | Prompt ràng buộc + validate output + disclaimer |
| Key lộ khi nộp bài | Mất quota, rủi ro bảo mật | DEP-01 rotate; chỉ nộp `.env.example` |
| SDK deprecated | Lỗi khi update | P2-06 chuyển `google-genai` |
| Mất mạng khi demo | Không gọi được AI | Fallback nội bộ đúng (P0-02) + ảnh chụp kết quả mẫu |

---

## 10. Lệnh kiểm tra nhanh

```powershell
# 1. Chạy toàn bộ test
python -m pytest -q

# 2. Chạy server
python main.py

# 3. Smoke test
curl http://localhost:8000/api/health

# 4. Gọi AI với admin (PowerShell)
$h = @{ "X-Username"="admin"; "X-Password"="admin123"; "Content-Type"="application/json" }
Invoke-RestMethod "http://localhost:8000/api/ai/analyze" -Method Post -Headers $h `
  -Body (@{ household_id = 1; months = 6 } | ConvertTo-Json)

# 5. Kiểm tra user không được xem hộ khác (kỳ vọng 403)
$u = @{ "X-Username"="ho101"; "X-Password"="ho101"; "Content-Type"="application/json" }
Invoke-RestMethod "http://localhost:8000/api/ai/analyze" -Method Post -Headers $u `
  -Body (@{ household_id = 2; months = 6 } | ConvertTo-Json)
```

---

## 11. Bảng theo dõi tiến độ

| Mã | Việc | Ưu tiên | Ước lượng | Người làm | Trạng thái | Ghi chú |
|---|---|---|---|---|---|---|
| P0-01 | Sửa cắt cụt output | P0 | 2–3h | | ☐ | |
| P0-02 | Sửa fallback đảo chiều | P0 | 1–2h | | ☐ | |
| P0-03 | Chat AI / đổi nhãn | P0 | 0,5–4h | | ☐ | |
| P1-01 | Validate `months` | P1 | 1–2h | | ☐ | |
| P1-02 | Đồng bộ ngưỡng | P1 | 2h | | ☐ | |
| P1-03 | Badge nguồn kết quả | P1 | 2h | | ☐ | |
| P1-04 | Validate format | P1 | 2h | | ☐ | |
| P1-05 | Vá RBAC `None` | P1 | 2h | | ☐ | |
| P1-06 | Test API/billing/alert | P1 | 4–5h | | ☐ | |
| P1-07 | Đồng bộ tài liệu | P1 | 1h | | ☐ | |
| P1-08 | Bảo mật cơ bản | P1 | 3–4h | | ☐ | |
| P1-09 | Chọn dữ liệu theo kỳ | P1 | 1–2h | | ☐ | |
| P1-10 | Cache/cooldown 429 | P1 | 2h | | ☐ | |
| P2-01 | Tách prompt | P2 | 2h | | ☐ | |
| P2-02 | Minh chứng 3 vòng | P2 | 3h | | ☐ | |
| P2-03 | Minh chứng AI review | P2 | 1h | | ☐ | |
| P2-04 | README/test report | P2 | 3h | | ☐ | |
| P2-05 | Slide/demo | P2 | 3h | | ☐ | |
| P2-06 | Chuẩn hóa SDK OpenAI | P2 | 2h | | ☐ | |
| P2-07 | Backup/migration | P2 | 2h | | ☐ | |
| P2-08 | Cấu hình production | P2 | 3h | | ☐ | |
| DEP | Checklist triển khai | P0/P1 | 4h | | ☐ | |

---

**Ghi chú cuối:** Các kết luận trong tài liệu này được kiểm chứng bằng cách chạy `pytest` (47 test pass), gọi Gemini thật qua `POST /api/ai/analyze` (trước khi chuyển provider), kiểm tra phân quyền với tài khoản `ho101`, và kiểm tra trực tiếp `_mock_analysis`/`process_message`.

---

## 12. Nhật ký cập nhật

- **2026-10-28 — Chuyển AI provider:**
  - Thêm `app/services/ai_client.py` gọi API chuẩn OpenAI (`/chat/completions`), mặc định `https://discovery-api.intern-ai.org.cn/v1`, model `qwen3.8-27b`.
  - Cấu hình qua `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL`, `AI_TIMEOUT`, `AI_MAX_TOKENS`; đã xóa key Gemini khỏi `.env` (cần revoke key cũ).
  - Bỏ `google-generativeai`, thêm `openai` vào `requirements.txt`/`start.bat`.
  - `max_tokens=4096`, retry khi `finish_reason=length`, fallback nếu vẫn cắt.
  - UI đổi nhãn Gemini → AI/Qwen3.8-27B.
  - Test: 47 passed (thêm test cấu hình, wire format, retry/fallback).
  - **Còn lại:** điền `AI_API_KEY`, chạy live 3/6/12 tháng để xác nhận; P0-02, P0-03 và các mục P1/P2 khác vẫn mở.
