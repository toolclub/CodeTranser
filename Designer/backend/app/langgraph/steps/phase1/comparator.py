"""字段级精确对比。不做语义等价(`{"status":"ok"}` ≠ `{"status":"success"}`)。"""

from typing import Any


def _numeric_and_not_bool(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def deep_equal(a: Any, b: Any) -> bool:
    if type(a) is not type(b):
        if _numeric_and_not_bool(a) and _numeric_and_not_bool(b):
            return a == b
        return False
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(deep_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(deep_equal(x, y) for x, y in zip(a, b))
    return a == b


def diff_report(expected: Any, actual: Any, path: str = "$") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if type(expected) is not type(actual):
        if not (_numeric_and_not_bool(expected) and _numeric_and_not_bool(actual)):
            out.append(
                {
                    "path": path,
                    "kind": "type_mismatch",
                    "expected": expected,
                    "actual": actual,
                }
            )
            return out
    if isinstance(expected, dict):
        ek, ak = set(expected.keys()), set(actual.keys())
        for k in sorted(ek - ak):
            out.append(
                {"path": f"{path}.{k}", "kind": "missing_key", "expected": expected[k]}
            )
        for k in sorted(ak - ek):
            out.append({"path": f"{path}.{k}", "kind": "extra_key", "actual": actual[k]})
        for k in sorted(ek & ak):
            out.extend(diff_report(expected[k], actual[k], f"{path}.{k}"))
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            out.append(
                {
                    "path": path,
                    "kind": "length_mismatch",
                    "expected_len": len(expected),
                    "actual_len": len(actual),
                }
            )
        for i, (e, a) in enumerate(zip(expected, actual)):
            out.extend(diff_report(e, a, f"{path}[{i}]"))
    else:
        if expected != actual:
            out.append(
                {
                    "path": path,
                    "kind": "value_mismatch",
                    "expected": expected,
                    "actual": actual,
                }
            )
    return out
