"""
tools/prompt_experiments.py — Tái lập 3 vòng tối ưu prompt (V1/V2/V3).

Mặc định chỉ in prompt (dry-run). Thêm --live để gọi model thật và xuất CSV.

Ví dụ:
  python tools/prompt_experiments.py
  python tools/prompt_experiments.py --live
  python tools/prompt_experiments.py --live --out docs/prompt-experiments.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.ai_client import chat_completion, is_configured
from app.services.ai_service import SYSTEM_PROMPT, _build_user_prompt

READINGS = [
    {"period": "2026-01", "meter_type": "electricity", "consumption": 150.0, "unit": "kWh"},
    {"period": "2026-02", "meter_type": "electricity", "consumption": 280.0, "unit": "kWh"},
    {"period": "2026-03", "meter_type": "electricity", "consumption": 160.0, "unit": "kWh"},
    {"period": "2026-01", "meter_type": "water", "consumption": 5.0, "unit": "m3"},
    {"period": "2026-02", "meter_type": "water", "consumption": 5.2, "unit": "m3"},
    {"period": "2026-03", "meter_type": "water", "consumption": 4.8, "unit": "m3"},
]
INVOICES = [
    {"period": "2026-01", "electricity_amount": 271000, "water_amount": 80000, "total_amount": 351000, "status": "paid"},
    {"period": "2026-02", "electricity_amount": 520000, "water_amount": 83000, "total_amount": 603000, "status": "unpaid"},
    {"period": "2026-03", "electricity_amount": 289000, "water_amount": 77000, "total_amount": 366000, "status": "paid"},
]

V1_SYSTEM = "Bạn là trợ lý phân tích hóa đơn điện nước."
V1_USER = """Phân tích tiêu thụ điện nước của hộ gia đình sau:
- Tháng 1: 150 kWh điện, 5 m³ nước
- Tháng 2: 280 kWh điện, 5.2 m³ nước
- Tháng 3: 160 kWh điện, 4.8 m³ nước
"""

V2_SYSTEM = """Bạn là trợ lý phân tích hóa đơn điện nước.
Quy tắc BẮT BUỘC:
1. Chỉ sử dụng dữ liệu được cung cấp. KHÔNG tự tạo số liệu.
2. Trả lời tiếng Việt, ngắn gọn.
3. Cấu trúc: TỔNG QUAN → BIẾN ĐỘNG → CẢNH BÁO → GỢI Ý → CHI PHÍ
"""
V2_USER = """Hộ/phòng: Phòng 101 — Nguyễn Văn A

📋 Lịch sử tiêu thụ:
  - Kỳ 2026-01: ⚡ Điện = 150 kWh
  - Kỳ 2026-02: ⚡ Điện = 280 kWh
  - Kỳ 2026-03: ⚡ Điện = 160 kWh

Hãy phân tích biến động, chỉ ra tháng cần kiểm tra và gợi ý tiết kiệm.
"""

VERSIONS = [
    ("V1", V1_SYSTEM, V1_USER, 3, "Prompt thô, không ràng buộc, dễ bịa nguyên nhân"),
    ("V2", V2_SYSTEM, V2_USER, 7, "Tách system/user, cấu trúc 5 phần, không bịa số"),
    ("V3", SYSTEM_PROMPT, _build_user_prompt("Phòng 101", READINGS, INVOICES), 9,
     "Thêm hóa đơn, ngưỡng 50%, gắn gợi ý với dữ liệu"),
]


async def run_live() -> list[dict]:
    if not is_configured():
        print("Chưa cấu hình AI_API_KEY — không chạy live.")
        return []

    rows = []
    for version, system, user, score, note in VERSIONS:
        started = time.perf_counter()
        try:
            result = await chat_completion(system, user, temperature=0.4, max_tokens=4096)
            elapsed = int((time.perf_counter() - started) * 1000)
            rows.append({
                "version": version,
                "model": result.model or "qwen3.8-27b",
                "chars": len(result.text or ""),
                "elapsed_ms": elapsed,
                "finish_reason": result.finish_reason,
                "score": score,
                "note": note,
            })
            print(f"\n===== {version} | {elapsed}ms | {result.finish_reason} =====")
            print(result.text[:1200])
        except Exception as exc:
            rows.append({
                "version": version,
                "model": "qwen3.8-27b",
                "chars": 0,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
                "finish_reason": "error",
                "score": score,
                "note": f"{note} | lỗi: {type(exc).__name__}",
            })
            print(f"{version}: lỗi {type(exc).__name__}: {exc}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Gọi model thật")
    parser.add_argument("--out", help="Ghi CSV ra file")
    args = parser.parse_args()

    if not args.live:
        for version, system, user, score, note in VERSIONS:
            print(f"\n===== {version} (score {score}) =====")
            print("[system]", system)
            print("[user]", user)
        return 0

    rows = asyncio.run(run_live())
    if not rows:
        return 1

    fieldnames = ["version", "model", "chars", "elapsed_ms", "finish_reason", "score", "note"]
    import io
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    print("\n--- CSV ---")
    print(buffer.getvalue())

    if args.out:
        Path(args.out).write_text(buffer.getvalue(), encoding="utf-8")
        print(f"Đã ghi: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
