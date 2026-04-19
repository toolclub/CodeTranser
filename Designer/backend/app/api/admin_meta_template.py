from typing import Any

from fastapi import APIRouter, Depends, Request

from app.middlewares.auth import require_admin, require_user
from app.schemas.common import ApiResponse
from app.schemas.meta_template import MetaTemplateDTO, MetaTemplateUpdateDTO
from app.services.meta_template_service import MetaTemplateService

router = APIRouter(prefix="/api/admin/meta-node-template", tags=["admin-meta-template"])


def _svc(request: Request) -> MetaTemplateService:
    return request.app.state.container.meta_template_service


@router.get("", response_model=ApiResponse[MetaTemplateDTO])
async def get_meta(
    request: Request, _user: Any = Depends(require_user)
) -> ApiResponse[MetaTemplateDTO]:
    return ApiResponse[MetaTemplateDTO](data=await _svc(request).get())


@router.put("", response_model=ApiResponse[dict])
async def update_meta(
    request: Request,
    body: MetaTemplateUpdateDTO,
    user: Any = Depends(require_admin),
) -> ApiResponse[dict]:
    await _svc(request).update(body, user.id)
    return ApiResponse[dict](data={"ok": True})
