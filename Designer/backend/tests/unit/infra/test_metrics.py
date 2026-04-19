from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.metrics import router


def test_metrics_endpoint_returns_prom_format() -> None:
    a = FastAPI()
    a.include_router(router)
    c = TestClient(a)
    r = c.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
    assert "llm_calls_total" in r.text
