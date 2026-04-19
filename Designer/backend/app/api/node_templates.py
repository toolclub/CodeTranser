from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.deps import get_session
from app.middlewares.auth import require_user
from app.schemas.common import ApiResponse
from app.schemas.tool import NodeTemplateCardDTO, NodeTemplateCreateDTO
from app.services.tool_service import ToolService

router = APIRouter(prefix="/api/node-templates", tags=["node-templates"])


async def _svc(
    request: Request, session: AsyncSession = Depends(get_session)
) -> ToolService:
    return request.app.state.container.tool_service_factory(session)


@router.get("", response_model=ApiResponse[list[NodeTemplateCardDTO]])
async def list_cards(
    category: str | None = None,
    scope: Literal["global", "private", "all"] = "all",
    user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[list[NodeTemplateCardDTO]]:
    rows = await svc.list_visible(scope=scope, category=category, user=user)
    cards: list[NodeTemplateCardDTO] = []
    for row in rows:
        tpl = await svc.registry.get_by_id(row.id)
        cards.append(svc.to_card_dto(tpl))
    return ApiResponse[list[NodeTemplateCardDTO]](data=cards)


@router.get("/{template_id}", response_model=ApiResponse[NodeTemplateCardDTO])
async def get_card(
    template_id: str,
    _user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[NodeTemplateCardDTO]:
    tpl = await svc.registry.get_by_id(template_id)
    return ApiResponse[NodeTemplateCardDTO](data=svc.to_card_dto(tpl))


@router.post("", response_model=ApiResponse[dict], status_code=201)
async def create_private(
    body: NodeTemplateCreateDTO,
    user: Any = Depends(require_user),
    svc: ToolService = Depends(_svc),
) -> ApiResponse[dict]:
    """设计人员建私有节点模板。scope 强制 private,engine 强制 llm(Service 层校验)。"""
    tid = await svc.create_private(body, user)
    return ApiResponse[dict](data={"template_id": tid})
