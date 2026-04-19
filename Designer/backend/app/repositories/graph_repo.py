from abc import ABC, abstractmethod
from typing import Any, Sequence

from sqlalchemy import select, update

from app.domain.errors import NotFound
from app.models.mysql.cascade_graph import CascadeGraphRow
from app.repositories.base import SqlRepoBase
from app.utils.clock import utcnow
from app.utils.ids import new_id


class GraphRepo(ABC):
    @abstractmethod
    async def create(self, name: str, description: str, owner_id: int) -> str: ...

    @abstractmethod
    async def get(self, graph_id: str) -> CascadeGraphRow: ...

    @abstractmethod
    async def list_mine(self, owner_id: int) -> Sequence[CascadeGraphRow]: ...

    @abstractmethod
    async def update_meta(
        self, graph_id: str, name: str | None, desc: str | None
    ) -> None: ...

    @abstractmethod
    async def soft_delete(self, graph_id: str) -> None: ...

    @abstractmethod
    async def set_latest_version(self, graph_id: str, version_id: str) -> None: ...


class SqlGraphRepo(SqlRepoBase, GraphRepo):
    async def create(self, name: str, description: str, owner_id: int) -> str:
        gid = new_id("g", 8)
        self._s.add(
            CascadeGraphRow(
                id=gid, name=name, description=description, owner_id=owner_id
            )
        )
        await self._s.flush()
        return gid

    async def get(self, graph_id: str) -> CascadeGraphRow:
        r = (
            await self._s.execute(
                select(CascadeGraphRow).where(
                    CascadeGraphRow.id == graph_id,
                    CascadeGraphRow.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if r is None:
            raise NotFound(graph_id)
        return r

    async def list_mine(self, owner_id: int) -> Sequence[CascadeGraphRow]:
        return list(
            (
                await self._s.execute(
                    select(CascadeGraphRow)
                    .where(
                        CascadeGraphRow.owner_id == owner_id,
                        CascadeGraphRow.deleted_at.is_(None),
                    )
                    .order_by(CascadeGraphRow.updated_at.desc())
                )
            ).scalars().all()
        )

    async def update_meta(
        self, graph_id: str, name: str | None, desc: str | None
    ) -> None:
        vals: dict[str, Any] = {}
        if name is not None:
            vals["name"] = name
        if desc is not None:
            vals["description"] = desc
        if vals:
            await self._s.execute(
                update(CascadeGraphRow)
                .where(CascadeGraphRow.id == graph_id)
                .values(**vals)
            )

    async def soft_delete(self, graph_id: str) -> None:
        await self._s.execute(
            update(CascadeGraphRow)
            .where(CascadeGraphRow.id == graph_id)
            .values(deleted_at=utcnow())
        )

    async def set_latest_version(self, graph_id: str, version_id: str) -> None:
        await self._s.execute(
            update(CascadeGraphRow)
            .where(CascadeGraphRow.id == graph_id)
            .values(latest_version_id=version_id)
        )
