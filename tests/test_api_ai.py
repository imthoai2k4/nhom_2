"""
tests/test_api_ai.py — Test API /api/ai/analyze bằng TestClient.

Phạm vi:
  - Phân quyền admin/user/no-household.
  - Validate months (1–12).
  - Metadata: source, prompt_version, period_from/to, data_points theo kỳ.
  - Cache theo (household_id, months).
  - Fallback khi chưa cấu hình AI.

Chạy: python -m pytest tests/test_api_ai.py -v
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app import models
from main import app
from app.routers.ai_analysis import clear_ai_cache

FULL_ANALYSIS = (
    "📊 TỔNG QUAN: Tiêu thụ ổn định trong 2 kỳ gần nhất.\n"
    "📈 BIẾN ĐỘNG: Điện tăng nhẹ 4% so với kỳ trước.\n"
    "⚠️ CẢNH BÁO: Chưa phát hiện bất thường.\n"
    "💡 GỢI Ý TIẾT KIỆM: Tắt thiết bị khi không dùng.\n"
    "💰 CHI PHÍ: Hóa đơn tháng 7 khoảng 250.000đ."
)


@pytest.fixture()
def api_ctx():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    h1 = models.Household(id=1, name="Phòng 101", owner_name="Trần Thị Bình", status="active")
    h2 = models.Household(id=2, name="Phòng 202", owner_name="Hoàng Văn Em", status="active")
    db.add_all([h1, h2])
    db.flush()

    admin = models.User(id=99, username="admin", password="admin123",
                        full_name="Admin", role="admin", household_id=None)
    user1 = models.User(id=1, username="u1", password="p1",
                        full_name="User 1", role="user", household_id=1)
    user2 = models.User(id=2, username="u2", password="p2",
                        full_name="User 2", role="user", household_id=2)
    nohh = models.User(id=3, username="nohh", password="p3",
                       full_name="No HH", role="user", household_id=None)
    db.add_all([admin, user1, user2, nohh])
    db.flush()

    db.add_all([
        models.Meter(id=1, household_id=1, meter_type="electricity", meter_number="E101", unit="kWh"),
        models.Meter(id=2, household_id=1, meter_type="water", meter_number="W101", unit="m3"),
        models.Meter(id=3, household_id=2, meter_type="electricity", meter_number="E202", unit="kWh"),
    ])
    db.flush()

    db.add_all([
        models.Reading(meter_id=1, period="2026-06", prev_reading=30, curr_reading=100,
                       consumption=70, recorded_by=99),
        models.Reading(meter_id=1, period="2026-07", prev_reading=100, curr_reading=178,
                       consumption=78, recorded_by=99),
        models.Reading(meter_id=2, period="2026-06", prev_reading=5, curr_reading=20,
                       consumption=15, recorded_by=99),
        models.Reading(meter_id=2, period="2026-07", prev_reading=20, curr_reading=36,
                       consumption=16, recorded_by=99),
        models.Reading(meter_id=3, period="2026-07", prev_reading=1000, curr_reading=1200,
                       consumption=200, recorded_by=99),
    ])
    db.add_all([
        models.Invoice(household_id=1, period="2026-07", electricity_amount=150000,
                       water_amount=100000, total_amount=250000, status="partial"),
        models.Invoice(household_id=2, period="2026-07", electricity_amount=400000,
                       water_amount=0, total_amount=400000, status="unpaid"),
    ])
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    clear_ai_cache()
    client = TestClient(app)

    yield SimpleNamespace(client=client, db=db)

    app.dependency_overrides.clear()
    clear_ai_cache()
    db.close()


ADMIN = {"X-Username": "admin", "X-Password": "admin123"}
USER1 = {"X-Username": "u1", "X-Password": "p1"}
USER2 = {"X-Username": "u2", "X-Password": "p2"}
NOHH = {"X-Username": "nohh", "X-Password": "p3"}

FAKE_RESULT = SimpleNamespace(
    text=FULL_ANALYSIS,
    source="ai",
    model="qwen3.8-27b",
    finish_reason="stop",
    truncated=False,
    fallback_reason="",
    prompt_version="v3",
)


def _fake_analyze(*args, **kwargs):
    return FAKE_RESULT


def test_TC_API_AI_001_admin_200(api_ctx):
    with patch("app.routers.ai_analysis.analyze_consumption_detailed",
               new=AsyncMock(side_effect=_fake_analyze)):
        r = api_ctx.client.post("/api/ai/analyze", json={"household_id": 1, "months": 6}, headers=ADMIN)

    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "ai"
    assert data["prompt_version"] == "v3"
    assert data["data_points"] == 2  # 2 kỳ, không phải 4 readings
    assert data["period_from"] == "2026-06"
    assert data["period_to"] == "2026-07"
    assert data["cached"] is False


def test_TC_API_AI_002_user_own_200(api_ctx):
    with patch("app.routers.ai_analysis.analyze_consumption_detailed",
               new=AsyncMock(return_value=FAKE_RESULT)):
        r = api_ctx.client.post("/api/ai/analyze", json={"household_id": 1, "months": 6}, headers=USER1)
    assert r.status_code == 200


def test_TC_API_AI_003_user_other_403(api_ctx):
    r = api_ctx.client.post("/api/ai/analyze", json={"household_id": 1, "months": 6}, headers=USER2)
    assert r.status_code == 403


def test_TC_API_AI_004_household_not_found_404(api_ctx):
    r = api_ctx.client.post("/api/ai/analyze", json={"household_id": 999, "months": 6}, headers=ADMIN)
    assert r.status_code == 404


def test_TC_API_AI_005_no_household_user_403(api_ctx):
    r = api_ctx.client.post("/api/ai/analyze", json={"household_id": 1, "months": 6}, headers=NOHH)
    assert r.status_code == 403


@pytest.mark.parametrize("months", [0, -1, 13, 100000])
def test_TC_API_AI_006_invalid_months_422(api_ctx, months):
    r = api_ctx.client.post(
        "/api/ai/analyze",
        json={"household_id": 1, "months": months},
        headers=ADMIN,
    )
    assert r.status_code == 422


def test_TC_API_AI_007_cache_second_call(api_ctx):
    clear_ai_cache()
    mock = AsyncMock(return_value=FAKE_RESULT)
    with patch("app.routers.ai_analysis.analyze_consumption_detailed", new=mock):
        r1 = api_ctx.client.post("/api/ai/analyze", json={"household_id": 1, "months": 6}, headers=ADMIN)
        r2 = api_ctx.client.post("/api/ai/analyze", json={"household_id": 1, "months": 6}, headers=ADMIN)

    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["cached"] is False
    assert r2.json()["cached"] is True
    assert mock.await_count == 1


def test_TC_API_AI_008_no_key_fallback_internal(api_ctx):
    clear_ai_cache()
    with patch("app.services.ai_service.is_configured", return_value=False):
        r = api_ctx.client.post("/api/ai/analyze", json={"household_id": 1, "months": 6}, headers=ADMIN)

    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "internal"
    assert "Chưa cấu hình" in data["analysis"]


def test_TC_API_AI_009_security_headers(api_ctx):
    r = api_ctx.client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"


def test_TC_API_AI_010_cors_allowlist(api_ctx):
    allowed = api_ctx.client.get(
        "/api/health",
        headers={"Origin": "http://localhost:8000"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:8000"

    blocked = api_ctx.client.get(
        "/api/health",
        headers={"Origin": "http://evil.example"},
    )
    assert "access-control-allow-origin" not in blocked.headers
