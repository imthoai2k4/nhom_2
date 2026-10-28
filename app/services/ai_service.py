"""
app/services/ai_service.py — Phân tích hóa đơn điện nước bằng AI

Sử dụng API chuẩn OpenAI (mặc định Qwen3.8-27B tại Intern-AI):
  - Nhận xét biến động tiêu thụ điện theo tháng
  - Cảnh báo dấu hiệu bất thường
  - Gợi ý tiết kiệm điện ở mức tham khảo

Xử lý lỗi đầy đủ: timeout, rate limit (429), API key, response rỗng,
finish_reason=length (bị cắt do giới hạn token), lỗi model.
"""
from app.services.ai_client import AIError, chat_completion, is_configured

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


def _error_fallback(
    exc: AIError,
    household_name: str,
    readings: list,
    invoices: list,
) -> str:
    """Trả thông báo lỗi thân thiện kèm phân tích nội bộ."""
    base = _mock_analysis(household_name, readings, invoices)
    detail = (exc.detail or "")[:120]

    if exc.kind == "no_key":
        return (
            "ℹ️ **Chưa cấu hình AI_API_KEY** — đang dùng phân tích nội bộ.\n\n" + base
        )
    if exc.kind == "timeout":
        return (
            "⏱️ **AI phân tích chậm (timeout 30s)** — Hệ thống dùng phân tích nội bộ thay thế:\n\n"
            + base
        )
    if exc.kind == "rate_limit":
        return (
            "⚠️ **AI đang quá tải (rate limit)** — Vui lòng thử lại sau ít phút.\n\n"
            "Phân tích cơ bản từ dữ liệu hệ thống:\n\n"
            + base
        )
    if exc.kind == "auth":
        return (
            "🔑 **API key AI không hợp lệ hoặc chưa được cấu hình** — Sử dụng phân tích nội bộ:\n\n"
            + base
        )
    if exc.kind == "unavailable":
        return (
            f"🛠️ **Dịch vụ AI tạm thời không khả dụng** (`{detail}`) — Sử dụng phân tích nội bộ:\n\n"
            + base
        )
    if exc.kind == "bad_request":
        return (
            f"⚠️ **Yêu cầu AI không hợp lệ** (`{detail}`) — Sử dụng phân tích nội bộ:\n\n"
            + base
        )
    if exc.kind == "missing_sdk":
        return (
            "🛠️ **Chưa cài thư viện `openai`** — chạy `pip install -r requirements.txt`. "
            "Đang dùng phân tích nội bộ:\n\n" + base
        )
    return (
        f"⚠️ **Lỗi AI (`{exc.kind}`)** — Sử dụng phân tích nội bộ:\n\n" + base
    )


async def analyze_consumption(
    household_name: str,
    readings: list,
    invoices: list,
) -> str:
    """
    Gọi AI (chuẩn OpenAI) phân tích tiêu thụ điện nước.
    Trả về chuỗi markdown nhận xét.
    """
    if not is_configured():
        return (
            "ℹ️ **Chưa cấu hình AI_API_KEY** — đang dùng phân tích nội bộ.\n\n"
            + _mock_analysis(household_name, readings, invoices)
        )

    user_prompt = _build_user_prompt(household_name, readings, invoices)

    try:
        result = await chat_completion(SYSTEM_PROMPT, user_prompt, temperature=0.7)

        # Model dừng vì hết token → thử lại 1 lần với ngân sách lớn hơn.
        if result.finish_reason == "length":
            result = await chat_completion(
                SYSTEM_PROMPT,
                user_prompt,
                temperature=0.7,
                max_tokens=8192,
            )

        text = (result.text or "").strip()

        if not text:
            return (
                "⚠️ **AI trả về kết quả rỗng** — Sử dụng phân tích nội bộ:\n\n"
                + _mock_analysis(household_name, readings, invoices)
            )

        if result.finish_reason == "length":
            return (
                "⚠️ **Phản hồi AI bị cắt do giới hạn độ dài** — Sử dụng phân tích nội bộ:\n\n"
                + _mock_analysis(household_name, readings, invoices)
            )

        # Kiểm tra độ dài tối thiểu (< 50 ký tự = phản hồi không đủ nội dung)
        if len(text) < 50:
            return (
                "⚠️ **Phản hồi AI không đủ nội dung** — Sử dụng phân tích nội bộ:\n\n"
                + _mock_analysis(household_name, readings, invoices)
            )

        return text

    except AIError as exc:
        return _error_fallback(exc, household_name, readings, invoices)
    except Exception as exc:
        # Fallback chung cho các lỗi không xác định
        error_type = type(exc).__name__
        return (
            f"⚠️ **Lỗi không xác định khi gọi AI** (`{error_type}: {str(exc)[:100]}`)\n\n"
            "Sử dụng phân tích nội bộ:\n\n"
            + _mock_analysis(household_name, readings, invoices)
        )


def _mock_analysis(household_name: str, readings: list, invoices: list) -> str:
    """Phân tích nội bộ khi chưa cấu hình AI hoặc AI không khả dụng."""
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
