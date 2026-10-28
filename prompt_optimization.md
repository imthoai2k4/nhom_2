# Tối ưu Prompt qua Thử nghiệm — Đề tài 48

**Hệ thống:** Quản lý Hóa đơn Điện nước Hộ gia đình có Tích hợp AI  
**Chức năng AI:** Phân tích tiêu thụ điện nước, cảnh báo bất thường, gợi ý tiết kiệm  
**Model khi thử nghiệm:** Google Gemini 2.5 Flash  
**Model production hiện tại:** Qwen3.8-27B (API chuẩn OpenAI — chuyển ngày 2026-10-28)  
**Mục tiêu tối ưu:** Prompt chính xác, có cấu trúc, phản hồi đủ nội dung, không tự tạo số liệu

---

## Vòng 1 — Prompt thô ban đầu

**Ngày thử:** 2026-09-01  
**Mô tả:** Prompt đơn giản, chưa có system prompt, không ràng buộc output.

### Prompt V1

```
Phân tích tiêu thụ điện nước của hộ gia đình sau:
- Tháng 1: 150 kWh điện, 5 m³ nước
- Tháng 2: 280 kWh điện, 5.2 m³ nước
- Tháng 3: 160 kWh điện, 4.8 m³ nước
```

### Kết quả V1

```
Nhìn vào dữ liệu, hộ gia đình này có mức tiêu thụ điện tăng mạnh vào tháng 2 (280 kWh), 
có thể do sử dụng điều hòa nhiều hơn trong mùa hè. Tiêu thụ nước khá ổn định...
(tiếp tục 3 đoạn văn không có cấu trúc)
```

### Vấn đề phát hiện

| # | Vấn đề | Mức độ |
|---|--------|--------|
| 1 | AI tự đoán nguyên nhân ("mùa hè") không có trong dữ liệu | 🔴 Nghiêm trọng |
| 2 | Không có cấu trúc rõ ràng, khó đọc | 🟠 Quan trọng |
| 3 | Không có cảnh báo rõ khi tăng đột biến (87%) | 🔴 Nghiêm trọng |
| 4 | Không có gợi ý tiết kiệm cụ thể | 🟡 Trung bình |
| 5 | Phản hồi bằng văn xuôi, khó tích hợp vào UI | 🟠 Quan trọng |

**Điểm đánh giá: 3/10**

---

## Vòng 2 — Thêm System Prompt và Ràng buộc

**Ngày thử:** 2026-09-08  
**Cải tiến:** Tách system prompt, ràng buộc "chỉ dùng dữ liệu được cung cấp", thêm cấu trúc output.

### System Prompt V2

```
Bạn là trợ lý phân tích hóa đơn điện nước.
Quy tắc BẮT BUỘC:
1. Chỉ sử dụng dữ liệu được cung cấp. KHÔNG tự tạo số liệu.
2. Trả lời tiếng Việt, ngắn gọn.
3. Cấu trúc: TỔNG QUAN → BIẾN ĐỘNG → CẢNH BÁO → GỢI Ý → CHI PHÍ
```

### User Prompt V2

```
Hộ/phòng: Phòng 101 — Nguyễn Văn A

📋 Lịch sử tiêu thụ:
  - Kỳ 2026-01: ⚡ Điện = 150 kWh
  - Kỳ 2026-02: ⚡ Điện = 280 kWh  ← tăng 87%
  - Kỳ 2026-03: ⚡ Điện = 160 kWh

Hãy phân tích biến động, chỉ ra tháng cần kiểm tra và gợi ý tiết kiệm.
```

### Kết quả V2

```
📊 TỔNG QUAN: Tiêu thụ điện dao động từ 150–280 kWh trong 3 tháng.
📈 BIẾN ĐỘNG: Tháng 2 tăng 87% so với tháng 1 (280 vs 150 kWh).
⚠️ CẢNH BÁO: Kỳ 2026-02 cần kiểm tra — tăng đột biến 87%.
💡 GỢI Ý: Tắt thiết bị điện khi không sử dụng; dùng đèn LED.
💰 CHI PHÍ: Không có dữ liệu hóa đơn để nhận xét chi phí.
```

### Cải tiến so với V1

| # | Cải tiến | Kết quả |
|---|----------|---------|
| 1 | Không còn tự đoán nguyên nhân | ✅ Đạt |
| 2 | Cấu trúc 5 phần rõ ràng | ✅ Đạt |
| 3 | Cảnh báo tháng 2 (+87%) | ✅ Đạt |
| 4 | Gợi ý tiết kiệm xuất hiện | ✅ Đạt |
| 5 | Tự nhận biết thiếu dữ liệu | ✅ Đạt |

**Điểm đánh giá: 7/10**

### Vấn đề còn lại

- Gợi ý tiết kiệm còn chung chung, chưa gắn với xu hướng dữ liệu
- Chưa có emoji nhất quán giúp UI dễ parse
- Cần thêm dữ liệu hóa đơn vào prompt để phân tích chi phí

---

## Vòng 3 — Tối ưu hoàn chỉnh (Phiên bản Production)

**Ngày thử:** 2026-09-15  
**Cải tiến:** Thêm emoji nhất quán, yêu cầu gắn gợi ý với xu hướng, thêm dữ liệu hóa đơn, thêm cảnh báo ngưỡng 50% (đồng bộ `alert_service`).

### System Prompt V3 (Final — dùng trong production)

```
Bạn là trợ lý AI phân tích hóa đơn điện nước cho hệ thống quản lý hộ gia đình.
Quy tắc:
1. Chỉ nhận xét từ DỮ LIỆU ĐƯỢC CUNG CẤP, không tự tạo số liệu.
2. Trả lời bằng tiếng Việt, ngắn gọn, dễ hiểu.
3. Sử dụng emoji phù hợp để trực quan hơn.
4. Cấu trúc phản hồi:
   📊 TỔNG QUAN: Tóm tắt tình hình tiêu thụ
   📈 BIẾN ĐỘNG: Phân tích xu hướng tăng/giảm qua các tháng
   ⚠️ CẢNH BÁO: Chỉ ra tháng cần kiểm tra (nếu có bất thường)
   💡 GỢI Ý TIẾT KIỆM: Đề xuất tiết kiệm điện/nước ở mức tham khảo
   💰 CHI PHÍ: Nhận xét về chi phí và cách tối ưu
```

### User Prompt V3 (Final — được build tự động từ DB)

```
Hộ/phòng: Phòng 101

📋 Lịch sử tiêu thụ:
  - Kỳ 2026-01: ⚡ Điện = 150 kWh
  - Kỳ 2026-02: ⚡ Điện = 280 kWh
  - Kỳ 2026-03: ⚡ Điện = 160 kWh
  - Kỳ 2026-01: 💧 Nước = 5.0 m³
  - Kỳ 2026-02: 💧 Nước = 5.2 m³
  - Kỳ 2026-03: 💧 Nước = 4.8 m³

🧾 Hóa đơn:
  - Kỳ 2026-01: Điện=271,000đ | Nước=80,000đ | Tổng=351,000đ | TT: Đã TT
  - Kỳ 2026-02: Điện=520,000đ | Nước=83,000đ | Tổng=603,000đ | TT: Chưa TT
  - Kỳ 2026-03: Điện=289,000đ | Nước=77,000đ | Tổng=366,000đ | TT: Đã TT

⚠️ Cảnh báo nghiệp vụ chưa xử lý:
  - Kỳ 2026-02: Tiêu thụ điện tăng 86.7% so với trung bình 2 kỳ trước.

Ngưỡng cảnh báo: tăng > 50% so với trung bình 3 kỳ gần nhất.

Hãy phân tích biến động tiêu thụ điện nước, chỉ ra tháng cần kiểm tra và gợi ý tiết kiệm.
```

### Kết quả V3

```
📊 TỔNG QUAN: Phòng 101 tiêu thụ trung bình ~197 kWh điện/tháng và ~5 m³ nước/tháng trong 
3 kỳ gần nhất. Có 1 kỳ chưa thanh toán (2026-02) với tổng 603,000đ.

📈 BIẾN ĐỘNG:
- Điện tăng đột biến 87% vào kỳ 2026-02 (280 kWh), rồi giảm về mức bình thường (160 kWh).
- Nước ổn định, dao động nhỏ (4.8–5.2 m³), không có bất thường.

⚠️ CẢNH BÁO: Kỳ 2026-02 cần kiểm tra — điện tăng 87% so với kỳ trước. Có thể do 
thiết bị hỏng, rò rỉ điện hoặc sinh hoạt tăng bất thường.

💡 GỢI Ý TIẾT KIỆM (dựa trên xu hướng quan sát):
- Mức điện tháng 2 bất thường — kiểm tra thiết bị làm mát (điều hòa, quạt công nghiệp).
- Duy trì mức tiêu thụ ~150–160 kWh như tháng 1 và 3 để tối ưu chi phí.
- Đặt lịch bảo trì đồng hồ định kỳ để phát hiện rò rỉ sớm.

💰 CHI PHÍ: Hóa đơn tháng 2 (603,000đ) cao gấp 1.7 lần mức bình thường (~360,000đ). 
Kỳ 2026-02 chưa thanh toán — cần thu nợ.
```

### So sánh 3 phiên bản

| Tiêu chí | V1 | V2 | V3 |
|----------|----|----|-----|
| Không tự tạo số liệu | ❌ | ✅ | ✅ |
| Cấu trúc rõ ràng | ❌ | ✅ | ✅ |
| Cảnh báo đúng ngưỡng (50%) | ❌ | ⚠️ | ✅ |
| Gợi ý gắn với dữ liệu | ❌ | ⚠️ | ✅ |
| Có thông tin hóa đơn/chi phí | ❌ | ❌ | ✅ |
| Emoji nhất quán cho UI | ❌ | ⚠️ | ✅ |
| **Điểm tổng** | **3/10** | **7/10** | **9/10** |

**Phiên bản V3 được áp dụng vào production** trong `app/services/ai_service.py` + `prompts/consumption_system_v3.txt` + `prompts/consumption_user_template.txt`.

---

## Tóm tắt Kết quả Tối ưu

- **3 vòng thử nghiệm** với cùng 1 bộ dữ liệu mẫu (Phòng 101, 3 tháng điện + nước + hóa đơn)
- **Cải tiến chính**: Tách system/user prompt → Thêm ràng buộc → Thêm dữ liệu hóa đơn → Gắn gợi ý với xu hướng
- **Kết quả**: Điểm chất lượng tăng từ **3/10 → 9/10**
- **File áp dụng**: [`app/services/ai_service.py`](app/services/ai_service.py) (SYSTEM_PROMPT + `_build_user_prompt()`)
