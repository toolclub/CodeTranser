from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.domain.errors import DomainError
from app.infra.logging import get_logger
from app.infra.tracing import current_trace_id

log = get_logger(__name__)


def _err_response(
    error_code: str, message: str, http_status: int, data: Any = None
) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={
            "code": 1,
            "error_code": error_code,
            "message": message,
            "data": data,
            "trace_id": current_trace_id(),
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(_req: Request, exc: DomainError) -> JSONResponse:
        return _err_response(exc.code, exc.message, exc.http_status, data=exc.extra or None)

    @app.exception_handler(PydanticValidationError)
    async def _pydantic_handler(_req: Request, exc: PydanticValidationError) -> JSONResponse:
        return _err_response("VALIDATION_FAILED", "validation error", 422, data=exc.errors())

    @app.exception_handler(Exception)
    async def _any_handler(_req: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", exc_info=exc)
        return _err_response("INTERNAL_UNEXPECTED", "internal error", 500)
