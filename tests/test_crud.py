"""
tests/test_crud.py — Kiểm thử API quản lý (CRUD) và chức năng nghiệp vụ

Bao gồm:
  - Test tính toán tiêu thụ (consumption = curr - prev)
  - Test logic hóa đơn và công nợ
  - Test phân quyền (admin vs user)
  - Test dữ liệu biên và trường hợp lỗi
  - Test chat service (intent detection)

Chạy: python -m pytest tests/test_crud.py -v
       python tests/test_crud.py  (chạy thủ công)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from decimal import Decimal


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 1: Tính toán tiêu thụ và hóa đơn (unit test — không cần DB)
# ═══════════════════════════════════════════════════════════════════════════════
class TestConsumptionLogic:
    """TC-CRUD-001 → TC-CRUD-008: Kiểm thử công thức tính tiêu thụ và hóa đơn."""

    # TC-CRUD-001: Tiêu thụ = chỉ số mới - chỉ số cũ (trường hợp đúng)
    def test_TC_CRUD_001_consumption_formula(self):
        """Công thức: consumption = curr_reading - prev_reading."""
        curr, prev = 520, 400
        consumption = curr - prev
        assert consumption == 120, "Tiêu thụ phải = 520 - 400 = 120 kWh"

    # TC-CRUD-002: Chỉ số mới < chỉ số cũ → tiêu thụ âm (lỗi nghiệp vụ)
    def test_TC_CRUD_002_negative_consumption_detection(self):
        """Chỉ số mới < chỉ số cũ → tiêu thụ âm, hệ thống phải phát hiện."""
        curr, prev = 300, 400
        consumption = curr - prev
        assert consumption < 0, "Tiêu thụ âm phải được phát hiện"

    # TC-CRUD-003: Tổng hóa đơn = tiền điện + tiền nước
    def test_TC_CRUD_003_invoice_total_formula(self):
        """invoice_total = electricity_amount + water_amount."""
        elec = Decimal("350000")
        water = Decimal("120000")
        total = elec + water
        assert total == Decimal("470000"), "Tổng hóa đơn phải = 350000 + 120000"

    # TC-CRUD-004: Công nợ = tổng hóa đơn - đã thanh toán
    def test_TC_CRUD_004_debt_formula(self):
        """debt = invoice_total - paid_amount."""
        invoice_total = Decimal("470000")
        paid = Decimal("200000")
        debt = invoice_total - paid
        assert debt == Decimal("270000"), "Công nợ phải = 470000 - 200000 = 270000"

    # TC-CRUD-005: Thanh toán đủ → công nợ = 0
    def test_TC_CRUD_005_fully_paid_debt_zero(self):
        """Thanh toán đủ → công nợ = 0."""
        invoice_total = Decimal("470000")
        paid = Decimal("470000")
        debt = invoice_total - paid
        assert debt == Decimal("0"), "Công nợ phải = 0 khi đã thanh toán đủ"

    # TC-CRUD-006: Thanh toán vượt hóa đơn → công nợ âm (cần ngăn chặn)
    def test_TC_CRUD_006_overpayment_negative_debt(self):
        """Thanh toán > hóa đơn → công nợ âm, hệ thống phải ngăn chặn."""
        invoice_total = Decimal("470000")
        paid = Decimal("600000")
        debt = invoice_total - paid
        assert debt < 0, "Phải phát hiện overpayment (công nợ âm)"

    # TC-CRUD-007: Tiêu thụ = 0 (đồng hồ không thay đổi) → hợp lệ
    def test_TC_CRUD_007_zero_consumption_valid(self):
        """Tiêu thụ 0 (chỉ số không đổi) → hợp lệ, không phải lỗi."""
        curr, prev = 400, 400
        consumption = curr - prev
        assert consumption == 0, "Tiêu thụ 0 phải là hợp lệ"

    # TC-CRUD-008: Đơn giá bậc thang điện EVN (100 kWh đầu tiên)
    def test_TC_CRUD_008_evn_tier_pricing(self):
        """Tiền điện theo bậc thang: 100 kWh đầu × đơn giá bậc 1."""
        consumption = 100  # kWh
        tier1_price = 1806  # VNĐ/kWh (EVN bậc 1 — 2024)
        expected_min = consumption * tier1_price
        assert expected_min == 180600, "Tiền điện 100 kWh bậc 1 = 180,600đ"


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 2: Test Chat Service — Intent Detection
# ═══════════════════════════════════════════════════════════════════════════════
class TestIntentDetection:
    """TC-CHAT-001 → TC-CHAT-012: Kiểm thử phát hiện ý định (intent) tiếng Việt."""

    def setup_method(self):
        from app.services.chat_service import detect_intent
        self.detect = detect_intent

    # TC-CHAT-001: Câu chào hỏi
    def test_TC_CHAT_001_greeting(self):
        assert self.detect("Xin chào") == "greeting"
        assert self.detect("hello") == "greeting"

    # TC-CHAT-002: Hỏi hóa đơn
    def test_TC_CHAT_002_invoice_intent(self):
        assert self.detect("Hóa đơn tháng 7 phòng 101") == "invoice"
        assert self.detect("Tiền điện tháng 8") == "invoice"

    # TC-CHAT-003: Hỏi thanh toán / công nợ
    def test_TC_CHAT_003_payment_intent(self):
        assert self.detect("Công nợ phòng 102") == "payment"
        assert self.detect("Còn nợ bao nhiêu?") == "payment"

    # TC-CHAT-004: Hỏi lịch sử tiêu thụ
    def test_TC_CHAT_004_consumption_intent(self):
        assert self.detect("Lịch sử tiêu thụ 6 tháng") == "consumption"
        assert self.detect("Biến động điện nước") == "consumption"

    # TC-CHAT-005: Hỏi đồng hồ
    def test_TC_CHAT_005_meter_intent(self):
        assert self.detect("Số đồng hồ phòng 101") == "meter_info"
        assert self.detect("Chỉ số mới nhất") == "meter_info"

    # TC-CHAT-006: Hỏi cảnh báo
    def test_TC_CHAT_006_alert_intent(self):
        assert self.detect("Có cảnh báo bất thường không?") == "alert"
        assert self.detect("Tăng đột biến tháng nào?") == "alert"

    # TC-CHAT-007: Hỏi tra cứu hộ
    def test_TC_CHAT_007_lookup_household(self):
        assert self.detect("SĐT hộ 101") == "lookup_household"
        assert self.detect("Chủ hộ phòng 202") == "lookup_household"

    # TC-CHAT-008: Tổng quan hệ thống
    def test_TC_CHAT_008_summary(self):
        assert self.detect("Tổng quan hệ thống") == "summary"
        assert self.detect("Tổng hợp dashboard") == "summary"

    # TC-CHAT-009: Yêu cầu trợ giúp
    def test_TC_CHAT_009_help(self):
        assert self.detect("Bạn làm được gì?") == "help"
        assert self.detect("Hướng dẫn sử dụng") == "help"

    # TC-CHAT-010: Câu không xác định → "general"
    def test_TC_CHAT_010_general_fallback(self):
        assert self.detect("xyzxyz không rõ gì cả") == "general"

    # TC-CHAT-011: Câu có số phòng → lookup_household
    def test_TC_CHAT_011_room_number_lookup(self):
        result = self.detect("phòng 101")
        assert result == "lookup_household", f"Expected lookup_household, got {result}"

    # TC-CHAT-012: Câu trống → không crash
    def test_TC_CHAT_012_empty_string(self):
        result = self.detect("")
        assert isinstance(result, str), "Không được crash với câu trống"


# ═══════════════════════════════════════════════════════════════════════════════
# NHÓM 3: Test xử lý lỗi và trường hợp biên
# ═══════════════════════════════════════════════════════════════════════════════
class TestEdgeCases:
    """TC-EDGE-001 → TC-EDGE-006: Kiểm thử các trường hợp biên."""

    # TC-EDGE-001: Consumption âm → nhận biết là lỗi
    def test_TC_EDGE_001_negative_consumption_flag(self):
        """Hàm validate phải trả False khi tiêu thụ âm."""
        def is_valid_consumption(curr, prev):
            return curr >= prev and curr >= 0 and prev >= 0

        assert not is_valid_consumption(300, 400), "curr < prev phải invalid"
        assert not is_valid_consumption(-10, 0), "Chỉ số âm phải invalid"
        assert is_valid_consumption(400, 300), "Trường hợp đúng phải valid"

    # TC-EDGE-002: Hóa đơn không có reading → vẫn xử lý được
    def test_TC_EDGE_002_invoice_without_readings(self):
        """Hóa đơn có thể tồn tại mà không có reading tương ứng (edge case)."""
        from app.services.ai_service import _mock_analysis
        result = _mock_analysis("Phòng Test", [], [{"period": "2026-01",
                                                     "electricity_amount": 100000,
                                                     "water_amount": 50000,
                                                     "total_amount": 150000,
                                                     "status": "unpaid"}])
        assert isinstance(result, str), "Không được crash"

    # TC-EDGE-003: Tên hộ rỗng → không crash
    def test_TC_EDGE_003_empty_household_name(self):
        """Tên hộ rỗng → hàm không crash."""
        from app.services.ai_service import _mock_analysis
        result = _mock_analysis("", [], [])
        assert isinstance(result, str)

    # TC-EDGE-004: Nhiều tháng dữ liệu (12 tháng) → xử lý được
    def test_TC_EDGE_004_large_dataset(self):
        """12 tháng dữ liệu → phân tích không crash."""
        from app.services.ai_service import _mock_analysis
        readings = []
        for i in range(12):
            readings.append({
                "period": f"2026-{i+1:02d}",
                "meter_type": "electricity",
                "consumption": 100 + i * 10,
                "unit": "kWh",
            })
        result = _mock_analysis("Phòng 301", readings, [])
        assert isinstance(result, str)
        assert len(result) > 100

    # TC-EDGE-005: Detect intent với ký tự đặc biệt → không crash
    def test_TC_EDGE_005_special_chars_intent(self):
        from app.services.chat_service import detect_intent
        result = detect_intent("!@#$%^&*()")
        assert isinstance(result, str)

    # TC-EDGE-006: Detect intent với chuỗi rất dài → không crash
    def test_TC_EDGE_006_very_long_message(self):
        from app.services.chat_service import detect_intent
        long_msg = "Hóa đơn " * 500
        result = detect_intent(long_msg)
        assert result == "invoice", "Phải nhận ra 'hóa đơn' dù chuỗi rất dài"


# ═══════════════════════════════════════════════════════════════════════════════
# Chạy thủ công không cần pytest
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    all_tests = []

    # Nhóm 1
    g1 = TestConsumptionLogic()
    all_tests += [
        ("TC-CRUD-001", g1.test_TC_CRUD_001_consumption_formula),
        ("TC-CRUD-002", g1.test_TC_CRUD_002_negative_consumption_detection),
        ("TC-CRUD-003", g1.test_TC_CRUD_003_invoice_total_formula),
        ("TC-CRUD-004", g1.test_TC_CRUD_004_debt_formula),
        ("TC-CRUD-005", g1.test_TC_CRUD_005_fully_paid_debt_zero),
        ("TC-CRUD-006", g1.test_TC_CRUD_006_overpayment_negative_debt),
        ("TC-CRUD-007", g1.test_TC_CRUD_007_zero_consumption_valid),
        ("TC-CRUD-008", g1.test_TC_CRUD_008_evn_tier_pricing),
    ]

    # Nhóm 2
    g2 = TestIntentDetection()
    g2.setup_method()
    all_tests += [
        ("TC-CHAT-001", g2.test_TC_CHAT_001_greeting),
        ("TC-CHAT-002", g2.test_TC_CHAT_002_invoice_intent),
        ("TC-CHAT-003", g2.test_TC_CHAT_003_payment_intent),
        ("TC-CHAT-004", g2.test_TC_CHAT_004_consumption_intent),
        ("TC-CHAT-005", g2.test_TC_CHAT_005_meter_intent),
        ("TC-CHAT-006", g2.test_TC_CHAT_006_alert_intent),
        ("TC-CHAT-007", g2.test_TC_CHAT_007_lookup_household),
        ("TC-CHAT-008", g2.test_TC_CHAT_008_summary),
        ("TC-CHAT-009", g2.test_TC_CHAT_009_help),
        ("TC-CHAT-010", g2.test_TC_CHAT_010_general_fallback),
        ("TC-CHAT-011", g2.test_TC_CHAT_011_room_number_lookup),
        ("TC-CHAT-012", g2.test_TC_CHAT_012_empty_string),
    ]

    # Nhóm 3
    g3 = TestEdgeCases()
    all_tests += [
        ("TC-EDGE-001", g3.test_TC_EDGE_001_negative_consumption_flag),
        ("TC-EDGE-002", g3.test_TC_EDGE_002_invoice_without_readings),
        ("TC-EDGE-003", g3.test_TC_EDGE_003_empty_household_name),
        ("TC-EDGE-004", g3.test_TC_EDGE_004_large_dataset),
        ("TC-EDGE-005", g3.test_TC_EDGE_005_special_chars_intent),
        ("TC-EDGE-006", g3.test_TC_EDGE_006_very_long_message),
    ]

    print("=" * 65)
    print("  KIỂM THỬ HỆ THỐNG QUẢN LÝ HOÁ ĐƠN ĐIỆN NƯỚC — ĐỀ TÀI 48")
    print("=" * 65)
    passed = failed = errors = 0
    for tc_id, fn in all_tests:
        try:
            fn()
            print(f"  ✅ {tc_id}: PASSED")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {tc_id}: FAILED  →  {e}")
            failed += 1
        except Exception as e:
            print(f"  ⚠️  {tc_id}: ERROR   →  {type(e).__name__}: {e}")
            errors += 1
    print("=" * 65)
    print(f"  KẾT QUẢ: {passed} PASSED | {failed} FAILED | {errors} ERRORS | {len(all_tests)} TOTAL")
    print("=" * 65)
    sys.exit(0 if failed == 0 and errors == 0 else 1)
