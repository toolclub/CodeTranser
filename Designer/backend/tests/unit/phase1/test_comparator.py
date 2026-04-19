from app.langgraph.steps.phase1.comparator import deep_equal, diff_report


def test_deep_equal_basic_ok() -> None:
    assert deep_equal({"a": 1, "b": [1, 2]}, {"b": [1, 2], "a": 1})


def test_deep_equal_int_float_equiv() -> None:
    assert deep_equal(1, 1.0)


def test_deep_equal_bool_not_int() -> None:
    assert not deep_equal(True, 1)


def test_deep_equal_dict_key_set_differs() -> None:
    assert not deep_equal({"a": 1}, {"a": 1, "b": 2})


def test_diff_missing_key() -> None:
    d = diff_report({"a": 1, "b": 2}, {"a": 1})
    assert d == [{"path": "$.b", "kind": "missing_key", "expected": 2}]


def test_diff_value_mismatch() -> None:
    d = diff_report({"status": "ok"}, {"status": "success"})
    assert d[0]["kind"] == "value_mismatch"


def test_diff_length_and_inner_mismatch() -> None:
    d = diff_report([1, 2, 3], [1, 2])
    assert any(e["kind"] == "length_mismatch" for e in d)
