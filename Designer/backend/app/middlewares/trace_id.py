from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.infra.tracing import new_trace_id, trace_id_ctx

HEADER = "X-Trace-Id"


class TraceIdMiddleware(BaseHTTPMiddleware):
    """读取/生成 trace_id 并写入 contextvar,响应头回写。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tid = request.headers.get(HEADER) or new_trace_id()
        token = trace_id_ctx.set(tid)
        try:
            response = await call_next(request)
            response.headers[HEADER] = tid
            return response
        finally:
            trace_id_ctx.reset(token)
