from abc import ABC, abstractmethod
from typing import Any, Sequence

from sqlalchemy import select

from app.domain.errors import NotFound
from app.domain.graph.errors import StaleVersion
from app.models.mysql.graph_version import GraphVersionRow
from app.repositories.base import SqlRepoBase
from app.utils.ids import new_id


class GraphVersionRepo(ABC):
    @abstractmethod
    async def save_new(
        self,
        graph_id: str,
        snapshot: dict[str, Any],
        commit_message: str,
        parent_version_id: str | None,
        user_id: int,
    ) -> GraphVersionRow: ...

    @abstractmethod
    async def get(self, version_id: str) -> GraphVersionRow: ...

    @abstractmethod
    async def get_by_number(
        self, graph_id: str, version_number: int
    ) -> GraphVersionRow: ...

    @abstractmethod
    async def list(self, graph_id: str) -> Sequence[GraphVersionRow]: ...


class SqlGraphVersionRepo(SqlRepoBase, GraphVersionRepo):
    async def save_new(
        self,
        graph_id: str,
        snapshot: dict[str, Any],
        commit_message: str,
        parent_version_id: str | None,
        user_id: int,
    ) -> GraphVersionRow:
        latest = (
            await self._s.execute(
                select(GraphVersionRow)
                .where(GraphVersionRow.graph_id == graph_id)
                .order_by(GraphVersionRow.version_number.desc())
            )
        ).scalars().first()
        if (
            latest is not None
            and parent_version_id is not None
            and latest.id != parent_version_id
        ):
            raise StaleVersion(
                "graph version changed",
                expected=parent_version_id,
                latest=latest.id,
            )
        new_num = (latest.version_number if latest else 0) + 1
        vid = new_id("gv", 8)
        row = GraphVersionRow(
            id=vid,
            graph_id=graph_id,
            version_number=new_num,
            snapshot=snapshot,
            commit_message=commit_message,
            parent_version_id=(latest.id if latest else None),
            created_by=user_id,
        )
        self._s.add(row)
        await self._s.flush()
        return row

    async def get(self, version_id: str) -> GraphVersionRow:
        r = (
            await self._s.execute(
                select(GraphVersionRow).where(GraphVersionRow.id == version_id)
            )
        ).scalar_one_or_none()
        if r is None:
            raise NotFound(version_id)
        return r

    async def get_by_number(
        self, graph_id: str, version_number: int
    ) -> GraphVersionRow:
        r = (
            await self._s.execute(
                select(GraphVersionRow).where(
                    GraphVersionRow.graph_id == graph_id,
                    GraphVersionRow.version_number == version_number,
                )
            )
        ).scalar_one_or_none()
        if r is None:
            raise NotFound(f"{graph_id}@{version_number}")
        return r

    async def list(self, graph_id: str) -> Sequence[GraphVersionRow]:
        return list(
            (
                await self._s.execute(
                    select(GraphVersionRow)
                    .where(GraphVersionRow.graph_id == graph_id)
                    .order_by(GraphVersionRow.version_number.desc())
                )
            ).scalars().all()
        )
