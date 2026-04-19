from typing import Any

from app.tool_runtime.errors import SimulatorInputInvalid


def get_required(d: dict[str, Any], *keys: str) -> tuple[Any, ...]:
    missing = [k for k in keys if k not in d]
    if missing:
        raise SimulatorInputInvalid(f"missing fields: {missing}")
    return tuple(d[k] for k in keys)


def coerce_int(v: Any, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise SimulatorInputInvalid(f"{name} must be int")
    return v


def effective_mask(mask: int | None, width_bits: int) -> int:
    if mask is None:
        return (1 << width_bits) - 1
    return mask & ((1 << width_bits) - 1)
