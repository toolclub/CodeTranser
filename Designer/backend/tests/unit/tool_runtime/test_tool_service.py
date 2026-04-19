from typing import Any

import pytest

from app.middlewares.auth import CurrentUser
from app.repositories.tool_repo import SqlToolRepo
from app.schemas.tool import (
    JsonSimulatorDTO,
    NodeTemplateCreateDTO,
    NodeTemplateDefinitionDTO,
    NodeTemplateSimulateReqDTO,
)
from app.services.tool_service import ToolService
from app.tool_runtime.factory import SimulatorFactory
from app.tool_runtime.loader import ToolLoader
from app.tool_runtime.registry import ToolRegistry


def _admin() -> CurrentUser:
    return CurrentUser(
        id=1, external_id="u_admin", username="a", display_name="A",
        email="", is_admin=True,
    )


def _user() -> CurrentUser:
    return CurrentUser(
        id=2, external_id="u_designer", username="d", display_name="D",
        email="", is_admin=False,
    )


def _dto(engine: str = "pure_python", name: str = "IndexTableLookup") -> NodeTemplateCreateDTO:
    return NodeTemplateCreateDTO(
        name=name,
        display_name="IT",
        category="util",
        scope="global",
        definition=NodeTemplateDefinitionDTO(
            description=["demo"],
            input_schema={
                "type": "object",
                "required": ["EntrySize", "MaxEntryNum"],
                "properties": {
                    "EntrySize": {"type": "integer"},
                    "MaxEntryNum": {"type": "integer"},
                    "Mask": {"type": ["integer", "null"]},
                },
            },
            output_schema={"type": "object"},
            simulator=JsonSimulatorDTO(
                engine=engine,  # type: ignore[arg-type]
                python_impl="IndexTableLookup" if engine != "llm" else None,
            ),
        ),
    )


class _Settings:
    TOOL_DESCRIPTION_MAX_LENGTH = 15000
    TOOL_INJECTION_BLOCKLIST: list[str] = []


def _svc(db: Any) -> ToolService:
    repo = SqlToolRepo(db)
    loader = ToolLoader(lambda: db)  # type: ignore[arg-type]
    # Loader 需要 session_factory,但 simulate 不走 loader,这里仅占位
    registry = ToolRegistry(loader, SimulatorFactory(), redis=None)
    return ToolService(repo=repo, registry=registry, llm_client=None, settings=_Settings())


@pytest.mark.asyncio
async def test_create_private_must_be_llm(db) -> None:
    svc = _svc(db)
    dto = _dto(engine="pure_python")
    dto_private = dto.model_copy(update={"scope": "private"})
    from app.tool_runtime.errors import TemplateDefinitionInvalid

    with pytest.raises(TemplateDefinitionInvalid):
        await svc.create_private(dto_private, _user())


@pytest.mark.asyncio
async def test_create_global_requires_admin(db) -> None:
    from app.domain.errors import Forbidden

    svc = _svc(db)
    with pytest.raises(Forbidden):
        await svc.create_global(_dto(), _user())


@pytest.mark.asyncio
async def test_create_global_by_admin_succeeds(db) -> None:
    svc = _svc(db)
    tid = await svc.create_global(_dto(), _admin())
    assert tid.startswith("tpl_")
