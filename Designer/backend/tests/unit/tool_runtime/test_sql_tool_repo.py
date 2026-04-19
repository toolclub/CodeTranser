import pytest

from app.repositories.tool_repo import SqlToolRepo
from app.schemas.tool import (
    JsonSimulatorDTO,
    NodeTemplateCreateDTO,
    NodeTemplateDefinitionDTO,
)


def _create_dto(name: str = "IndexTableLookup", scope: str = "global") -> NodeTemplateCreateDTO:
    return NodeTemplateCreateDTO(
        name=name,
        display_name="IT",
        category="util",
        scope=scope,  # type: ignore[arg-type]
        definition=NodeTemplateDefinitionDTO(
            description=["demo"],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            simulator=JsonSimulatorDTO(
                engine="pure_python", python_impl="IndexTableLookup"
            ),
        ),
    )


@pytest.mark.asyncio
async def test_create_then_get_then_update(db) -> None:
    repo = SqlToolRepo(db)
    tid, ver = await repo.create(_create_dto(), user_id=1)
    assert ver == 1
    row = await repo.get(tid)
    assert row.name == "IndexTableLookup"
    new_ver = await repo.update_create_version(
        tid,
        _create_dto().definition,
        change_note="bump",
        user_id=1,
    )
    assert new_ver == 2
    versions = await repo.list_versions(tid)
    assert [v.version_number for v in versions] == [2, 1]


@pytest.mark.asyncio
async def test_duplicate_name_in_same_scope_raises(db) -> None:
    repo = SqlToolRepo(db)
    await repo.create(_create_dto(), user_id=1)
    from app.tool_runtime.errors import TemplateDefinitionInvalid

    with pytest.raises(TemplateDefinitionInvalid):
        await repo.create(_create_dto(), user_id=1)


@pytest.mark.asyncio
async def test_fork_to_private_forces_llm(db) -> None:
    repo = SqlToolRepo(db)
    tid, _ = await repo.create(_create_dto(), user_id=1)
    new_tid = await repo.fork_to_private(tid, owner_id=2, user_id=2)
    row = await repo.get(new_tid)
    assert row.scope == "private"
    assert row.owner_id == 2
    v = await repo.get_version(new_tid, 1)
    assert v.definition["simulator"]["engine"] == "llm"
