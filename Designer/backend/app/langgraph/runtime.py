import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.domain.fsm import WorkflowRunSM
from app.infra.logging import get_logger
from app.infra.run_control import SessionRegistry, StopRegistry
from app.langgraph.errors import WorkflowTimeout
from app.langgraph.events import EventType, RunEvent, RunEventBus
from app.langgraph.pipeline import PipelineBuilder, PipelineVariant
from app.langgraph.state import CascadeState, initial_state
from app.repositories.run_repo import SqlWorkflowRunRepo
from app.utils.clock import utcnow

log = get_logger(__name__)

_HEARTBEAT_INTERVAL = 20.0


class RunCancelled(Exception):
    """Run 被 StopRegistry 请求停止时抛出。"""


class WorkflowRuntime:
    """对外入口:触发一次 Run,按 variant 选 Pipeline。

    分布式铁律兑现:
      1. t_workflow_run 状态走 FSM(pending→running→success|failed|cancelled)
      2. worker_id + heartbeat_at 持续刷 DB
      3. StopRegistry 跨 pod;最多 20s 传达
      4. LangGraph checkpointer 用 thread_id=run_id,pod 换了能 resume
      5. 事件先写 DB 再 Redis 广播
    """

    def __init__(
        self,
        builder: PipelineBuilder,
        events: RunEventBus,
        settings: Settings,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        stop_registry: StopRegistry | None = None,
        session_registry: SessionRegistry | None = None,
        worker_id: str = "",
    ) -> None:
        self._b = builder
        self._e = events
        self._s = settings
        self._sf = session_factory
        self._stops = stop_registry
        self._sessions = session_registry
        self._worker_id = worker_id
        self._run_repo = SqlWorkflowRunRepo(session_factory)

    async def run(
        self,
        *,
        run_id: str,
        graph_version_id: str,
        raw_graph_json: dict[str, Any],
        variant: PipelineVariant = PipelineVariant.FULL,
        provided_scenarios: list[dict[str, Any]] | None = None,
        triggered_by: int = 0,
    ) -> CascadeState:
        state = initial_state(run_id, graph_version_id, raw_graph_json, provided_scenarios)

        # 1. DB 预写(上层若已 INSERT,则 create 静默失败并走 log)
        await self._run_repo.create(
            run_id=run_id,
            graph_version_id=graph_version_id,
            triggered_by=triggered_by,
            options={"variant": variant.value},
            worker_id=self._worker_id,
        )

        # 2. FSM: pending → running
        sm = WorkflowRunSM.from_status("pending")
        try:
            sm.fire("start")
        except Exception as e:
            log.warning("workflow_start_transition_failed", run=run_id, error=str(e))
        await self._run_repo.update_status(
            run_id,
            status=sm.current_value,
            started_at=utcnow(),
            worker_id=self._worker_id,
            heartbeat_at=utcnow(),
        )

        if self._sessions:
            await self._sessions.register(run_id)

        await self._e.emit(
            RunEvent(
                type=EventType.RUN_STARTED,
                run_id=run_id,
                ts=utcnow().isoformat(),
                payload={"variant": variant.value, "worker_id": self._worker_id},
            )
        )

        pipeline = self._b.get(variant)
        config = {"configurable": {"thread_id": run_id}}
        pipeline_task = asyncio.create_task(pipeline.ainvoke(state, config=config))
        monitor_task = asyncio.create_task(self._monitor(run_id, pipeline_task))

        final: CascadeState | None = None
        terminal_event: str = "fail"
        error_msg: str | None = None
        raised: Exception | None = None

        try:
            final = await asyncio.wait_for(
                pipeline_task, timeout=self._s.WORKFLOW_GLOBAL_TIMEOUT
            )
            terminal_event = "finish"
        except asyncio.TimeoutError as e:
            pipeline_task.cancel()
            terminal_event = "fail"
            error_msg = f"timeout after {self._s.WORKFLOW_GLOBAL_TIMEOUT}s"
            raised = WorkflowTimeout(error_msg)
        except asyncio.CancelledError:
            terminal_event = "cancel"
            error_msg = "stop requested"
            raised = RunCancelled(run_id)
        except Exception as e:
            terminal_event = "fail"
            error_msg = str(e)[:2000]
            log.exception("workflow_run_failed", run=run_id)
            raised = e
        finally:
            monitor_task.cancel()
            if self._sessions:
                await self._sessions.release(run_id)
            if self._stops:
                await self._stops.clear(run_id)

        # 3. FSM 终态 + DB 写入
        try:
            sm.fire(terminal_event)
        except Exception as e:
            log.warning(
                "workflow_terminal_transition_failed",
                run=run_id,
                event=terminal_event,
                error=str(e),
            )
        update_fields: dict[str, Any] = {
            "status": sm.current_value,
            "finished_at": utcnow(),
        }
        if final is not None:
            update_fields["final_verdict"] = final.get("final_verdict")
            update_fields["phase1_verdict"] = final.get("phase1_verdict")
            update_fields["phase3_verdict"] = final.get("phase3_verdict")
            update_fields["summary"] = {
                "handler_traces": final.get("handler_traces") or [],
                "scenario_count": len(final.get("scenario_results") or []),
            }
        if error_msg:
            update_fields["error_message"] = error_msg
            if "timeout" in error_msg:
                update_fields["error_code"] = "TIMEOUT"
            elif terminal_event == "cancel":
                update_fields["error_code"] = "CANCELLED"
            else:
                update_fields["error_code"] = "FAILED"
        await self._run_repo.update_status(run_id, **update_fields)

        await self._e.emit(
            RunEvent(
                type=EventType.RUN_FINISHED,
                run_id=run_id,
                ts=utcnow().isoformat(),
                payload={
                    "final_verdict": final.get("final_verdict") if final else None,
                    "status": sm.current_value,
                    "worker_id": self._worker_id,
                    "error_message": error_msg,
                },
            )
        )

        # 4. 抛出上游关心的错误
        if raised is not None:
            raise raised
        assert final is not None
        return final

    async def _monitor(self, run_id: str, pipeline_task: asyncio.Task[Any]) -> None:
        while not pipeline_task.done():
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                if self._sessions:
                    await self._sessions.heartbeat(run_id)
                await self._run_repo.heartbeat(run_id, self._worker_id)
                if self._stops and await self._stops.is_stopped(run_id):
                    log.info("run_stop_requested", run_id=run_id, worker=self._worker_id)
                    pipeline_task.cancel()
                    return
            except asyncio.CancelledError:
                return
            except Exception as e:
                log.warning("monitor_loop_error", run_id=run_id, error=str(e))
