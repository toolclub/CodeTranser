import re
from typing import Any

from app.config import Settings
from app.domain.errors import Forbidden
from app.domain.run.sim import SimContext
from app.domain.tool.tool import NodeTemplate, Scope
from app.middlewares.auth import CurrentUser
from app.models.mysql.node_template import NodeTemplateRow
from app.repositories.tool_repo import ToolRepo
from app.schemas.tool import (
    CodeHintsDTO,
    EdgeSemanticDTO,
    JsonSimulatorDTO,
    NodeTemplateCardDTO,
    NodeTemplateCreateDTO,
    NodeTemplateDefinitionDTO,
    NodeTemplateOutDTO,
    NodeTemplateSimulateReqDTO,
    NodeTemplateSimulateRespDTO,
    NodeTemplateUpdateDTO,
)
from app.tool_runtime.errors import (
    SimulatorNotRegistered,
    TemplateDefinitionInvalid,
)
from app.tool_runtime.json_parser import parse_definition
from app.tool_runtime.json_schema import validate_input, validate_output
from app.tool_runtime.registry import ToolRegistry
from app.tool_runtime.simulators import SIMULATOR_REGISTRY

_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_]{2,63}$")
_FIELD_RE = re.compile(r"^[a-z_][a-zA-Z0-9_]{0,63}$")


class ToolService:
    """节点模板 Policy 层。

    - 管控权限(admin vs private owner)
    - 保证私有强制 engine=llm
    - 保证 pure_python 对应 simulator 已注册
    - simulate 预览(不落 DB)
    """

    def __init__(
        self,
        repo: ToolRepo,
        registry: ToolRegistry,
        llm_client: Any,
        settings: Settings,
    ) -> None:
        self._repo = repo
        self._registry = registry
        self._llm = llm_client
        self._settings = settings

    # ---- create/update ----

    async def create_global(
        self, dto: NodeTemplateCreateDTO, user: CurrentUser
    ) -> str:
        if not user.is_admin:
            raise Forbidden("create global template requires admin")
        self._pre_check_name(dto.name)
        self._validate_definition(dto.definition, scope=Scope.GLOBAL)
        tid, _ = await self._repo.create(dto, user.id)
        await self._registry.invalidate(tid)
        return tid

    async def create_private(
        self, dto: NodeTemplateCreateDTO, user: CurrentUser
    ) -> str:
        self._pre_check_name(dto.name)
        if dto.definition.simulator.engine != "llm":
            raise TemplateDefinitionInvalid("private template must use engine=llm")
        self._validate_definition(dto.definition, scope=Scope.PRIVATE)
        dto2 = dto.model_copy(update={"scope": "private"})
        tid, _ = await self._repo.create(dto2, user.id)
        await self._registry.invalidate(tid)
        return tid

    async def update(
        self,
        template_id: str,
        dto: NodeTemplateUpdateDTO,
        user: CurrentUser,
    ) -> int:
        row = await self._repo.get(template_id)
        self._require_can_write(row, user)
        scope = Scope(row.scope)
        if scope is Scope.PRIVATE and dto.definition.simulator.engine != "llm":
            raise TemplateDefinitionInvalid("private template must use engine=llm")
        self._validate_definition(dto.definition, scope=scope)
        new_ver = await self._repo.update_create_version(
            template_id, dto.definition, dto.change_note, user.id
        )
        await self._registry.invalidate(template_id)
        return new_ver

    async def fork(self, template_id: str, user: CurrentUser) -> str:
        new_tid = await self._repo.fork_to_private(template_id, user.id, user.id)
        await self._registry.invalidate(new_tid)
        return new_tid

    # ---- query ----

    async def list_visible(
        self,
        *,
        scope: str,
        category: str | None,
        user: CurrentUser,
    ) -> list[NodeTemplateRow]:
        scope_enum: Scope | None = None
        if scope == "global":
            scope_enum = Scope.GLOBAL
        elif scope == "private":
            scope_enum = Scope.PRIVATE
        rows = await self._repo.list(
            scope=scope_enum,
            owner_id=user.id if scope == "private" else None,
            category=category,
        )
        return list(rows)

    # ---- simulate ----

    async def simulate(
        self,
        template_id: str,
        req: NodeTemplateSimulateReqDTO,
        user: CurrentUser,
    ) -> NodeTemplateSimulateRespDTO:
        tpl = await self._registry.get_by_id(template_id)
        sim = self._registry.simulator_of(tpl)
        ctx = SimContext(
            run_id="preview",
            instance_id="preview",
            table_data=req.tables,
            llm=self._llm,
            trace=None,
        )
        validate_input(tpl.input_schema, req.field_values)
        r = sim.run(req.field_values, req.input_json, ctx)
        validate_output(tpl.output_schema, r.output)
        return NodeTemplateSimulateRespDTO(
            output_json=r.output,
            engine_used=r.engine_used.value,
            duration_ms=r.duration_ms,
            llm_call_id=r.llm_call_ref,
        )

    # ---- projection DTOs ----

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    @property
    def repo(self) -> ToolRepo:
        return self._repo

    def to_card_dto(self, tpl: NodeTemplate) -> NodeTemplateCardDTO:
        return NodeTemplateCardDTO(
            id=tpl.id,
            name=tpl.name,
            display_name=tpl.display_name,
            category=tpl.category,
            current_version=tpl.version,
            input_schema=dict(tpl.input_schema),
            edge_semantics=[
                EdgeSemanticDTO(field=e.field, description=e.description)
                for e in tpl.edge_semantics
            ],
            extensions=dict(tpl.extensions),
        )

    def to_out_dto(self, tpl: NodeTemplate) -> NodeTemplateOutDTO:
        return NodeTemplateOutDTO(
            id=tpl.id,
            name=tpl.name,
            display_name=tpl.display_name,
            category=tpl.category,
            scope=tpl.scope.value,
            status="active",
            current_version=tpl.version,
            definition=NodeTemplateDefinitionDTO(
                description=tpl.description.split("\n") if tpl.description else [],
                input_schema=dict(tpl.input_schema),
                output_schema=dict(tpl.output_schema),
                simulator=JsonSimulatorDTO(
                    engine=tpl.simulator.engine.value,
                    python_impl=tpl.simulator.python_impl,
                    llm_fallback=tpl.simulator.llm_fallback,
                ),
                edge_semantics=[
                    EdgeSemanticDTO(field=e.field, description=e.description)
                    for e in tpl.edge_semantics
                ],
                code_hints=CodeHintsDTO(
                    style_hints=list(tpl.code_hints.style_hints),
                    forbidden=list(tpl.code_hints.forbidden),
                    example_fragment=tpl.code_hints.example_fragment,
                ),
                extensions=dict(tpl.extensions),
            ),
            created_at="",
            updated_at="",
        )

    # ---- private ----

    def _pre_check_name(self, name: str) -> None:
        if not _NAME_RE.match(name):
            raise TemplateDefinitionInvalid(f"bad template name: {name}")

    def _validate_definition(
        self, d: NodeTemplateDefinitionDTO, *, scope: Scope
    ) -> None:
        joined_desc = "\n".join(d.description)
        if len(joined_desc) > self._settings.TOOL_DESCRIPTION_MAX_LENGTH:
            raise TemplateDefinitionInvalid("description too long")
        for kw in self._settings.TOOL_INJECTION_BLOCKLIST or []:
            if kw and kw in joined_desc:
                raise TemplateDefinitionInvalid(f"blocklist hit: {kw}")
        parse_definition(d.model_dump())
        if d.simulator.engine == "pure_python":
            if scope is Scope.PRIVATE:
                raise TemplateDefinitionInvalid("private template must be engine=llm")
            impl = d.simulator.python_impl
            if impl is None or impl not in SIMULATOR_REGISTRY:
                raise SimulatorNotRegistered(impl or "<none>")
        for e in d.edge_semantics:
            if not _FIELD_RE.match(e.field):
                raise TemplateDefinitionInvalid(f"invalid edge field: {e.field}")
        fields = [e.field for e in d.edge_semantics]
        if len(set(fields)) != len(fields):
            raise TemplateDefinitionInvalid("duplicate edge_semantics.field")

    def _require_can_write(self, row: NodeTemplateRow, user: CurrentUser) -> None:
        if user.is_admin:
            return
        if row.scope == "global":
            raise Forbidden("global template is admin-only")
        if row.owner_id != user.id:
            raise Forbidden("not your private template")
