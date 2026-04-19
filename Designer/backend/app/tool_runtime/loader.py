from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.tool.tool import (
    CodeGenerationHints,
    EdgeSemantic,
    Engine,
    JsonSimulatorSpec,
    NodeTemplate,
    Scope,
)
from app.models.mysql.node_template import NodeTemplateRow
from app.models.mysql.node_template_version import NodeTemplateVersionRow
from app.tool_runtime.errors import NodeTemplateNotFound


class ToolLoader:
    """把 DB 行装配成 `NodeTemplate` 值对象,独立于 Repo(可跨 session 缓存)。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def load_by_id(self, template_id: str, version: int | None = None) -> NodeTemplate:
        async with self._sf() as s:
            row = (
                await s.execute(
                    select(NodeTemplateRow).where(NodeTemplateRow.id == template_id)
                )
            ).scalar_one_or_none()
            if row is None:
                raise NodeTemplateNotFound(template_id)

            q = select(NodeTemplateVersionRow).where(
                NodeTemplateVersionRow.template_id == template_id
            )
            if version is not None:
                q = q.where(NodeTemplateVersionRow.version_number == version)
            else:
                q = q.where(NodeTemplateVersionRow.id == row.current_version_id)
            v = (await s.execute(q)).scalar_one_or_none()
            if v is None:
                raise NodeTemplateNotFound(f"{template_id} v{version}")
            return _row_to_tpl(row, v)

    async def load(
        self,
        *,
        name: str,
        owner_id: int | None,
        scope: Scope,
        version: int | None = None,
    ) -> NodeTemplate:
        async with self._sf() as s:
            q = select(NodeTemplateRow).where(
                NodeTemplateRow.name == name,
                NodeTemplateRow.scope == scope.value,
            )
            if scope is Scope.PRIVATE and owner_id is not None:
                q = q.where(NodeTemplateRow.owner_id == owner_id)
            row = (await s.execute(q)).scalar_one_or_none()
            if row is None:
                raise NodeTemplateNotFound(name)
        return await self.load_by_id(row.id, version)


def _row_to_tpl(row: NodeTemplateRow, ver: NodeTemplateVersionRow) -> NodeTemplate:
    d: dict[str, Any] = dict(ver.definition)
    raw_desc = d.get("description", "")
    desc = "\n".join(raw_desc) if isinstance(raw_desc, list) else str(raw_desc)

    sim_raw = d.get("simulator") or {}
    sim = JsonSimulatorSpec(
        engine=Engine(sim_raw.get("engine", "llm")),
        python_impl=sim_raw.get("python_impl"),
        llm_fallback=bool(sim_raw.get("llm_fallback", False)),
    )

    ch_raw = d.get("code_hints") or {}
    code_hints = CodeGenerationHints(
        style_hints=tuple(ch_raw.get("style_hints", [])),
        forbidden=tuple(ch_raw.get("forbidden", [])),
        example_fragment=ch_raw.get("example_fragment", ""),
    )
    edges = tuple(
        EdgeSemantic(e["field"], e.get("description", ""))
        for e in d.get("edge_semantics", []) or []
    )
    return NodeTemplate(
        id=row.id,
        name=row.name,
        display_name=row.display_name,
        category=row.category,
        scope=Scope(row.scope),
        version=ver.version_number,
        description=desc,
        input_schema=d.get("input_schema", {}),
        output_schema=d.get("output_schema", {}),
        simulator=sim,
        edge_semantics=edges,
        code_hints=code_hints,
        extensions=d.get("extensions", {}),
        definition_hash=ver.definition_hash,
        owner_id=row.owner_id,
    )


def to_anthropic_tool_spec(tpl: NodeTemplate) -> dict[str, Any]:
    return {
        "name": tpl.name,
        "description": tpl.description,
        "input_schema": dict(tpl.input_schema),
    }
