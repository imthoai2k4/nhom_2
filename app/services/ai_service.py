"""
app/services/ai_service.py — Tích hợp Gemini AI phân tích hóa đơn tiền điện

Sử dụng Google Generative AI (Gemini) để:
  - Nhận xét biến động tiêu thụ điện theo tháng
  - Cảnh báo dấu hiệu bất thường
  - Gợi ý tiết kiệm điện ở mức tham khảo

Xử lý lỗi đầy đủ: timeout, rate limit (429), response rỗng/sai định dạng, lỗi model.
"""
import os
from dotenv import load_dotenv

load_dotenv()

_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# ── System prompt (theo đề tài 48) ──────────────────────────────────────────
SYSTEM_PROMPT = """Bạn là trợ lý AI phân tích hóa đơn điện nước cho hệ thống quản lý hộ gia đình.
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
"""


def _build_user_prompt(household_name: str, readings: list, invoices: list) -> str:
    """Xây dựng prompt người dùng từ dữ liệu tiêu thụ."""
    lines = [f"Hộ/phòng: {household_name}\n"]

    # Nhóm readings theo kỳ
    if readings:
        lines.append("📋 Lịch sử tiêu thụ:")
        for r in readings:
            unit_label = "kWh" if r["unit"] in ("kWh",) else "m³"
            type_label = "⚡ Điện" if r["meter_type"] == "electricity" else "💧 Nước"
            lines.append(f"  - Kỳ {r['period']}: {type_label} = {r['consumption']} {unit_label}")

    if invoices:
        lines.append("\n🧾 Hóa đơn:")
        for inv in invoices:
            status_label = {"unpaid": "Chưa TT", "partial": "Một phần", "paid": "Đã TT"}.get(inv["status"], inv["status"])
            lines.append(
                f"  - Kỳ {inv['period']}: "
                f"Điện={inv['electricity_amount']:,}đ | "
                f"Nước={inv['water_amount']:,}đ | "
                f"Tổng={inv['total_amount']:,}đ | "
                f"TT: {status_label}"
            )

    lines.append("\nHãy phân tích biến động tiêu thụ điện nước, chỉ ra tháng cần kiểm tra và gợi ý tiết kiệm.")
    return "\n".join(lines)


async def analyze_consumption(
    household_name: str,
    readings: list,
    invoices: list,
) -> str:
    """
    Gọi Gemini API phân tích tiêu thụ điện nước.
    Trả về chuỗi markdown nhận xét.
    Xử lý đầy đủ: timeout, rate limit, response rỗng, lỗi model.
    """
    if not _GEMINI_KEY:
        return _mock_analysis(household_name, readings, invoices)

    try:
        import google.generativeai as genai

        genai.configure(api_key=_GEMINI_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")

        user_prompt = _build_user_prompt(household_name, readings, invoices)

        # ── Gọi API với xử lý lỗi phân loại ────────────────────────────────
        try:
            response = model.generate_content(
                [
                    {"role": "user", "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_prompt}]},
                ],
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
                request_options={"timeout": 30},  # timeout 30 giây
            )
        except Exception as api_err:
            err_str = str(api_err).lower()
            err_type = type(api_err).__name__

            # Timeout
            if any(k in err_str for k in ("deadline", "timeout", "timed out")):
                return (
                    "⏱️ **AI phân tích chậm (timeout 30s)** — Hệ thống dùng phân tích nội bộ thay thế:\n\n"
                    + _mock_analysis(household_name, readings, invoices)
                )
            # Rate limit (HTTP 429)
            if any(k in err_str for k in ("quota", "resource_exhausted", "429", "rate limit", "rateLimitExceeded")):
                return (
                    "⚠️ **AI đang quá tải (rate limit)** — Vui lòng thử lại sau ít phút.\n\n"
                    "Phân tích cơ bản từ dữ liệu hệ thống:\n\n"
                    + _mock_analysis(household_name, readings, invoices)
                )
            # API key không hợp lệ hoặc hết hạn
            if any(k in err_str for k in ("permission", "api_key", "invalid_argument", "unauthenticated")):
                return (
                    "🔑 **API key Gemini không hợp lệ hoặc hết hạn** — Sử dụng phân tích nội bộ:\n\n"
                    + _mock_analysis(household_name, readings, invoices)
                )
            # Lỗi model / service không khả dụng
            if any(k in err_str for k in ("service_unavailable", "internal", "model")):
                return (
                    f"🛠️ **Dịch vụ AI tạm thời không khả dụng** (`{err_type}`) — Sử dụng phân tích nội bộ:\n\n"
                    + _mock_analysis(household_name, readings, invoices)
                )
            # Lỗi API không xác định → re-raise để xử lý ở ngoài
            raise

        # ── Kiểm tra response rỗng / sai định dạng ──────────────────────────
        if not response or not hasattr(response, "text"):
            return (
                "⚠️ **AI không trả về đối tượng kết quả hợp lệ** — Sử dụng phân tích nội bộ:\n\n"
                + _mock_analysis(household_name, readings, invoices)
            )

        result_text = (response.text or "").strip()

        if not result_text:
            return (
                "⚠️ **AI trả về kết quả rỗng** — Sử dụng phân tích nội bộ:\n\n"
                + _mock_analysis(household_name, readings, invoices)
            )

        # Kiểm tra độ dài tối thiểu (< 50 ký tự = phản hồi không đủ nội dung)
        if len(result_text) < 50:
            return (
                "⚠️ **Phản hồi AI không đủ nội dung** — Sử dụng phân tích nội bộ:\n\n"
                + _mock_analysis(household_name, readings, invoices)
            )

        return result_text

    except Exception as e:
        # Fallback chung cho các lỗi không xác định
        error_type = type(e).__name__
        return (
            f"⚠️ **Lỗi không xác định khi gọi Gemini AI** (`{error_type}: {str(e)[:100]}`)\n\n"
            "Sử dụng phân tích nội bộ:\n\n"
            + _mock_analysis(household_name, readings, invoices)
        )


def _mock_analysis(household_name: str, readings: list, invoices: list) -> str:
    """Phân tích mock khi không có Gemini API key."""
    # Phân tích cơ bản từ dữ liệu
    elec_readings = [r for r in readings if r.get("meter_type") == "electricity"]
    water_readings = [r for r in readings if r.get("meter_type") == "water"]

    result_lines = [f"## 📊 Phân tích tiêu thụ — {household_name}\n"]

    if elec_readings:
        consumptions = [r["consumption"] for r in elec_readings]
        avg = sum(consumptions) / len(consumptions) if consumptions else 0
        max_c = max(consumptions) if consumptions else 0
        min_c = min(consumptions) if consumptions else 0

        result_lines.append("### ⚡ Điện")
        result_lines.append(f"- Trung bình: **{avg:.1f} kWh/tháng**")
        result_lines.append(f"- Cao nhất: **{max_c:.1f} kWh** | Thấp nhất: **{min_c:.1f} kWh**")

        if len(consumptions) >= 2:
            change = consumptions[-1] - consumptions[-2]
            pct = (change / consumptions[-2] * 100) if consumptions[-2] > 0 else 0
            if pct > 20:
                result_lines.append(f"- ⚠️ **Tăng {pct:.1f}%** so với tháng trước — cần kiểm tra!")
            elif pct < -10:
                result_lines.append(f"- ✅ Giảm {abs(pct):.1f}% so với tháng trước")
            else:
                result_lines.append(f"- ✅ Biến động bình thường ({pct:+.1f}%)")

    if water_readings:
        consumptions = [r["consumption"] for r in water_readings]
        avg = sum(consumptions) / len(consumptions) if consumptions else 0

        result_lines.append("\n### 💧 Nước")
        result_lines.append(f"- Trung bình: **{avg:.1f} m³/tháng**")

    result_lines.append("\n### 💡 Gợi ý tiết kiệm")
    result_lines.append("- Tắt thiết bị điện khi không sử dụng")
    result_lines.append("- Sử dụng đèn LED tiết kiệm năng lượng")
    result_lines.append("- Đặt máy lạnh ở mức 26°C trở lên")

    result_lines.append("\n> *Phân tích tự động — dữ liệu chỉ mang tính tham khảo*")

    return "\n".join(result_lines)
