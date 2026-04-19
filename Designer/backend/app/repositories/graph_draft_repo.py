from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import delete, select

from app.models.mysql.graph_draft import GraphDraftRow
from app.repositories.base import SqlRepoBase


class GraphDraftRepo(ABC):
    @abstractmethod
    async def get(self, graph_id: str) -> GraphDraftRow | None: ...

    @abstractmethod
    async def upsert(self, graph_id: str, snapshot: dict[str, Any], user_id: int) -> None: ...

    @abstractmethod
    async def clear(self, graph_id: str) -> None: ...


class SqlGraphDraftRepo(SqlRepoBase, GraphDraftRepo):
    async def get(self, graph_id: str) -> GraphDraftRow | None:
        return (
            await self._s.execute(
                select(GraphDraftRow).where(GraphDraftRow.graph_id == graph_id)
            )
        ).scalar_one_or_none()

    async def upsert(self, graph_id: str, snapshot: dict[str, Any], user_id: int) -> None:
        row = await self.get(graph_id)
        if row is None:
            self._s.add(
                GraphDraftRow(graph_id=graph_id, snapshot=snapshot, saved_by=user_id)
            )
        else:
            row.snapshot = snapshot
            row.saved_by = user_id

    async def clear(self, graph_id: str) -> None:
        await self._s.execute(delete(GraphDraftRow).where(GraphDraftRow.graph_id == graph_id))
