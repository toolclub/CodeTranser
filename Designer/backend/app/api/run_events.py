"""Run events / stop 控制(分布式)。

- `GET /events`:从 DB 按自增 id 读,任何 pod 都能响应(DB 是 source of truth)
- `POST /stop`:任意 pod 接到请求 → 写 Redis `cascade:run:stop:{id}`;
  实际执行 Run 的 pod 在下次 heartbeat 监控周期(最多 20s)内看到 flag 并取消 pipeline
- `GET /owner`:运维查哪个 worker_id 在跑(来自 SessionRegistry)
"""

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.middlewares.auth import require_user
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/runs", tags=["run-events"])


@router.get("/{run_id}/events", response_model=ApiResponse[list])
async def list_events(
    run_id: str,
    request: Request,
    after_id: int = 0,
    message_id: str | None = None,
    limit: int = 2000,
    _user: Any = Depends(require_user),
) -> ApiResponse[list]:
    container = request.app.state.container
    store = container.event_log_store
    if store is None:
        return ApiResponse[list](data=[])
    rows = await store.list_since(run_id, after_id, message_id=message_id or None, limit=limit)
    return ApiResponse[list](data=list(rows))


@router.post("/{run_id}/stop", response_model=ApiResponse[dict])
async def stop_run(
    run_id: str,
    request: Request,
    _user: Any = Depends(require_user),
) -> ApiResponse[dict]:
    container = request.app.state.container
    reg = container.stop_registry
    if reg is None:
        return ApiResponse[dict](code=1, message="stop registry unavailable", data=None)
    ok = await reg.request_stop(run_id)
    return ApiResponse[dict](data={"requested": ok, "run_id": run_id})


@router.get("/{run_id}/owner", response_model=ApiResponse[dict])
async def who_owns(
    run_id: str,
    request: Request,
    _user: Any = Depends(require_user),
) -> ApiResponse[dict]:
    container = request.app.state.container
    reg = container.session_registry
    owner = await reg.who_owns(run_id) if reg else None
    return ApiResponse[dict](data={"run_id": run_id, "worker_id": owner})
