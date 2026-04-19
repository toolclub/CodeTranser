"""BasePipelineStep 需要的 run_step 存储接口。

分布式铁律:步骤摘要 **必须** 入 `t_run_step` 表(`NoopRunStepStore` 只能用于单元测试)。
生产用 `SqlRunStepStore`。
"""

from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.session import session_scope
from app.infra.logging import get_logger
from app.models.mysql.run_step import RunStepRow

log = get_logger(__name__)


class RunStepStore(Protocol):
    async def create(
        self,
        *,
        id: str,
        run_id: str,
        phase: int,
        node_name: str,
        iteration_index: int,
        status: str,
        mongo_ref: str | None,
        duration_ms: int,
        started_at: datetime,
        summary: dict[str, Any],
        error_message: str | None = None,
    ) -> None: ...


class SqlRunStepStore:
    """生产实现:每个 step 结束时写一行 `t_run_step`。

    用独立 session(不复用业务事务),避免 step 失败写 trace 时把主事务搞坏。
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def create(
        self,
        *,
        id: str,
        run_id: str,
        phase: int,
        node_name: str,
        iteration_index: int,
        status: str,
        mongo_ref: str | None,
        duration_ms: int,
        started_at: datetime,
        summary: dict[str, Any],
        error_message: str | None = None,
    ) -> None:
        try:
            async with session_scope(self._sf) as s:
                s.add(
                    RunStepRow(
                        id=id,
                        run_id=run_id,
                        phase=phase,
                        node_name=node_name,
                        iteration_index=iteration_index,
                        status=status,
                        mongo_ref=mongo_ref,
                        duration_ms=duration_ms,
                        started_at=started_at,
                        summary=summary or {},
                        error_message=error_message,
                    )
                )
        except Exception as e:
            # 不抛出,以免拖垮正在成功返回的主流程(已有 log 追踪)
            log.warning(
                "run_step_persist_failed",
                run_id=run_id,
                step_id=id,
                error=str(e),
            )


class NoopRunStepStore:
    """**仅单元测试使用**。生产必须用 `SqlRunStepStore`,否则 t_run_step 永远为空。"""

    async def create(self, **_: Any) -> None:
        return None
