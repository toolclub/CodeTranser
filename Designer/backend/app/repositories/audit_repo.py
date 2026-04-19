from abc import ABC, abstractmethod
from typing import Any

from app.models.mysql.audit_log import AuditLogRow
from app.repositories.base import SqlRepoBase
from app.utils.ids import new_id


class AuditRepo(ABC):
    @abstractmethod
    async def write(
        self,
        actor_user_id: int,
        action: str,
        target_type: str,
        target_id: str,
        result: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
        trace_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None: ...


class SqlAuditRepo(SqlRepoBase, AuditRepo):
    async def write(
        self,
        actor_user_id: int,
        action: str,
        target_type: str,
        target_id: str,
        result: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
        trace_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._s.add(
            AuditLogRow(
                id=new_id("al", 12),
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                result=result,
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
                extra=extra or {},
            )
        )
