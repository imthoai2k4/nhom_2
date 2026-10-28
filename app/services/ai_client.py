"""
app/services/ai_client.py — Client gọi API chuẩn OpenAI (Qwen3.8-27B)

Cấu hình qua biến môi trường:
  AI_API_KEY    — API key (bắt buộc để gọi model)
  AI_BASE_URL   — mặc định https://discovery-api.intern-ai.org.cn/v1
  AI_MODEL      — mặc định qwen3.8-27b
  AI_TIMEOUT    — timeout mỗi request (giây), mặc định 30
  AI_MAX_TOKENS — số token tối đa cho câu trả lời, mặc định 4096

Thiết kế:
  - Dùng đúng giao thức OpenAI: POST {base_url}/chat/completions với Bearer token.
  - Import `openai` theo kiểu lazy để ứng dụng vẫn khởi động được khi chưa cài SDK.
  - Lỗi được chuẩn hóa thành AIError(kind=...) để tầng service quyết định fallback.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://discovery-api.intern-ai.org.cn/v1"
DEFAULT_MODEL = "qwen3.8-27b"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_TOKENS = 4096


@dataclass(frozen=True)
class AIConfig:
    """Cấu hình bất biến cho một lần gọi AI."""

    api_key: str
    base_url: str
    model: str
    timeout: float
    max_tokens: int


@dataclass
class ChatResult:
    """Kết quả chuẩn hóa từ API chat completions."""

    text: str
    finish_reason: str = ""
    model: str = ""
    usage: Optional[dict] = None


class AIError(Exception):
    """Lỗi AI đã được phân loại để tầng service chọn thông báo/fallback."""

    def __init__(self, kind: str, detail: str = ""):
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}" if detail else kind)


def _read_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _read_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def get_config() -> AIConfig:
    """Đọc cấu hình tại thời điểm gọi (hỗ trợ đổi .env rồi restart server)."""
    api_key = (os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = (os.getenv("AI_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
    model = (os.getenv("AI_MODEL") or DEFAULT_MODEL).strip()
    return AIConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=_read_float("AI_TIMEOUT", DEFAULT_TIMEOUT),
        max_tokens=_read_int("AI_MAX_TOKENS", DEFAULT_MAX_TOKENS),
    )


def is_configured() -> bool:
    """True nếu đã có API key để gọi model."""
    return bool(get_config().api_key)


def _classify_error(exc: Exception) -> str:
    """Phân loại lỗi SDK/HTTP thành kind ổn định cho tầng service."""
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    msg = str(exc).lower()

    if status == 429 or "ratelimit" in name or "rate limit" in msg or "quota" in msg:
        return "rate_limit"
    if status in (401, 403) or "authentication" in name or "permission" in name:
        return "auth"
    if "invalid api key" in msg or "incorrect api key" in msg:
        return "auth"
    if "timeout" in name or "timeout" in msg or "timed out" in msg or "deadline" in msg:
        return "timeout"
    if "connection" in name or "connect" in msg:
        return "unavailable"
    if isinstance(status, int) and status >= 500:
        return "unavailable"
    if status == 400 or "badrequest" in name:
        return "bad_request"
    return "unknown"


def _build_messages(system_prompt: str, user_prompt: str) -> list[dict]:
    """Tách system/user prompt đúng chuẩn chat completions."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _to_result(response) -> ChatResult:
    """Chuẩn hóa response của SDK thành ChatResult."""
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise AIError("empty", "API không trả về choices")

    choice = choices[0]
    message = getattr(choice, "message", None)
    text = (getattr(message, "content", "") or "").strip()

    usage = getattr(response, "usage", None)
    usage_dict = None
    if usage is not None:
        if hasattr(usage, "model_dump"):
            usage_dict = usage.model_dump()
        elif isinstance(usage, dict):
            usage_dict = usage

    return ChatResult(
        text=text,
        finish_reason=getattr(choice, "finish_reason", "") or "",
        model=getattr(response, "model", "") or "",
        usage=usage_dict,
    )


async def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> ChatResult:
    """
    Gọi API chat completions bất đồng bộ.

    Raises:
        AIError: kind ∈ no_key | missing_sdk | timeout | rate_limit | auth |
                 unavailable | bad_request | empty | unknown
    """
    cfg = get_config()
    if not cfg.api_key:
        raise AIError("no_key", "AI_API_KEY chưa được cấu hình")

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise AIError(
            "missing_sdk",
            "Chưa cài thư viện openai. Chạy: pip install -r requirements.txt",
        ) from exc

    client = AsyncOpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=cfg.timeout,
        max_retries=0,
    )
    try:
        response = await client.chat.completions.create(
            model=cfg.model,
            messages=_build_messages(system_prompt, user_prompt),
            temperature=temperature,
            max_tokens=max_tokens or cfg.max_tokens,
        )
    except Exception as exc:  # SDK ném nhiều lớp lỗi khác nhau
        raise AIError(_classify_error(exc), str(exc)[:300]) from exc
    finally:
        await client.close()

    return _to_result(response)


def chat_completion_sync(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.5,
    max_tokens: Optional[int] = None,
) -> Optional[ChatResult]:
    """
    Phiên bản đồng bộ dùng cho chat service.
    Trả None khi chưa cấu hình, lỗi hoặc response rỗng — nơi gọi tự fallback rule-based.
    """
    cfg = get_config()
    if not cfg.api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=cfg.timeout,
        max_retries=0,
    )
    try:
        response = client.chat.completions.create(
            model=cfg.model,
            messages=_build_messages(system_prompt, user_prompt),
            temperature=temperature,
            max_tokens=max_tokens or cfg.max_tokens,
        )
        result = _to_result(response)
        return result if (result.text or "").strip() else None
    except Exception:
        return None
    finally:
        client.close()
