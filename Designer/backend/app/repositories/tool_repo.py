from abc import ABC, abstractmethod
from typing import Sequence

from sqlalchemy import select, update

from app.domain.tool.tool import Scope
from app.models.mysql.node_template import NodeTemplateRow
from app.models.mysql.node_template_version import NodeTemplateVersionRow
from app.repositories.base import SqlRepoBase
from app.schemas.tool import NodeTemplateCreateDTO, NodeTemplateDefinitionDTO
from app.tool_runtime.errors import NodeTemplateNotFound, TemplateDefinitionInvalid
from app.utils.clock import utcnow
from app.utils.hash import sha256_json
from app.utils.ids import new_id


class ToolRepo(ABC):
    @abstractmethod
    async def create(self, dto: NodeTemplateCreateDTO, user_id: int) -> tuple[str, int]: ...

    @abstractmethod
    async def update_create_version(
        self,
        template_id: str,
        definition: NodeTemplateDefinitionDTO,
        change_note: str,
        user_id: int,
    ) -> int: ...

    @abstractmethod
    async def activate_version(self, template_id: str, version_number: int) -> None: ...

    @abstractmethod
    async def list(
        self,
        *,
        scope: Scope | None,
        owner_id: int | None,
        category: str | None,
        status: str | None = None,
    ) -> Sequence[NodeTemplateRow]: ...

    @abstractmethod
    async def soft_delete(self, template_id: str) -> None: ...

    @abstractmethod
    async def fork_to_private(self, template_id: str, owner_id: int, user_id: int) -> str: ...

    @abstractmethod
    async def get(self, template_id: str) -> NodeTemplateRow: ...

    @abstractmethod
    async def get_version(
        self, template_id: str, version_number: int
    ) -> NodeTemplateVersionRow: ...

    @abstractmethod
    async def list_versions(self, template_id: str) -> Sequence[NodeTemplateVersionRow]: ...


class SqlToolRepo(SqlRepoBase, ToolRepo):
    async def create(
        self, dto: NodeTemplateCreateDTO, user_id: int
    ) -> tuple[str, int]:
        q = select(NodeTemplateRow).where(
            NodeTemplateRow.name == dto.name,
            NodeTemplateRow.scope == dto.scope,
        )
        if dto.scope == "private":
            q = q.where(NodeTemplateRow.owner_id == user_id)
        if (await self._s.execute(q)).scalar_one_or_none():
            raise TemplateDefinitionInvalid(f"duplicate template name: {dto.name}")

        tid = new_id("tpl", 8)
        vid = new_id("tpv", 8)
        defn = dto.definition.model_dump()
        self._s.add(
            NodeTemplateRow(
                id=tid,
                name=dto.name,
                display_name=dto.display_name,
                category=dto.category,
                scope=dto.scope,
                status="active",
                owner_id=user_id if dto.scope == "private" else None,
                created_by=user_id,
                current_version_id=vid,
            )
        )
        self._s.add(
            NodeTemplateVersionRow(
                id=vid,
                template_id=tid,
                version_number=1,
                definition=defn,
                definition_hash=sha256_json(defn),
                change_note=dto.change_note,
                created_by=user_id,
            )
        )
        await self._s.flush()
        return tid, 1

    async def update_create_version(
        self,
        template_id: str,
        definition: NodeTemplateDefinitionDTO,
        change_note: str,
        user_id: int,
    ) -> int:
        latest = (
            await self._s.execute(
                select(NodeTemplateVersionRow)
                .where(NodeTemplateVersionRow.template_id == template_id)
                .order_by(NodeTemplateVersionRow.version_number.desc())
            )
        ).scalars().first()
        new_num = (latest.version_number if latest else 0) + 1
        vid = new_id("tpv", 8)
        defn = definition.model_dump()
        self._s.add(
            NodeTemplateVersionRow(
                id=vid,
                template_id=template_id,
                version_number=new_num,
                definition=defn,
                definition_hash=sha256_json(defn),
                change_note=change_note,
                created_by=user_id,
            )
        )
        await self._s.flush()
        await self._s.execute(
            update(NodeTemplateRow)
            .where(NodeTemplateRow.id == template_id)
            .values(current_version_id=vid)
        )
        return new_num

    async def activate_version(self, template_id: str, version_number: int) -> None:
        v = await self.get_version(template_id, version_number)
        await self._s.execute(
            update(NodeTemplateRow)
            .where(NodeTemplateRow.id == template_id)
            .values(current_version_id=v.id)
        )

    async def list(
        self,
        *,
        scope: Scope | None,
        owner_id: int | None,
        category: str | None,
        status: str | None = None,
    ) -> Sequence[NodeTemplateRow]:
        q = select(NodeTemplateRow).where(NodeTemplateRow.deleted_at.is_(None))
        if scope is not None:
            q = q.where(NodeTemplateRow.scope == scope.value)
        if owner_id is not None:
            q = q.where(NodeTemplateRow.owner_id == owner_id)
        if category is not None:
            q = q.where(NodeTemplateRow.category == category)
        if status is not None:
            q = q.where(NodeTemplateRow.status == status)
        return list((await self._s.execute(q)).scalars().all())

    async def soft_delete(self, template_id: str) -> None:
        await self._s.execute(
            update(NodeTemplateRow)
            .where(NodeTemplateRow.id == template_id)
            .values(deleted_at=utcnow())
        )

    async def fork_to_private(
        self, template_id: str, owner_id: int, user_id: int
    ) -> str:
        src = await self.get(template_id)
        src_v = (
            await self._s.execute(
                select(NodeTemplateVersionRow).where(
                    NodeTemplateVersionRow.id == src.current_version_id
                )
            )
        ).scalar_one()
        definition = dict(src_v.definition)
        definition["simulator"] = {
            "engine": "llm",
            "python_impl": None,
            "llm_fallback": False,
        }
        new_tid = new_id("tpl", 8)
        new_vid = new_id("tpv", 8)
        self._s.add(
            NodeTemplateRow(
                id=new_tid,
                name=src.name + "_fork",
                display_name=f"{src.display_name} (Fork)",
                category=src.category,
                scope="private",
                status="active",
                owner_id=owner_id,
                forked_from_id=src.id,
                created_by=user_id,
                current_version_id=new_vid,
            )
        )
        self._s.add(
            NodeTemplateVersionRow(
                id=new_vid,
                template_id=new_tid,
                version_number=1,
                definition=definition,
                definition_hash=sha256_json(definition),
                change_note="fork",
                created_by=user_id,
            )
        )
        await self._s.flush()
        return new_tid

    async def get(self, template_id: str) -> NodeTemplateRow:
        row = (
            await self._s.execute(
                select(NodeTemplateRow).where(NodeTemplateRow.id == template_id)
            )
        ).scalar_one_or_none()
        if row is None:
            raise NodeTemplateNotFound(template_id)
        return row

    async def get_version(
        self, template_id: str, version_number: int
    ) -> NodeTemplateVersionRow:
        v = (
            await self._s.execute(
                select(NodeTemplateVersionRow).where(
                    NodeTemplateVersionRow.template_id == template_id,
                    NodeTemplateVersionRow.version_number == version_number,
                )
            )
        ).scalar_one_or_none()
        if v is None:
            raise NodeTemplateNotFound(f"{template_id} v{version_number}")
        return v

    async def list_versions(
        self, template_id: str
    ) -> Sequence[NodeTemplateVersionRow]:
        return list(
            (
                await self._s.execute(
                    select(NodeTemplateVersionRow)
                    .where(NodeTemplateVersionRow.template_id == template_id)
                    .order_by(NodeTemplateVersionRow.version_number.desc())
                )
            ).scalars().all()
        )
