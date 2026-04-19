from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin_meta_template import router as admin_meta_router
from app.api.admin_tools import router as admin_tools_router
from app.api.graphs import router as graphs_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.node_templates import router as node_templates_router
from app.api.run_events import router as run_events_router
from app.bootstrap import build_container, shutdown, startup
from app.config import get_settings
from app.infra.logging import get_logger
from app.middlewares.auth import AuthMiddleware
from app.middlewares.error_handler import register_error_handlers
from app.middlewares.trace_id import TraceIdMiddleware

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    container = build_container(settings)
    app.state.container = container
    await startup(container)
    log.info("app_started", env=settings.APP_ENV)
    try:
        yield
    finally:
        await shutdown(container)
        log.info("app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

    # 中间件(注册顺序 = 请求从外到内)
    app.add_middleware(TraceIdMiddleware)
    if settings.AUTH_ENABLED:
        app.add_middleware(AuthMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    register_error_handlers(app)

    app.include_router(health_router)
    if settings.METRICS_ENABLED:
        app.include_router(metrics_router)

    # Ch03 节点模板路由
    app.include_router(admin_tools_router)
    app.include_router(node_templates_router)
    app.include_router(admin_meta_router)

    # Ch04 图路由
    app.include_router(graphs_router)

    # Run event log (resume / audit — ChatFlow 派生)
    app.include_router(run_events_router)

    return app


app = create_app()
