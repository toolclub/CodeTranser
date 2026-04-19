from fastapi import APIRouter, Request
from sqlalchemy import text

from app.config import get_settings
from app.schemas.common import ApiResponse

router = APIRouter(tags=["meta"])


@router.get("/healthz", response_model=ApiResponse[dict])
async def healthz() -> ApiResponse[dict]:
    s = get_settings()
    return ApiResponse[dict](data={"status": "ok", "app": s.APP_NAME, "env": s.APP_ENV})


@router.get("/readyz", response_model=ApiResponse[dict])
async def readyz(request: Request) -> ApiResponse[dict]:
    container = getattr(request.app.state, "container", None)
    checks: dict[str, str] = {"status": "ok"}

    if container is not None:
        # DB
        try:
            async with container.session_factory() as s:
                await s.execute(text("SELECT 1"))
            checks["mysql"] = "ok"
        except Exception as e:
            checks["mysql"] = f"error: {e.__class__.__name__}"

        # Mongo
        if container.mongo_db is not None:
            try:
                await container.mongo_db.command("ping")
                checks["mongo"] = "ok"
            except Exception as e:
                checks["mongo"] = f"error: {e.__class__.__name__}"

        # Redis
        if container.redis is not None:
            try:
                await container.redis.ping()
                checks["redis"] = "ok"
            except Exception as e:
                checks["redis"] = f"error: {e.__class__.__name__}"

    return ApiResponse[dict](data=checks)
