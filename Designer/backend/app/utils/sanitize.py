import hashlib
from typing import Any

SENSITIVE_KEYS: set[str] = {
    "authorization",
    "cookie",
    "password",
    "token",
    "api_key",
    "secret",
}

MAX_STRING_BYTES = 64 * 1024


def sanitize(value: Any) -> Any:
    """递归脱敏 + 截断超长字符串 + bytes 折叠。"""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in SENSITIVE_KEYS:
                out[k] = "***"
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [sanitize(v) for v in value]
    if isinstance(value, bytes):
        return {"__bytes__": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    if isinstance(value, str) and len(value.encode("utf-8")) > MAX_STRING_BYTES:
        truncated = value.encode("utf-8")[:MAX_STRING_BYTES].decode("utf-8", errors="ignore")
        return truncated + "...[truncated]"
    return value
