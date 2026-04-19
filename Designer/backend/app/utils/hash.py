import hashlib
import json
from typing import Any


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def sha256_json(obj: Any) -> str:
    """对任意 JSON-able 对象做稳定 hash:键排序 + 紧凑分隔符。"""
    return sha256_text(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
