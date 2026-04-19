from dataclasses import dataclass
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.domain.errors import Forbidden, Unauthorized
from app.infra.db.session import session_scope
from app.middlewares.sso_adapter import verify_token
from app.repositories.user_repo import SqlUserRepo


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: int
    external_id: str
    username: str
    display_name: str
    email: str
    is_admin: bool
    roles: tuple[str, ...] = ()


PUBLIC_PATHS: set[str] = {
    "/healthz",
    "/readyz",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
}
PUBLIC_PREFIXES: tuple[str, ...] = ("/public/",)


class AuthMiddleware(BaseHTTPMiddleware):
    """SSO token 校验 + 当前用户注入。

    - 仅当 `Settings.AUTH_ENABLED` 为 True 时介入;否则直通。
    - PUBLIC_PATHS / PUBLIC_PREFIXES 永远放过。
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        token = _extract_bearer(request)
        if not token:
            raise Unauthorized("missing token")

        claims = await verify_token(token)
        user = await _load_user(request.app.state.container, claims)
        request.state.user = user
        return await call_next(request)


def _extract_bearer(request: Request) -> str | None:
    h = request.headers.get("authorization", "")
    return h[7:] if h.lower().startswith("bearer ") else None


async def _load_user(container: Any, claims: dict[str, Any]) -> CurrentUser:
    settings = get_settings()
    external_id = claims["sub"]
    is_admin_claim = "admin" in claims.get("roles", [])
    is_admin_cfg = external_id in settings.ADMIN_EXTERNAL_IDS
    async with session_scope(container.session_factory) as s:
        profile = {
            "external_id": external_id,
            "username": claims.get("preferred_username", external_id),
            "display_name": claims.get("name", external_id),
            "email": claims.get("email", ""),
            "is_admin": is_admin_claim or is_admin_cfg,
        }
        u = await SqlUserRepo(s).upsert_from_sso(profile)
    return CurrentUser(
        id=u["id"],
        external_id=u["external_id"],
        username=u["username"],
        display_name=u["display_name"],
        email=u["email"],
        is_admin=u["is_admin"],
        roles=tuple(claims.get("roles", [])),
    )


# AUTH_ENABLED=false(本地 dev / 自测)时的兜底用户:所有接口直接放行并视为 admin。
# 生产 K8S 必须 AUTH_ENABLED=true,走 SSO。
_DEV_USER = CurrentUser(
    id=1,
    external_id="u_dev",
    username="dev",
    display_name="Dev",
    email="dev@local",
    is_admin=True,
    roles=("admin",),
)


def require_user(request: Request) -> CurrentUser:
    u = getattr(request.state, "user", None)
    if u is not None:
        return u
    if not get_settings().AUTH_ENABLED:
        return _DEV_USER
    raise Unauthorized("missing user")


def require_admin(request: Request) -> CurrentUser:
    u = require_user(request)
    if not u.is_admin:
        raise Forbidden("admin required")
    return u
