# Thực nghiệm tối ưu prompt (V1 → V2 → V3)

**Ngày chạy:** 2026-10-28  
**Model:** `qwen3.8-27b` (OpenAI-compatible Intern-AI)  
**Dữ liệu:** Phòng 101, 3 kỳ 2026-01 → 2026-03, điện + nước + 3 hóa đơn.  
**Script tái lập:** `python tools/prompt_experiments.py --live`

## Bảng kết quả

| Vòng | Ký tự | Thời gian | Finish | Điểm | Nhận xét |
|---|---:|---:|---|---:|---|
| V1 — prompt thô | 794 | 10,7s | length | 3/10 | Lan man, tự suy diễn nguyên nhân, không cấu trúc |
| V2 — system + cấu trúc | 1.020 | 7,0s | stop | 7/10 | Đủ 5 phần, không bịa số, nhưng thiếu hóa đơn/chi phí |
| V3 — production | 1.489 | 21,2s | stop | 9/10 | Có hóa đơn, ngưỡng 50%, bám dữ liệu; đôi khi dừng giữa mục chi phí |

## Khác biệt chính

1. **V1:** không có system prompt, không ràng buộc output → dễ bịa nguyên nhân (“do mùa hè”), dài dòng.
2. **V2:** tách system/user, buộc cấu trúc 5 phần, nói rõ “không tự tạo số liệu” → giảm hallucination.
3. **V3:** thêm hóa đơn, ngưỡng cảnh báo 50%, cảnh báo nghiệp vụ; gắn gợi ý với dữ liệu thực.

## Ghi chú

- V1 có lần chạy timeout 30s khi tăng `max_tokens` lên 4096; điều này cho thấy prompt thô tạo output dài, không ổn định.
- V3 có lần dừng giữa mục “CHI PHÍ” dù `finish_reason=stop`; app đã có kiểm tra kết thúc câu + retry/fallback (P0-01/P1-04).
- Điểm 3/7/9 là đánh giá thủ công theo 5 tiêu chí: bám dữ liệu, cấu trúc, cảnh báo, gợi ý, chi phí.
- File CSV: [prompt-experiments.csv](prompt-experiments.csv).

## Cách tái lập

```powershell
# Dry-run: chỉ in prompt
python tools/prompt_experiments.py

# Gọi model thật, in CSV ra stdout
python tools/prompt_experiments.py --live

# Ghi CSV (máy có quyền ghi file)
python tools/prompt_experiments.py --live --out docs/prompt-experiments.csv
```

## Transcript (rút gọn từ lần chạy thật)

### V1 — 794 ký tự, `finish_reason=length`

```text
Dưới đây là phân tích nhanh dựa trên 3 tháng dữ liệu bạn cung cấp. Vì chưa có thông tin số người
trong hộ, chu kỳ hóa đơn, loại thiết bị sử dụng và đơn giá, nên đây là nhận định xu hướng...
| Tháng 2 | 280 | +130 kWh, tương đương +86,7% | ...
```

Nhận xét: lan man, dễ suy diễn nguyên nhân, không có cấu trúc 5 mục cố định.

### V2 — 1.020 ký tự, `finish_reason=stop`

```text
TỔNG QUAN
- Hộ/phòng: Phòng 101 — Nguyễn Văn A.
- Điện: 01/2026 = 150 kWh; 02/2026 = 280 kWh; 03/2026 = 160 kWh.
BIẾN ĐỘNG
- 01→02: tăng 130 kWh; 02→03: giảm 120 kWh.
CẢNH BÁO
- Tháng 02/2026 cần kiểm tra do mức tiêu thụ cao bất thường.
GỢI Ý
- Kiểm tra điều hòa, bếp điện, bình nóng lạnh; tắt thiết bị khi không dùng.
CHI PHÍ
- Chưa thể tính chi phí cụ thể vì chưa có đơn giá điện.
```

Nhận xét: có cấu trúc, không bịa số, nhưng thiếu dữ liệu hóa đơn.

### V3 — 1.489 ký tự, `finish_reason=stop`

```text
📊 TỔNG QUAN: Phòng 101 có 3 kỳ 2026-01 → 2026-03.
- ⚡ Điện: 150 → 280 → 160 kWh, trung bình ~196,7 kWh/kỳ.
- 💧 Nước: 5,0 → 5,2 → 4,8 m³.
- 💵 Tổng hóa đơn: 351.000đ → 603.000đ → 366.000đ. Kỳ 2026-02 chưa thanh toán.
📈 BIẾN ĐỘNG: Điện tăng mạnh ở kỳ 2026-02 (+86,7% so với tháng 1); tháng 3 giảm về 160 kWh.
⚠️ CẢNH BÁO: Theo ngưỡng >50% so với trung bình 3 kỳ, tháng 2 là 280 kWh, chưa vượt ~295 kWh;
tuy nhiên nên kiểm tra vì tăng đột biến so với tháng 1.
💡 GỢI Ý TIẾT KIỆM: Kiểm tra thiết bị công suất lớn; tắt khi không dùng; kiểm tra rò rỉ nước.
💰 CHI PHÍ: Kỳ 2026-02 có chi phí cao nhất:
```

Lần chạy này dừng giữa mục CHI PHÍ dù `finish_reason=stop` — đúng loại lỗi mà app xử lý bằng
kiểm tra kết thúc câu + retry/fallback.

