"""
tests/test_ai.py — Kiểm thử chức năng AI (ai_service.py)

Bao gồm các trường hợp:
  - Dữ liệu hợp lệ (đúng)
  - Dữ liệu rỗng (biên)
  - Dữ liệu tăng đột biến / âm / mâu thuẫn (sai / biên)
  - Không có API key → fallback mock
  - Response rỗng / timeout / rate limit

Chạy: python -m pytest tests/test_ai.py -v
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock


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


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 2: Test analyze_consumption (hàm async, kiểm tra fallback khi không có key)
# ═══════════════════════════════════════════════════════════════════════════════
class TestAnalyzeConsumption:
    """TC-AI-008 → TC-AI-015: Kiểm thử hàm analyze_consumption async."""

    # TC-AI-008: Không có API key → dùng mock analysis, không crash
    def test_TC_AI_008_no_api_key(self):
        """Không có GEMINI_API_KEY → fallback về _mock_analysis."""
        with patch("app.services.ai_service._GEMINI_KEY", ""):
            from app.services.ai_service import analyze_consumption
            readings = _make_readings([150, 160])
            result = asyncio.get_event_loop().run_until_complete(
                analyze_consumption("Phòng 108", readings, [])
            )
        assert isinstance(result, str)
        assert len(result) > 50, "Kết quả phải có nội dung"

    # TC-AI-009: Timeout → thông báo timeout + fallback
    def test_TC_AI_009_timeout_error(self):
        """Timeout khi gọi Gemini → trả về thông báo timeout + phân tích nội bộ."""
        with patch("app.services.ai_service._GEMINI_KEY", "fake-key"):
            with patch("google.generativeai.GenerativeModel") as mock_model:
                mock_instance = MagicMock()
                mock_instance.generate_content.side_effect = Exception("deadline exceeded timeout")
                mock_model.return_value = mock_instance
                with patch("google.generativeai.configure"):
                    from app.services import ai_service
                    import importlib
                    importlib.reload(ai_service)
                    ai_service._GEMINI_KEY = "fake-key"

                    readings = _make_readings([100, 120])
                    result = asyncio.get_event_loop().run_until_complete(
                        ai_service.analyze_consumption("Phòng 109", readings, [])
                    )
        assert isinstance(result, str)
        # Phải trả về chuỗi hợp lệ (timeout hoặc fallback)
        assert len(result) > 0

    # TC-AI-010: Rate limit → thông báo rate limit + fallback
    def test_TC_AI_010_rate_limit_error(self):
        """Rate limit → trả về thông báo + phân tích nội bộ."""
        with patch("app.services.ai_service._GEMINI_KEY", "fake-key"):
            with patch("google.generativeai.GenerativeModel") as mock_model:
                mock_instance = MagicMock()
                mock_instance.generate_content.side_effect = Exception("quota resource_exhausted 429")
                mock_model.return_value = mock_instance
                with patch("google.generativeai.configure"):
                    from app.services import ai_service
                    ai_service._GEMINI_KEY = "fake-key"
                    readings = _make_readings([100, 120])
                    result = asyncio.get_event_loop().run_until_complete(
                        ai_service.analyze_consumption("Phòng 110", readings, [])
                    )
        assert isinstance(result, str)
        assert len(result) > 0

    # TC-AI-011: Response rỗng từ API → fallback
    def test_TC_AI_011_empty_response(self):
        """AI trả về text rỗng → fallback phân tích nội bộ."""
        with patch("app.services.ai_service._GEMINI_KEY", "fake-key"):
            with patch("google.generativeai.GenerativeModel") as mock_model:
                mock_resp = MagicMock()
                mock_resp.text = ""   # response rỗng
                mock_instance = MagicMock()
                mock_instance.generate_content.return_value = mock_resp
                mock_model.return_value = mock_instance
                with patch("google.generativeai.configure"):
                    from app.services import ai_service
                    ai_service._GEMINI_KEY = "fake-key"
                    readings = _make_readings([100])
                    result = asyncio.get_event_loop().run_until_complete(
                        ai_service.analyze_consumption("Phòng 111", readings, [])
                    )
        assert isinstance(result, str)
        assert len(result) > 0, "Phải có fallback khi response rỗng"

    # TC-AI-012: Response đủ nội dung từ Gemini → trả về nguyên văn
    def test_TC_AI_012_valid_gemini_response(self):
        """Gemini trả về nội dung hợp lệ → trả thẳng kết quả của Gemini."""
        expected = "📊 TỔNG QUAN: Tiêu thụ ổn định trong 6 tháng qua, mức trung bình 150 kWh."
        with patch("app.services.ai_service._GEMINI_KEY", "fake-key"):
            with patch("google.generativeai.GenerativeModel") as mock_model:
                mock_resp = MagicMock()
                mock_resp.text = expected
                mock_instance = MagicMock()
                mock_instance.generate_content.return_value = mock_resp
                mock_model.return_value = mock_instance
                with patch("google.generativeai.configure"):
                    from app.services import ai_service
                    ai_service._GEMINI_KEY = "fake-key"
                    readings = _make_readings([150, 145, 160])
                    result = asyncio.get_event_loop().run_until_complete(
                        ai_service.analyze_consumption("Phòng 112", readings, [])
                    )
        assert result == expected, "Phải trả về nguyên văn kết quả Gemini khi hợp lệ"


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 3: Test _build_user_prompt
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
    import sys, os
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
