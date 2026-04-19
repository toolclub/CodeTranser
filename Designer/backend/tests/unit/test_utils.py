from app.utils.hash import sha256_json, sha256_text
from app.utils.ids import new_id
from app.utils.sanitize import sanitize


def test_new_id_prefix_and_length() -> None:
    i = new_id("tpl", 8)
    assert i.startswith("tpl_")
    assert len(i) == len("tpl_") + 8


def test_sha256_json_stable_sorted_keys() -> None:
    a = {"a": 1, "b": 2}
    b = {"b": 2, "a": 1}
    assert sha256_json(a) == sha256_json(b)


def test_sha256_text_differs_for_different_input() -> None:
    assert sha256_text("a") != sha256_text("b")


def test_sanitize_masks_sensitive_keys() -> None:
    out = sanitize({"Authorization": "Bearer xyz", "ok": 1})
    assert out["Authorization"] == "***"
    assert out["ok"] == 1


def test_sanitize_recurses_and_handles_bytes() -> None:
    out = sanitize({"nested": {"token": "abc", "data": b"\x00\x01"}})
    assert out["nested"]["token"] == "***"
    assert set(out["nested"]["data"].keys()) == {"__bytes__", "sha256"}
