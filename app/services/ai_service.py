"""
app/services/ai_service.py — Phân tích hóa đơn điện nước bằng AI

Sử dụng API chuẩn OpenAI (mặc định Qwen3.8-27B tại Intern-AI):
  - Nhận xét biến động tiêu thụ điện theo tháng
  - Cảnh báo dấu hiệu bất thường
  - Gợi ý tiết kiệm điện ở mức tham khảo

Xử lý lỗi đầy đủ: timeout, rate limit (429), API key, response rỗng,
finish_reason=length (bị cắt do giới hạn token), thiếu mục output, lỗi model.
"""
import logging
import time
from dataclasses import dataclass
from string import Template

from app.services.ai_client import AIError, chat_completion, is_configured
from app.services.alert_service import SPIKE_THRESHOLD_PCT
from app.services.prompt_loader import PROMPT_VERSION, load_prompt

logger = logging.getLogger(__name__)

# 5 mục bắt buộc theo SYSTEM_PROMPT — dùng để kiểm tra output có đầy đủ không.
REQUIRED_SECTIONS = ("📊", "📈", "⚠️", "💡", "💰")
MIN_ANALYSIS_LENGTH = 120
MAX_ANALYSIS_CHARS = 4000
MAX_PROMPT_CHARS = 6000
TRUNCATE_NOTE = "\n\n> *Nội dung đã được rút gọn do giới hạn hiển thị.*"

RETRY_INSTRUCTION = (
    "\n\nLƯU Ý: Phản hồi trước chưa đạt yêu cầu định dạng. "
    "Hãy trả lời lại đầy đủ 5 mục có nhãn: 📊 TỔNG QUAN, 📈 BIẾN ĐỘNG, "
    "⚠️ CẢNH BÁO, 💡 GỢI Ý TIẾT KIỆM, 💰 CHI PHÍ. Không bỏ mục nào."
)

# ── Prompt mặc định (fallback nếu thiếu file trong prompts/) ─────────────────
DEFAULT_SYSTEM_PROMPT = """Bạn là trợ lý AI phân tích hóa đơn điện nước cho hệ thống quản lý hộ gia đình.
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
5. Nếu dữ liệu thiếu, âm hoặc mâu thuẫn, nói rõ và không suy diễn.
"""

DEFAULT_USER_TEMPLATE = """Hộ/phòng: $household_name

$readings_block

$invoices_block

$alerts_block

Ngưỡng cảnh báo: tăng > $threshold_pct% so với trung bình 3 kỳ gần nhất.

Hãy phân tích biến động tiêu thụ điện nước, chỉ ra tháng cần kiểm tra và gợi ý tiết kiệm.
"""

SYSTEM_PROMPT = load_prompt("consumption_system_v3.txt", DEFAULT_SYSTEM_PROMPT)
USER_TEMPLATE = load_prompt("consumption_user_template.txt", DEFAULT_USER_TEMPLATE)


@dataclass
class AnalysisResult:
    """Kết quả phân tích kèm metadata để UI hiển thị đúng nguồn/độ đầy đủ."""

    text: str
    source: str = "internal"          # "ai" | "internal"
    model: str = ""
    finish_reason: str = ""
    truncated: bool = False
    fallback_reason: str = ""
    prompt_version: str = PROMPT_VERSION


def _missing_sections(text: str) -> list[str]:
    """Trả về các mục còn thiếu trong output của model."""
    return [section for section in REQUIRED_SECTIONS if section not in text]


_SENTENCE_ENDINGS = (".", "!", "?", "…", "。", ")", "]", "”", "’", '"', "'")


def _ends_sentence(text: str) -> bool:
    """Heuristic: phản hồi phải kết thúc bằng dấu câu/ngoặc thay vì bị cắt giữa từ."""
    stripped = text.rstrip()
    return bool(stripped) and stripped[-1] in _SENTENCE_ENDINGS


def _is_complete(text: str) -> bool:
    """Output hợp lệ khi đủ 5 mục, đủ độ dài và kết thúc bằng dấu câu."""
    return (
        len(text.strip()) >= MIN_ANALYSIS_LENGTH
        and not _missing_sections(text)
        and _ends_sentence(text)
    )


def _build_user_prompt(
    household_name: str,
    readings: list,
    invoices: list,
    alerts: list | None = None,
    threshold_pct: int = SPIKE_THRESHOLD_PCT,
) -> str:
    """Xây dựng prompt người dùng từ dữ liệu tiêu thụ + hóa đơn + cảnh báo."""
    if readings:
        reading_lines = ["📋 Lịch sử tiêu thụ:"]
        for r in readings:
            unit_label = "kWh" if r["unit"] in ("kWh",) else "m³"
            type_label = "⚡ Điện" if r["meter_type"] == "electricity" else "💧 Nước"
            reading_lines.append(
                f"  - Kỳ {r['period']}: {type_label} = {r['consumption']} {unit_label}"
            )
        readings_block = "\n".join(reading_lines)
    else:
        readings_block = "Chưa có dữ liệu tiêu thụ."

    if invoices:
        invoice_lines = ["🧾 Hóa đơn:"]
        for inv in invoices:
            status_label = {"unpaid": "Chưa TT", "partial": "Một phần", "paid": "Đã TT"}.get(
                inv["status"], inv["status"]
            )
            invoice_lines.append(
                f"  - Kỳ {inv['period']}: "
                f"Điện={inv['electricity_amount']:,}đ | "
                f"Nước={inv['water_amount']:,}đ | "
                f"Tổng={inv['total_amount']:,}đ | "
                f"TT: {status_label}"
            )
        invoices_block = "\n".join(invoice_lines)
    else:
        invoices_block = "Chưa có hóa đơn."

    if alerts:
        alert_lines = ["⚠️ Cảnh báo nghiệp vụ chưa xử lý:"]
        for a in alerts:
            pct = a.get("percent_change")
            pct_text = f" (tăng {float(pct):.1f}%)" if pct is not None else ""
            alert_lines.append(
                f"  - Kỳ {a.get('period', '—')}: {a.get('message', '')}{pct_text}"
            )
        alerts_block = "\n".join(alert_lines)
    else:
        alerts_block = "Không có cảnh báo nghiệp vụ nào chưa xử lý."

    prompt = Template(USER_TEMPLATE).safe_substitute(
        household_name=household_name,
        readings_block=readings_block,
        invoices_block=invoices_block,
        alerts_block=alerts_block,
        threshold_pct=threshold_pct,
    )
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[:MAX_PROMPT_CHARS] + "\n\n[Đã rút gọn dữ liệu do giới hạn độ dài prompt]"
    return prompt


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
        wait = f" Thử lại sau khoảng {exc.retry_after} giây." if exc.retry_after else ""
        return (
            f"⚠️ **AI đang quá tải (rate limit)**.{wait} Vui lòng thử lại sau ít phút.\n\n"
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


async def analyze_consumption_detailed(
    household_name: str,
    readings: list,
    invoices: list,
    alerts: list | None = None,
) -> AnalysisResult:
    """
    Gọi AI phân tích và trả về text + metadata (source, model, finish_reason, truncated).

    Quy tắc:
      - `finish_reason=length` → retry 1 lần với 8192 token.
      - Thiếu mục/độ dài/kết thúc câu → retry 1 lần với nhắc định dạng.
      - Không đạt sau retry → fallback nội bộ, source="internal".
    """
    started = time.perf_counter()

    def finish(
        text: str,
        *,
        source: str = "internal",
        model: str = "",
        finish_reason: str = "",
        truncated: bool = False,
        fallback_reason: str = "",
        usage: dict | None = None,
    ) -> AnalysisResult:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        total_tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
        logger.info(
            "ai_analysis household=%s source=%s model=%s finish=%s truncated=%s "
            "chars=%d elapsed_ms=%d total_tokens=%s fallback=%s prompt=%s",
            household_name,
            source,
            model or "-",
            finish_reason or "-",
            truncated,
            len(text),
            elapsed_ms,
            total_tokens if total_tokens is not None else "-",
            fallback_reason or "-",
            PROMPT_VERSION,
        )
        return AnalysisResult(
            text=text,
            source=source,
            model=model,
            finish_reason=finish_reason,
            truncated=truncated,
            fallback_reason=fallback_reason,
            prompt_version=PROMPT_VERSION,
        )

    if not is_configured():
        return finish(
            "ℹ️ **Chưa cấu hình AI_API_KEY** — đang dùng phân tích nội bộ.\n\n"
            + _mock_analysis(household_name, readings, invoices),
            fallback_reason="no_key",
        )

    user_prompt = _build_user_prompt(
        household_name,
        readings,
        invoices,
        alerts=alerts,
    )

    try:
        result = await chat_completion(SYSTEM_PROMPT, user_prompt, temperature=0.7)
        length_retry_done = False

        # Model dừng vì hết token → thử lại 1 lần với ngân sách lớn hơn.
        if result.finish_reason == "length":
            result = await chat_completion(
                SYSTEM_PROMPT,
                user_prompt,
                temperature=0.7,
                max_tokens=8192,
            )
            length_retry_done = True
            if result.finish_reason == "length":
                return finish(
                    "⚠️ **Phản hồi AI bị cắt do giới hạn độ dài** — Sử dụng phân tích nội bộ:\n\n"
                    + _mock_analysis(household_name, readings, invoices),
                    truncated=True,
                    finish_reason=result.finish_reason,
                    fallback_reason="truncated",
                    usage=result.usage,
                )

        text = (result.text or "").strip()

        if not text:
            return finish(
                "⚠️ **AI trả về kết quả rỗng** — Sử dụng phân tích nội bộ:\n\n"
                + _mock_analysis(household_name, readings, invoices),
                finish_reason=result.finish_reason,
                fallback_reason="empty",
                usage=result.usage,
            )

        # Thiếu mục/độ dài/kết thúc câu → retry 1 lần với nhắc định dạng.
        if not _is_complete(text) and not length_retry_done:
            retry = await chat_completion(
                SYSTEM_PROMPT,
                user_prompt + RETRY_INSTRUCTION,
                temperature=0.4,
            )

            if retry.finish_reason == "length":
                return finish(
                    "⚠️ **Phản hồi AI bị cắt do giới hạn độ dài** — Sử dụng phân tích nội bộ:\n\n"
                    + _mock_analysis(household_name, readings, invoices),
                    truncated=True,
                    finish_reason=retry.finish_reason,
                    fallback_reason="truncated",
                    usage=retry.usage,
                )

            retry_text = (retry.text or "").strip()
            if retry_text and _is_complete(retry_text):
                result = retry
                text = retry_text
            else:
                return finish(
                    "⚠️ **Phản hồi AI chưa đầy đủ 5 mục** — Sử dụng phân tích nội bộ:\n\n"
                    + _mock_analysis(household_name, readings, invoices),
                    finish_reason=retry.finish_reason or result.finish_reason,
                    fallback_reason="incomplete",
                    usage=retry.usage or result.usage,
                )

        if not _is_complete(text):
            return finish(
                "⚠️ **Phản hồi AI chưa đầy đủ 5 mục** — Sử dụng phân tích nội bộ:\n\n"
                + _mock_analysis(household_name, readings, invoices),
                finish_reason=result.finish_reason,
                fallback_reason="incomplete",
                usage=result.usage,
            )

        # Giới hạn độ dài hiển thị; cắt ở newline gần nhất để tránh vỡ câu.
        truncated = False
        if len(text) > MAX_ANALYSIS_CHARS:
            cut = text.rfind("\n", 0, MAX_ANALYSIS_CHARS)
            if cut < MIN_ANALYSIS_LENGTH:
                cut = MAX_ANALYSIS_CHARS
            text = text[:cut].rstrip() + TRUNCATE_NOTE
            truncated = True

        return finish(
            text,
            source="ai",
            model=result.model,
            finish_reason=result.finish_reason,
            truncated=truncated,
            usage=result.usage,
        )

    except AIError as exc:
        return finish(
            _error_fallback(exc, household_name, readings, invoices),
            fallback_reason=exc.kind,
        )
    except Exception as exc:
        # Fallback chung cho các lỗi không xác định
        error_type = type(exc).__name__
        return finish(
            f"⚠️ **Lỗi không xác định khi gọi AI** (`{error_type}: {str(exc)[:100]}`)\n\n"
            "Sử dụng phân tích nội bộ:\n\n"
            + _mock_analysis(household_name, readings, invoices),
            fallback_reason="unknown",
        )


async def analyze_consumption(
    household_name: str,
    readings: list,
    invoices: list,
    alerts: list | None = None,
) -> str:
    """Wrapper tương thích cũ — chỉ trả text, dùng cho test hoặc nơi không cần metadata."""
    result = await analyze_consumption_detailed(
        household_name,
        readings,
        invoices,
        alerts=alerts,
    )
    return result.text


def _mock_analysis(household_name: str, readings: list, invoices: list) -> str:
    """Phân tích nội bộ khi chưa cấu hình AI hoặc AI không khả dụng."""
    # Sắp xếp theo kỳ tăng dần: API trả DESC (mới nhất trước), nhưng phần
    # so sánh "tháng trước" cần kỳ mới nhất nằm ở cuối danh sách.
    ordered = sorted(readings, key=lambda r: str(r.get("period", "")))
    elec_readings = [r for r in ordered if r.get("meter_type") == "electricity"]
    water_readings = [r for r in ordered if r.get("meter_type") == "water"]

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
            if pct > SPIKE_THRESHOLD_PCT:
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
