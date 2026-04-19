from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.deps import get_session
from app.middlewares.auth import require_admin, require_user
from app.schemas.common import ApiResponse
from app.schemas.tool import (
    NodeTemplateCreateDTO,
    NodeTemplateOutDTO,
    NodeTemplateSimulateReqDTO,
    NodeTemplateSimulateRespDTO,
    NodeTemplateUpdateDTO,
)
from app.services.tool_service import ToolService

router = APIRouter(prefix="/api/admin/node-templates", tags=["admin-node-templates"])


async def _svc(
    request: Request, session: AsyncSession = Depends(get_session)
) -> ToolService:
    return request.app.state.container.tool_service_factory(session)


@router.post("", response_model=ApiResponse[dict], status_code=201)
async def create_global(
    body: NodeTemplateCreateDTO,
    user: Any = Depends(require_admin),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[dict]:
    tid = await svc.create_global(body, user)
    return ApiResponse[dict](data={"template_id": tid})


@router.put("/{template_id}", response_model=ApiResponse[dict])
async def update_tpl(
    template_id: str,
    body: NodeTemplateUpdateDTO,
    user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[dict]:
    v = await svc.update(template_id, body, user)
    return ApiResponse[dict](data={"version_number": v})


@router.get("/{template_id}", response_model=ApiResponse[NodeTemplateOutDTO])
async def get_tpl(
    template_id: str,
    version: int | None = None,
    _user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[NodeTemplateOutDTO]:
    tpl = await svc.registry.get_by_id(template_id, version)
    return ApiResponse[NodeTemplateOutDTO](data=svc.to_out_dto(tpl))


@router.get("/{template_id}/versions", response_model=ApiResponse[list])
async def versions(
    template_id: str,
    _user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[list]:
    rs = await svc.repo.list_versions(template_id)
    return ApiResponse[list](
        data=[
            {
                "version_number": r.version_number,
                "change_note": r.change_note,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rs
        ]
    )


@router.post(
    "/{template_id}/versions/{ver}/activate",
    response_model=ApiResponse[dict],
)
async def activate(
    template_id: str,
    ver: int,
    _user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[dict]:
    await svc.repo.activate_version(template_id, ver)
    await svc.registry.invalidate(template_id)
    return ApiResponse[dict](data={"ok": True})


@router.post("/{template_id}/fork", response_model=ApiResponse[dict])
async def fork(
    template_id: str,
    user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[dict]:
    new_id = await svc.fork(template_id, user)
    return ApiResponse[dict](data={"template_id": new_id})


@router.post(
    "/{template_id}/simulate",
    response_model=ApiResponse[NodeTemplateSimulateRespDTO],
)
async def simulate(
    template_id: str,
    body: NodeTemplateSimulateReqDTO,
    user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[NodeTemplateSimulateRespDTO]:
    return ApiResponse[NodeTemplateSimulateRespDTO](
        data=await svc.simulate(template_id, body, user)
    )


@router.post("/registry/reload", response_model=ApiResponse[dict])
async def reload_registry(
    request: Request, _user: Any = Depends(require_admin)
) -> ApiResponse[dict]:
    await request.app.state.container.tool_registry.invalidate()
    return ApiResponse[dict](data={"ok": True})
