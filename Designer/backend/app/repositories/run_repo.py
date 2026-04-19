from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.session import session_scope
from app.infra.logging import get_logger
from app.models.mysql.workflow_run import WorkflowRunRow
from app.utils.clock import utcnow

log = get_logger(__name__)


class WorkflowRunRepo(ABC):
    @abstractmethod
    async def create(
        self,
        *,
        run_id: str,
        graph_version_id: str,
        triggered_by: int,
        options: dict[str, Any],
        worker_id: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def get(self, run_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def update_status(self, run_id: str, **fields: Any) -> None: ...

    @abstractmethod
    async def heartbeat(self, run_id: str, worker_id: str) -> None: ...


class SqlWorkflowRunRepo(WorkflowRunRepo):
    """直接用 session_factory 起独立 session(workflow 状态更新 vs 业务事务解耦)。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def create(
        self,
        *,
        run_id: str,
        graph_version_id: str,
        triggered_by: int,
        options: dict[str, Any],
        worker_id: str | None = None,
    ) -> None:
        try:
            async with session_scope(self._sf) as s:
                s.add(
                    WorkflowRunRow(
                        id=run_id,
                        graph_version_id=graph_version_id,
                        status="pending",
                        triggered_by=triggered_by,
                        summary={},
                        options=options,
                        worker_id=worker_id,
                    )
                )
        except Exception as e:
            log.warning("workflow_run_create_failed", run_id=run_id, error=str(e))

    async def get(self, run_id: str) -> dict[str, Any] | None:
        async with self._sf() as s:
            r = (
                await s.execute(
                    select(WorkflowRunRow).where(WorkflowRunRow.id == run_id)
                )
            ).scalar_one_or_none()
            if r is None:
                return None
            return {
                "id": r.id,
                "graph_version_id": r.graph_version_id,
                "status": r.status,
                "final_verdict": r.final_verdict,
                "phase1_verdict": r.phase1_verdict,
                "phase3_verdict": r.phase3_verdict,
                "worker_id": r.worker_id,
                "heartbeat_at": r.heartbeat_at.isoformat() if r.heartbeat_at else None,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "error_code": r.error_code,
                "error_message": r.error_message,
            }

    async def update_status(self, run_id: str, **fields: Any) -> None:
        if not fields:
            return
        try:
            async with session_scope(self._sf) as s:
                await s.execute(
                    update(WorkflowRunRow)
                    .where(WorkflowRunRow.id == run_id)
                    .values(**fields)
                )
        except Exception as e:
            log.warning(
                "workflow_run_update_failed",
                run_id=run_id,
                fields=list(fields.keys()),
                error=str(e),
            )

    async def heartbeat(self, run_id: str, worker_id: str) -> None:
        try:
            async with session_scope(self._sf) as s:
                await s.execute(
                    update(WorkflowRunRow)
                    .where(WorkflowRunRow.id == run_id)
                    .values(worker_id=worker_id, heartbeat_at=utcnow())
                )
        except Exception as e:
            log.warning("workflow_run_heartbeat_failed", run_id=run_id, error=str(e))


class RunStepRepo(ABC):
    @abstractmethod
    async def insert(self, step: dict[str, Any]) -> None: ...

    @abstractmethod
    async def list_by_run(self, run_id: str) -> Sequence[dict[str, Any]]: ...


class JsonCaseRepo(ABC):
    @abstractmethod
    async def insert(self, case: dict[str, Any]) -> None: ...

    @abstractmethod
    async def list_by_run(self, run_id: str) -> Sequence[dict[str, Any]]: ...


class SandboxCaseRepo(ABC):
    @abstractmethod
    async def insert(self, case: dict[str, Any]) -> None: ...

    @abstractmethod
    async def list_by_run(self, run_id: str) -> Sequence[dict[str, Any]]: ...


class CodeSnapshotRepo(ABC):
    @abstractmethod
    async def insert(self, snapshot: dict[str, Any]) -> None: ...

    @abstractmethod
    async def by_iter(self, run_id: str, iteration: int) -> dict[str, Any] | None: ...
