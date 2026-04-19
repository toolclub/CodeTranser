from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middlewares.trace_id import HEADER, TraceIdMiddleware


def _app() -> TestClient:
    a = FastAPI()
    a.add_middleware(TraceIdMiddleware)

    @a.get("/echo")
    async def echo() -> dict[str, str]:
        from app.infra.tracing import current_trace_id

        return {"trace_id": current_trace_id() or ""}

    return TestClient(a)


def test_no_header_auto_generates() -> None:
    c = _app()
    r = c.get("/echo")
    assert r.status_code == 200
    assert len(r.headers[HEADER]) == 16
    assert r.json()["trace_id"] == r.headers[HEADER]


def test_header_is_propagated() -> None:
    c = _app()
    r = c.get("/echo", headers={HEADER: "provided-trace-123"})
    assert r.headers[HEADER] == "provided-trace-123"
    assert r.json()["trace_id"] == "provided-trace-123"
