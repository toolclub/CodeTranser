import base64
import json

import pytest
from starlette.requests import Request

from app.domain.errors import Forbidden, Unauthorized
from app.middlewares.auth import CurrentUser, require_admin, require_user
from app.middlewares.sso_adapter import verify_token


def _mk_request(user: CurrentUser | None) -> Request:
    # 直接构造 Scope 不方便;用一个简化 stub
    class _S:
        def __init__(self, u: CurrentUser | None) -> None:
            self.user = u

    class _R:
        def __init__(self, u: CurrentUser | None) -> None:
            self.state = _S(u)

    return _R(user)  # type: ignore[return-value]


def test_require_user_raises_when_missing() -> None:
    with pytest.raises(Unauthorized):
        require_user(_mk_request(None))


def test_require_admin_raises_when_not_admin() -> None:
    u = CurrentUser(
        id=1, external_id="u_x", username="x", display_name="X", email="", is_admin=False
    )
    with pytest.raises(Forbidden):
        require_admin(_mk_request(u))


def test_require_admin_passes_for_admin() -> None:
    u = CurrentUser(
        id=1, external_id="u_x", username="x", display_name="X", email="", is_admin=True
    )
    assert require_admin(_mk_request(u)) is u


@pytest.mark.asyncio
async def test_dev_bypass_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    claims = {"sub": "u_dev", "roles": ["admin"]}
    encoded = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    decoded = await verify_token(f"dev.{encoded}")
    assert decoded == claims


@pytest.mark.asyncio
async def test_malformed_dev_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    with pytest.raises(Unauthorized):
        await verify_token("dev.not-base64-!!!")
