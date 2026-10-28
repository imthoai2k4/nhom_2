"""
app/services/prompt_loader.py — Nạp prompt từ thư mục prompts/ (có cache).

Cho phép đổi prompt không cần sửa code; nếu thiếu file thì dùng default truyền vào.
"""
from functools import lru_cache
from pathlib import Path

PROMPT_VERSION = "v3"
PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache(maxsize=16)
def load_prompt(filename: str, default: str = "") -> str:
    """Đọc file prompt UTF-8; trả default nếu không đọc được."""
    path = PROMPT_DIR / filename
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return default
