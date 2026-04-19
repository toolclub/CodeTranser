"""Run event log:把每条 RunEvent 落 DB,支持按 `after_id` 断线重连。

ChatFlow `event_store.py` 的对应物。核心:**DB 是事件流的 source of truth**,
Redis pub/sub 只是实时广播通道;Redis 挂了,重新连 DB 读 since-id 就能补齐。
"""

from abc import ABC, abstractmethod
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.session import session_scope
from app.models.mysql.event_log import RunEventLogRow


class EventLogStore(ABC):
    @abstractmethod
    async def append(
        self,
        *,
        run_id: str,
        event_type: str,
        event_data: dict[str, Any],
        message_id: str | None = None,
    ) -> int:
        """写一条事件,返回自增 id。"""

    @abstractmethod
    async def list_since(
        self,
        run_id: str,
        after_id: int = 0,
        *,
        message_id: str | None = None,
        limit: int = 2000,
    ) -> Sequence[dict[str, Any]]:
        """返回 `id > after_id` 的事件(用于 resume)。"""


class SqlEventLogStore(EventLogStore):
    """跨 session 独立写入;每次新开 session 避免把 event 绑在业务事务上。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def append(
        self,
        *,
        run_id: str,
        event_type: str,
        event_data: dict[str, Any],
        message_id: str | None = None,
    ) -> int:
        async with session_scope(self._sf) as s:
            row = RunEventLogRow(
                run_id=run_id,
                message_id=message_id,
                event_type=event_type,
                event_data=event_data,
            )
            s.add(row)
            # 先 flush 再 commit 才能拿到自增 id(ChatFlow `save_artifact id=0` 的坑)
            await s.flush()
            eid = row.id
        return int(eid)

    async def list_since(
        self,
        run_id: str,
        after_id: int = 0,
        *,
        message_id: str | None = None,
        limit: int = 2000,
    ) -> Sequence[dict[str, Any]]:
        async with self._sf() as s:
            q = (
                select(RunEventLogRow)
                .where(RunEventLogRow.run_id == run_id)
                .where(RunEventLogRow.id > after_id)
            )
            if message_id:
                q = q.where(RunEventLogRow.message_id == message_id)
            q = q.order_by(RunEventLogRow.id.asc()).limit(limit)
            rows = (await s.execute(q)).scalars().all()
            return [
                {
                    "id": r.id,
                    "run_id": r.run_id,
                    "message_id": r.message_id,
                    "event_type": r.event_type,
                    "event_data": r.event_data,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
