from abc import ABC, abstractmethod
from typing import Any, Sequence

from app.domain.tool.tool import NodeTemplate, Scope


class NodeTemplateRepo(ABC):
    """节点模板(= Tool)读写抽象。SQL 实现由 03 章落地。"""

    @abstractmethod
    async def get_by_id(self, tpl_id: str) -> NodeTemplate | None: ...

    @abstractmethod
    async def list_visible(self, user_id: int, is_admin: bool) -> Sequence[NodeTemplate]: ...

    @abstractmethod
    async def list_by_scope(self, scope: Scope) -> Sequence[NodeTemplate]: ...

    @abstractmethod
    async def create(self, tpl: NodeTemplate, definition: dict[str, Any], created_by: int) -> NodeTemplate: ...

    @abstractmethod
    async def update_definition(
        self,
        tpl_id: str,
        definition: dict[str, Any],
        change_note: str,
        updated_by: int,
    ) -> NodeTemplate: ...


class NodeTemplateVersionRepo(ABC):
    @abstractmethod
    async def latest(self, template_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def by_version(self, template_id: str, version_number: int) -> dict[str, Any] | None: ...
