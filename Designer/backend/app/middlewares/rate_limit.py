from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.domain.errors import TooManyRequests


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 Redis 的滑动窗口限流。按 (user_id, action) 分桶。

    rules:  {"/api/runs:POST": (max_count, window_seconds), ...}
    """

    def __init__(
        self,
        app: ASGIApp,
        redis: Any,
        rules: dict[str, tuple[int, int]],
    ) -> None:
        super().__init__(app)
        self._redis = redis
        self._rules = rules

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        user = getattr(request.state, "user", None)
        if user is not None and self._redis is not None:
            key = f"{request.url.path}:{request.method}"
            rule = self._rules.get(key)
            if rule:
                max_n, win = rule
                bucket = f"rl:{user.id}:{key}"
                c = await self._redis.incr(bucket)
                if c == 1:
                    await self._redis.expire(bucket, win)
                if c > max_n:
                    raise TooManyRequests(f"rate limit {key}")
        return await call_next(request)
