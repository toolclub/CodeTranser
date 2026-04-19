from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.deps import get_session
from app.middlewares.auth import require_user
from app.schemas.common import ApiResponse
from app.schemas.graph import ForestSnapshotDTO, GraphCreateDTO, GraphVersionSaveDTO
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api/graphs", tags=["graphs"])


async def _svc(
    request: Request, session: AsyncSession = Depends(get_session)
) -> GraphService:
    return request.app.state.container.graph_service_factory(session)


@router.post("", response_model=ApiResponse[dict], status_code=201)
async def create_graph(
    body: GraphCreateDTO,
    user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict]:
    return ApiResponse[dict](data={"graph_id": await svc.create(body, user)})


@router.get("", response_model=ApiResponse[list])
async def list_mine(
    user: Any = Depends(require_user), svc: GraphService = Depends(_svc)
) -> ApiResponse[list]:
    rows = await svc.graph_repo.list_mine(user.id)
    return ApiResponse[list](
        data=[
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "status": r.status,
                "latest_version_id": r.latest_version_id,
            }
            for r in rows
        ]
    )


@router.get("/{graph_id}", response_model=ApiResponse[dict])
async def detail(
    graph_id: str,
    _user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict]:
    g = await svc.graph_repo.get(graph_id)
    return ApiResponse[dict](
        data={
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "status": g.status,
            "latest_version_id": g.latest_version_id,
        }
    )


@router.put("/{graph_id}", response_model=ApiResponse[dict])
async def update_meta(
    graph_id: str,
    body: dict[str, Any],
    _user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict]:
    await svc.graph_repo.update_meta(graph_id, body.get("name"), body.get("description"))
    return ApiResponse[dict](data={"ok": True})


@router.delete("/{graph_id}", status_code=204)
async def delete_graph(
    graph_id: str,
    _user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> None:
    await svc.graph_repo.soft_delete(graph_id)


@router.get("/{graph_id}/versions", response_model=ApiResponse[list])
async def versions(
    graph_id: str,
    _user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[list]:
    return ApiResponse[list](data=await svc.list_versions(graph_id))


@router.post("/{graph_id}/versions", response_model=ApiResponse[dict], status_code=201)
async def save_version(
    graph_id: str,
    body: GraphVersionSaveDTO,
    user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict]:
    return ApiResponse[dict](
        data={"version_id": await svc.save_version(graph_id, body, user)}
    )


@router.get(
    "/{graph_id}/versions/{version_number}", response_model=ApiResponse[dict]
)
async def get_version(
    graph_id: str,
    version_number: int,
    _user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict]:
    return ApiResponse[dict](data=await svc.get_version(graph_id, version_number))


@router.get("/{graph_id}/versions/_diff", response_model=ApiResponse[dict])
async def diff_versions(
    graph_id: str,
    v1: int,
    v2: int,
    _user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict]:
    d = await svc.diff_versions(graph_id, v1, v2)
    return ApiResponse[dict](data=svc.diff_to_dict(d))


@router.get("/{graph_id}/draft", response_model=ApiResponse[dict | None])
async def get_draft(
    graph_id: str,
    _user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict | None]:
    return ApiResponse[dict | None](data=await svc.get_draft(graph_id))


@router.put("/{graph_id}/draft", response_model=ApiResponse[dict])
async def save_draft(
    graph_id: str,
    body: ForestSnapshotDTO,
    user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict]:
    await svc.save_draft(graph_id, body, user)
    return ApiResponse[dict](data={"ok": True})


@router.post("/_validate", response_model=ApiResponse[dict])
async def validate_snapshot(
    body: ForestSnapshotDTO,
    _user: Any = Depends(require_user),
    svc: GraphService = Depends(_svc),
) -> ApiResponse[dict]:
    report = await svc.validate_snapshot(body)
    return ApiResponse[dict](
        data={
            "ok": report.ok,
            "errors": report.errors,
            "warnings": report.warnings,
        }
    )
