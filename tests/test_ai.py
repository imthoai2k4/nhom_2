"""
tests/test_ai.py — Kiểm thử chức năng AI (ai_service.py + ai_client.py)

Bao gồm các trường hợp:
  - Dữ liệu hợp lệ (đúng)
  - Dữ liệu rỗng (biên)
  - Dữ liệu tăng đột biến / âm / mâu thuẫn (sai / biên)
  - Không có API key → fallback nội bộ
  - Timeout / rate limit / response rỗng / response bị cắt (finish_reason=length)
  - Output thiếu mục → retry định dạng → fallback
  - Cấu hình OpenAI-compatible: base URL, model Qwen3.8-27B

Chạy: python -m pytest tests/test_ai.py -v
"""
import asyncio
from unittest.mock import AsyncMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────────
def _make_readings(consumptions_elec, consumptions_water=None):
    """Tạo danh sách readings mẫu."""
    readings = []
    for i, c in enumerate(consumptions_elec):
        readings.append({
            "period": f"2026-{i+1:02d}",
            "meter_type": "electricity",
            "consumption": c,
            "unit": "kWh",
        })
    if consumptions_water:
        for i, c in enumerate(consumptions_water):
            readings.append({
                "period": f"2026-{i+1:02d}",
                "meter_type": "water",
                "consumption": c,
                "unit": "m3",
            })
    return readings


def _make_invoices(total_amounts, statuses=None):
    """Tạo danh sách invoices mẫu."""
    if statuses is None:
        statuses = ["paid"] * len(total_amounts)
    invoices = []
    for i, (amt, st) in enumerate(zip(total_amounts, statuses)):
        invoices.append({
            "period": f"2026-{i+1:02d}",
            "electricity_amount": int(amt * 0.7),
            "water_amount": int(amt * 0.3),
            "total_amount": amt,
            "status": st,
        })
    return invoices


# Output hợp lệ: đủ 5 mục + đủ độ dài tối thiểu (dùng cho test completeness).
FULL_ANALYSIS = (
    "📊 TỔNG QUAN: Tiêu thụ điện nước của hộ ổn định trong 6 tháng gần nhất, "
    "trung bình khoảng 150 kWh điện và 15 m³ nước mỗi tháng.\n"
    "📈 BIẾN ĐỘNG: Tháng 7 tăng nhẹ 4% so với tháng 6, không có đột biến lớn.\n"
    "⚠️ CẢNH BÁO: Chưa phát hiện tháng nào cần kiểm tra đặc biệt.\n"
    "💡 GỢI Ý TIẾT KIỆM: Dùng đèn LED, tắt thiết bị khi không dùng và bảo trì đồng hồ định kỳ.\n"
    "💰 CHI PHÍ: Hóa đơn tháng 7 khoảng 350.000đ; có thể tiết kiệm 10% nếu duy trì mức hiện tại."
)

# Output thiếu 4/5 mục nhưng vẫn đủ dài — dùng để test retry định dạng.
PARTIAL_ANALYSIS = "📊 TỔNG QUAN: " + ("Dữ liệu tiêu thụ ổn định. " * 10)


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 1: Test _mock_analysis (không cần API key)
# ═══════════════════════════════════════════════════════════════════════════════
class TestMockAnalysis:
    """TC-AI-001 → TC-AI-007: Kiểm thử phân tích nội bộ (mock)."""

    def setup_method(self):
        from app.services.ai_service import _mock_analysis
        self.analyze = _mock_analysis

    # TC-AI-001: Dữ liệu điện hợp lệ, biến động bình thường
    def test_TC_AI_001_normal_electricity(self):
        """Dữ liệu điện bình thường → phân tích có tổng quan và gợi ý."""
        readings = _make_readings([150, 145, 160, 155, 140, 150])
        result = self.analyze("Phòng 101", readings, [])
        assert "📊" in result, "Phải có tổng quan"
        assert "⚡" in result, "Phải có phần điện"
        assert "💡" in result, "Phải có gợi ý tiết kiệm"
        assert "Phòng 101" in result, "Phải có tên hộ"

    # TC-AI-002: Tăng đột biến > 20% → cảnh báo ⚠️
    def test_TC_AI_002_electricity_spike(self):
        """Điện tăng đột biến > 20% → phải cảnh báo."""
        readings = _make_readings([100, 200])  # tăng 100%
        result = self.analyze("Phòng 102", readings, [])
        assert "⚠️" in result or "Tăng" in result, "Phải cảnh báo khi tăng đột biến"

    # TC-AI-003: Giảm > 10% → thông báo giảm ✅
    def test_TC_AI_003_electricity_decrease(self):
        """Điện giảm > 10% → thông báo giảm."""
        readings = _make_readings([200, 150])  # giảm 25%
        result = self.analyze("Phòng 103", readings, [])
        assert "Giảm" in result or "✅" in result, "Phải ghi nhận giảm tiêu thụ"

    # TC-AI-004: Dữ liệu rỗng → không crash, trả về chuỗi hợp lệ
    def test_TC_AI_004_empty_data(self):
        """Không có readings/invoices → không crash, trả về markdown hợp lệ."""
        result = self.analyze("Phòng 104", [], [])
        assert isinstance(result, str), "Phải trả về chuỗi"
        assert len(result) > 0, "Không được trả về chuỗi rỗng"

    # TC-AI-005: Chỉ có dữ liệu nước, không có điện
    def test_TC_AI_005_water_only(self):
        """Chỉ có dữ liệu nước → có phần nước trong kết quả."""
        readings = _make_readings([], [5, 6, 5.5, 7])
        result = self.analyze("Phòng 105", readings, [])
        assert "💧" in result, "Phải có phần nước"

    # TC-AI-006: Tiêu thụ âm (dữ liệu lỗi) → không crash
    def test_TC_AI_006_negative_consumption(self):
        """Dữ liệu tiêu thụ âm (lỗi nghiệp vụ) → hàm không crash."""
        readings = _make_readings([-50, 100])
        result = self.analyze("Phòng 106", readings, [])
        assert isinstance(result, str), "Không được crash với dữ liệu âm"

    # TC-AI-007: Chỉ 1 điểm dữ liệu → không so sánh biến động (không crash)
    def test_TC_AI_007_single_data_point(self):
        """Chỉ 1 tháng dữ liệu → không tính biến động, không crash."""
        readings = _make_readings([120])
        result = self.analyze("Phòng 107", readings, [])
        assert "120" in result or "kWh" in result or "📊" in result

    # TC-AI-028: Dữ liệu DESC từ API → vẫn so sánh đúng tháng gần nhất
    def test_TC_AI_028_desc_order_latest_trend(self):
        """Readings DESC (mới nhất trước) → báo tăng +4.0%, không báo giảm."""
        readings = [
            {"period": "2026-07", "meter_type": "electricity", "consumption": 78.0, "unit": "kWh"},
            {"period": "2026-06", "meter_type": "electricity", "consumption": 75.0, "unit": "kWh"},
            {"period": "2026-05", "meter_type": "electricity", "consumption": 65.0, "unit": "kWh"},
        ]
        result = self.analyze("Phòng 120", readings, [])
        assert "Biến động bình thường" in result
        assert "+4.0%" in result
        assert "Giảm 13.3%" not in result

    # TC-AI-029: DESC + tăng >20% → cảnh báo tăng, không báo giảm
    def test_TC_AI_029_desc_order_spike(self):
        """Readings DESC với mức tăng 33.3% → phải cảnh báo tăng."""
        readings = [
            {"period": "2026-07", "meter_type": "electricity", "consumption": 200.0, "unit": "kWh"},
            {"period": "2026-06", "meter_type": "electricity", "consumption": 150.0, "unit": "kWh"},
            {"period": "2026-05", "meter_type": "electricity", "consumption": 100.0, "unit": "kWh"},
        ]
        result = self.analyze("Phòng 121", readings, [])
        assert "Tăng 33.3%" in result
        assert "Giảm" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 2: Test analyze_consumption (async, mock lớp AI client)
# ═══════════════════════════════════════════════════════════════════════════════
class TestAnalyzeConsumption:
    """TC-AI-008 → TC-AI-027: Kiểm thử analyze_consumption với các lỗi AI."""

    # TC-AI-008: Không có API key → fallback nội bộ, không crash
    def test_TC_AI_008_no_api_key(self):
        """Không có AI_API_KEY → fallback về _mock_analysis."""
        from app.services.ai_service import analyze_consumption

        with patch("app.services.ai_service.is_configured", return_value=False):
            result = asyncio.run(
                analyze_consumption("Phòng 108", _make_readings([150, 160]), [])
            )
        assert "Chưa cấu hình" in result
        assert len(result) > 50, "Kết quả phải có nội dung"

    # TC-AI-009: Timeout → thông báo timeout + fallback
    def test_TC_AI_009_timeout_error(self):
        """Timeout khi gọi AI → trả về thông báo timeout + phân tích nội bộ."""
        from app.services.ai_client import AIError
        from app.services.ai_service import analyze_consumption

        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch(
                 "app.services.ai_service.chat_completion",
                 new=AsyncMock(side_effect=AIError("timeout", "deadline exceeded")),
             ):
            result = asyncio.run(
                analyze_consumption("Phòng 109", _make_readings([100, 120]), [])
            )
        assert "timeout" in result.lower() or "⏱️" in result

    # TC-AI-010: Rate limit → thông báo rate limit + fallback
    def test_TC_AI_010_rate_limit_error(self):
        """Rate limit → trả về thông báo + phân tích nội bộ."""
        from app.services.ai_client import AIError
        from app.services.ai_service import analyze_consumption

        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch(
                 "app.services.ai_service.chat_completion",
                 new=AsyncMock(side_effect=AIError("rate_limit", "429 quota")),
             ):
            result = asyncio.run(
                analyze_consumption("Phòng 110", _make_readings([100, 120]), [])
            )
        assert "rate limit" in result.lower() or "quá tải" in result.lower()

    # TC-AI-011: Response rỗng từ API → fallback
    def test_TC_AI_011_empty_response(self):
        """AI trả về text rỗng → fallback phân tích nội bộ."""
        from app.services.ai_client import ChatResult
        from app.services.ai_service import analyze_consumption

        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch(
                 "app.services.ai_service.chat_completion",
                 new=AsyncMock(return_value=ChatResult(text="", finish_reason="stop")),
             ):
            result = asyncio.run(
                analyze_consumption("Phòng 111", _make_readings([100]), [])
            )
        assert "rỗng" in result.lower()
        assert len(result) > 0, "Phải có fallback khi response rỗng"

    # TC-AI-012: Response đủ nội dung → trả về nguyên văn
    def test_TC_AI_012_valid_ai_response(self):
        """AI trả về nội dung hợp lệ → trả thẳng kết quả của model."""
        from app.services.ai_client import ChatResult
        from app.services.ai_service import analyze_consumption

        expected = FULL_ANALYSIS
        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch(
                 "app.services.ai_service.chat_completion",
                 new=AsyncMock(
                     return_value=ChatResult(
                         text=expected,
                         finish_reason="stop",
                         model="qwen3.8-27b",
                     )
                 ),
             ):
            result = asyncio.run(
                analyze_consumption("Phòng 112", _make_readings([150, 145, 160]), [])
            )
        assert result == expected, "Phải trả về nguyên văn kết quả AI khi hợp lệ"

    # TC-AI-013: finish_reason=length lần đầu → retry 1 lần với max_tokens lớn hơn
    def test_TC_AI_013_length_retry(self):
        """Lần đầu bị cắt (length) → retry và nhận kết quả đầy đủ."""
        from app.services.ai_client import ChatResult
        from app.services.ai_service import analyze_consumption

        expected = FULL_ANALYSIS
        mock = AsyncMock(side_effect=[
            ChatResult(text="📊 TỔNG QUAN: ngắn", finish_reason="length"),
            ChatResult(text=expected, finish_reason="stop", model="qwen3.8-27b"),
        ])
        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch("app.services.ai_service.chat_completion", new=mock):
            result = asyncio.run(
                analyze_consumption("Phòng 113", _make_readings([120, 130]), [])
            )
        assert result == expected
        assert mock.await_count == 2, "Phải retry đúng 1 lần"

    # TC-AI-014: finish_reason=length cả 2 lần → fallback, không trả nửa câu
    def test_TC_AI_014_length_still_truncated(self):
        """Vẫn bị cắt sau retry → fallback và thông báo rõ."""
        from app.services.ai_client import ChatResult
        from app.services.ai_service import analyze_consumption

        mock = AsyncMock(return_value=ChatResult(text="📊 TỔNG QUAN: ngắn", finish_reason="length"))
        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch("app.services.ai_service.chat_completion", new=mock):
            result = asyncio.run(
                analyze_consumption("Phòng 114", _make_readings([100, 110]), [])
            )
        assert "giới hạn độ dài" in result.lower()

    # TC-AI-023: Thiếu mục → retry định dạng; lần 2 đủ → dùng kết quả lần 2
    def test_TC_AI_023_incomplete_retry(self):
        """Output thiếu 4/5 mục → retry 1 lần và nhận kết quả đầy đủ."""
        from app.services.ai_client import ChatResult
        from app.services.ai_service import analyze_consumption_detailed

        mock = AsyncMock(side_effect=[
            ChatResult(text=PARTIAL_ANALYSIS, finish_reason="stop"),
            ChatResult(text=FULL_ANALYSIS, finish_reason="stop", model="qwen3.8-27b"),
        ])
        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch("app.services.ai_service.chat_completion", new=mock):
            result = asyncio.run(
                analyze_consumption_detailed("Phòng 115", _make_readings([120, 130]), [])
            )
        assert result.text == FULL_ANALYSIS
        assert result.source == "ai"
        assert mock.await_count == 2, "Phải retry đúng 1 lần vì thiếu mục"

    # TC-AI-024: Thiếu mục cả 2 lần → fallback, source internal
    def test_TC_AI_024_incomplete_after_retry(self):
        """Retry vẫn thiếu mục → fallback nội bộ và báo rõ."""
        from app.services.ai_client import ChatResult
        from app.services.ai_service import analyze_consumption_detailed

        mock = AsyncMock(return_value=ChatResult(text=PARTIAL_ANALYSIS, finish_reason="stop"))
        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch("app.services.ai_service.chat_completion", new=mock):
            result = asyncio.run(
                analyze_consumption_detailed("Phòng 116", _make_readings([100, 110]), [])
            )
        assert result.source == "internal"
        assert result.fallback_reason == "incomplete"
        assert "chưa đầy đủ" in result.text.lower()
        assert mock.await_count == 2

    # TC-AI-025: Detailed result khi chưa có key → source internal
    def test_TC_AI_025_detailed_no_key(self):
        """Không có key → metadata source=internal, fallback_reason=no_key."""
        from app.services.ai_service import analyze_consumption_detailed

        with patch("app.services.ai_service.is_configured", return_value=False):
            result = asyncio.run(
                analyze_consumption_detailed("Phòng 117", _make_readings([150, 160]), [])
            )
        assert result.source == "internal"
        assert result.fallback_reason == "no_key"
        assert "Chưa cấu hình" in result.text

    # TC-AI-026: Detailed result khi AI trả đủ → metadata nguồn/model
    def test_TC_AI_026_detailed_success_metadata(self):
        """AI trả đủ 5 mục → source=ai, model/finish_reason/truncated đúng."""
        from app.services.ai_client import ChatResult
        from app.services.ai_service import analyze_consumption_detailed

        mock = AsyncMock(return_value=ChatResult(
            text=FULL_ANALYSIS,
            finish_reason="stop",
            model="qwen3.8-27b",
        ))
        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch("app.services.ai_service.chat_completion", new=mock):
            result = asyncio.run(
                analyze_consumption_detailed("Phòng 118", _make_readings([150, 145, 160]), [])
            )
        assert result.source == "ai"
        assert result.model == "qwen3.8-27b"
        assert result.finish_reason == "stop"
        assert result.truncated is False
        assert result.fallback_reason == ""

    # TC-AI-027: Bị cắt cả 2 lần → metadata truncated, fallback
    def test_TC_AI_027_detailed_truncated(self):
        """finish_reason=length cả 2 lần → source internal, truncated=True."""
        from app.services.ai_client import ChatResult
        from app.services.ai_service import analyze_consumption_detailed

        mock = AsyncMock(return_value=ChatResult(text="📊 ngắn", finish_reason="length"))
        with patch("app.services.ai_service.is_configured", return_value=True), \
             patch("app.services.ai_service.chat_completion", new=mock):
            result = asyncio.run(
                analyze_consumption_detailed("Phòng 119", _make_readings([100, 110]), [])
            )
        assert result.source == "internal"
        assert result.truncated is True
        assert result.fallback_reason == "truncated"
        assert "giới hạn độ dài" in result.text.lower()
        assert mock.await_count == 2


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 3: Test cấu hình OpenAI-compatible
# ═══════════════════════════════════════════════════════════════════════════════
class TestAIConfig:
    """TC-AI-020 → TC-AI-021: Kiểm thử base URL / model mặc định và override."""

    def test_TC_AI_020_default_config(self, monkeypatch):
        """Không có env → dùng base URL và model Qwen3.8-27B mặc định."""
        from app.services.ai_client import get_config

        for key in (
            "AI_API_KEY",
            "OPENAI_API_KEY",
            "AI_BASE_URL",
            "AI_MODEL",
            "AI_TIMEOUT",
            "AI_MAX_TOKENS",
        ):
            monkeypatch.delenv(key, raising=False)

        cfg = get_config()
        assert cfg.base_url == "https://discovery-api.intern-ai.org.cn/v1"
        assert cfg.model == "qwen3.8-27b"
        assert cfg.timeout == 30.0
        assert cfg.max_tokens == 4096

    def test_TC_AI_021_env_override(self, monkeypatch):
        """Env override được base URL/model; bỏ dấu '/' cuối base URL."""
        from app.services.ai_client import get_config

        monkeypatch.setenv("AI_BASE_URL", "https://example.com/v1/")
        monkeypatch.setenv("AI_MODEL", "qwen-test")

        cfg = get_config()
        assert cfg.base_url == "https://example.com/v1"
        assert cfg.model == "qwen-test"


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 3B: Test lớp client gửi đúng giao thức OpenAI
# ═══════════════════════════════════════════════════════════════════════════════
class TestAIClient:
    """TC-AI-022: Kiểm tra payload/URL/model đúng chuẩn OpenAI."""

    def test_TC_AI_022_openai_wire_format(self, monkeypatch):
        """Client phải gửi system/user message, model Qwen và base URL đã cấu hình."""
        import sys
        import types
        from app.services.ai_client import chat_completion

        monkeypatch.setenv("AI_API_KEY", "test-key")
        monkeypatch.delenv("AI_BASE_URL", raising=False)
        monkeypatch.delenv("AI_MODEL", raising=False)

        captured = {}

        class FakeCompletions:
            async def create(self, **kwargs):
                captured.update(kwargs)
                return types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            message=types.SimpleNamespace(content="📊 TỔNG QUAN: ok"),
                            finish_reason="stop",
                        )
                    ],
                    model="qwen3.8-27b",
                    usage=None,
                )

        class FakeAsyncOpenAI:
            def __init__(self, **kwargs):
                captured["client"] = kwargs
                self.chat = types.SimpleNamespace(completions=FakeCompletions())

            async def close(self):
                pass

        fake_module = types.SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI)
        with patch.dict(sys.modules, {"openai": fake_module}):
            result = asyncio.run(chat_completion("Hệ thống", "Dữ liệu"))

        assert result.text == "📊 TỔNG QUAN: ok"
        assert result.finish_reason == "stop"
        assert captured["model"] == "qwen3.8-27b"
        assert captured["messages"] == [
            {"role": "system", "content": "Hệ thống"},
            {"role": "user", "content": "Dữ liệu"},
        ]
        assert captured["client"]["base_url"] == "https://discovery-api.intern-ai.org.cn/v1"
        assert captured["client"]["api_key"] == "test-key"


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 4: Test _build_user_prompt
# ═══════════════════════════════════════════════════════════════════════════════
class TestBuildUserPrompt:
    """TC-AI-016 → TC-AI-019: Kiểm thử hàm xây dựng prompt."""

    def setup_method(self):
        from app.services.ai_service import _build_user_prompt
        self.build = _build_user_prompt

    # TC-AI-016: Prompt có tên hộ
    def test_TC_AI_016_prompt_contains_household_name(self):
        readings = _make_readings([100])
        prompt = self.build("Phòng 201", readings, [])
        assert "Phòng 201" in prompt

    # TC-AI-017: Prompt có dữ liệu tiêu thụ
    def test_TC_AI_017_prompt_contains_consumption(self):
        readings = _make_readings([123.5])
        prompt = self.build("Phòng 202", readings, [])
        assert "123.5" in prompt or "kWh" in prompt

    # TC-AI-018: Prompt có dữ liệu hóa đơn
    def test_TC_AI_018_prompt_contains_invoice(self):
        invoices = _make_invoices([500000], ["unpaid"])
        prompt = self.build("Phòng 203", [], invoices)
        assert "500000" in prompt or "Chưa TT" in prompt

    # TC-AI-019: Prompt có yêu cầu phân tích ở cuối
    def test_TC_AI_019_prompt_ends_with_request(self):
        prompt = self.build("Phòng 204", [], [])
        assert "phân tích" in prompt.lower() or "gợi ý" in prompt.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Chạy trực tiếp (không cần pytest)
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    print("=" * 60)
    print("Chạy test AI thủ công (không cần pytest)")
    print("=" * 60)

    suite = TestMockAnalysis()
    suite.setup_method()
    tests = [
        ("TC-AI-001", suite.test_TC_AI_001_normal_electricity),
        ("TC-AI-002", suite.test_TC_AI_002_electricity_spike),
        ("TC-AI-003", suite.test_TC_AI_003_electricity_decrease),
        ("TC-AI-004", suite.test_TC_AI_004_empty_data),
        ("TC-AI-005", suite.test_TC_AI_005_water_only),
        ("TC-AI-006", suite.test_TC_AI_006_negative_consumption),
        ("TC-AI-007", suite.test_TC_AI_007_single_data_point),
    ]

    passed = 0
    failed = 0
    for tc_id, fn in tests:
        try:
            fn()
            print(f"  ✅ {tc_id}: PASSED")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {tc_id}: FAILED — {e}")
            failed += 1
        except Exception as e:
            print(f"  ⚠️  {tc_id}: ERROR — {type(e).__name__}: {e}")
            failed += 1

    prompt_suite = TestBuildUserPrompt()
    prompt_suite.setup_method()
    prompt_tests = [
        ("TC-AI-016", prompt_suite.test_TC_AI_016_prompt_contains_household_name),
        ("TC-AI-017", prompt_suite.test_TC_AI_017_prompt_contains_consumption),
        ("TC-AI-018", prompt_suite.test_TC_AI_018_prompt_contains_invoice),
        ("TC-AI-019", prompt_suite.test_TC_AI_019_prompt_ends_with_request),
    ]
    for tc_id, fn in prompt_tests:
        try:
            fn()
            print(f"  ✅ {tc_id}: PASSED")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {tc_id}: FAILED — {e}")
            failed += 1
        except Exception as e:
            print(f"  ⚠️  {tc_id}: ERROR — {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Kết quả: {passed} PASSED / {failed} FAILED / {passed+failed} TOTAL")
    print("=" * 60)
