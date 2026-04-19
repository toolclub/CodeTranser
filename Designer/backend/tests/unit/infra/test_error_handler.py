from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.errors import Forbidden, NotFound, Unauthorized
from app.middlewares.error_handler import register_error_handlers


def _app() -> TestClient:
    a = FastAPI()
    register_error_handlers(a)

    @a.get("/401")
    async def _401() -> None:
        raise Unauthorized("no token")

    @a.get("/403")
    async def _403() -> None:
        raise Forbidden("nope")

    @a.get("/404")
    async def _404() -> None:
        raise NotFound("missing", target="x")

    @a.get("/500")
    async def _500() -> None:
        raise RuntimeError("boom")

    return TestClient(a, raise_server_exceptions=False)


def test_domain_error_mapping() -> None:
    c = _app()
    assert c.get("/401").status_code == 401
    assert c.get("/401").json()["error_code"] == "AUTH_UNAUTHORIZED"
    assert c.get("/403").status_code == 403
    assert c.get("/403").json()["error_code"] == "PERM_DENIED"

    r404 = c.get("/404")
    assert r404.status_code == 404
    body = r404.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["data"] == {"target": "x"}


def test_unhandled_is_500() -> None:
    c = _app()
    r = c.get("/500")
    assert r.status_code == 500
    assert r.json()["error_code"] == "INTERNAL_UNEXPECTED"
