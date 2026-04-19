from app.infra.tracing import current_trace_id, new_trace_id, trace_id_ctx


def test_new_trace_id_is_hex_16() -> None:
    tid = new_trace_id()
    assert len(tid) == 16
    int(tid, 16)  # 纯十六进制


def test_current_trace_id_via_ctx() -> None:
    assert current_trace_id() is None
    token = trace_id_ctx.set("abc123")
    try:
        assert current_trace_id() == "abc123"
    finally:
        trace_id_ctx.reset(token)
    assert current_trace_id() is None
