from abc import ABC, abstractmethod
from time import perf_counter_ns
from typing import Any, ClassVar

from app.infra.logging import get_logger
from app.langgraph.errors import StepFailed
from app.langgraph.events import EventType, RunEvent, RunEventBus
from app.langgraph.run_step_store import RunStepStore
from app.langgraph.state import CascadeState
from app.langgraph.trace_sink import ToolCallTraceContext, TraceSink
from app.llm.decorators.trace import LLMTraceContext
from app.utils.clock import utcnow
from app.utils.ids import new_id

log = get_logger(__name__)

_HEAVY_KEYS = frozenset({"raw_graph_json", "composite_code", "code_skeleton"})


def _strip_heavy(state: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in state.items():
        if k in _HEAVY_KEYS:
            if v is None:
                out[k] = None
            else:
                out[k] = {"__omitted__": True, "size_hint": len(str(v))}
        else:
            out[k] = v
    return out


class BasePipelineStep(ABC):
    """模板方法:把横切关注点(trace / events / run_step 摘要 / 异常包装)固化,
    子类只需实现 `_do(state) -> state`。
    """

    name: ClassVar[str] = ""
    phase: ClassVar[int] = 0
    depends_on: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        *,
        event_bus: RunEventBus,
        trace_sink: TraceSink,
        llm_trace_ctx: LLMTraceContext,
        tool_trace_ctx: ToolCallTraceContext,
        run_step_store: RunStepStore,
    ) -> None:
        self._events = event_bus
        self._trace = trace_sink
        self._llm_ctx = llm_trace_ctx
        self._tool_ctx = tool_trace_ctx
        self._run_step = run_step_store

    async def execute(self, state: CascadeState) -> CascadeState:
        step_id = new_id("s", 12)
        t0 = perf_counter_ns()
        self._llm_ctx.begin_scope()
        self._tool_ctx.begin_scope()

        await self._events.emit(
            RunEvent(
                type=EventType.STEP_STARTED,
                run_id=state["run_id"],
                ts=utcnow().isoformat(),
                phase=self.phase,
                step_id=step_id,
                node_name=self.name,
            )
        )

        try:
            new_state = await self._do(state)
            duration_ms = (perf_counter_ns() - t0) // 1_000_000
            llm_calls = self._llm_ctx.end_scope()
            tool_calls = self._tool_ctx.end_scope()
            mongo_ref = await self._trace.write_step_detail(
                run_id=state["run_id"],
                step_id=step_id,
                phase=self.phase,
                node_name=self.name,
                iteration=self._iteration_of(state),
                handler_name=new_state.get("current_handler"),
                input_state=_strip_heavy(dict(state)),
                output_state=_strip_heavy(dict(new_state)),
                tool_calls=tool_calls,
                llm_calls=llm_calls,
                decision=new_state.get("decision"),
                status="success",
            )
            await self._run_step.create(
                id=step_id,
                run_id=state["run_id"],
                phase=self.phase,
                node_name=self.name,
                iteration_index=self._iteration_of(state),
                status="success",
                mongo_ref=mongo_ref,
                duration_ms=int(duration_ms),
                started_at=utcnow(),
                summary=self._summary(new_state),
            )
            await self._events.emit(
                RunEvent(
                    type=EventType.STEP_COMPLETED,
                    run_id=state["run_id"],
                    ts=utcnow().isoformat(),
                    phase=self.phase,
                    step_id=step_id,
                    node_name=self.name,
                    payload={"status": "success", "duration_ms": duration_ms},
                )
            )
            return new_state

        except Exception as e:
            duration_ms = (perf_counter_ns() - t0) // 1_000_000
            llm_calls = self._llm_ctx.end_scope()
            tool_calls = self._tool_ctx.end_scope()
            log.error("step_failed", step=self.name, error=str(e))
            try:
                await self._trace.write_step_detail(
                    run_id=state["run_id"],
                    step_id=step_id,
                    phase=self.phase,
                    node_name=self.name,
                    iteration=self._iteration_of(state),
                    handler_name=state.get("current_handler"),
                    input_state=_strip_heavy(dict(state)),
                    output_state={},
                    tool_calls=tool_calls,
                    llm_calls=llm_calls,
                    status="failed",
                    error=str(e),
                )
                await self._run_step.create(
                    id=step_id,
                    run_id=state["run_id"],
                    phase=self.phase,
                    node_name=self.name,
                    iteration_index=self._iteration_of(state),
                    status="failed",
                    mongo_ref=None,
                    duration_ms=int(duration_ms),
                    started_at=utcnow(),
                    summary={},
                    error_message=str(e)[:2000],
                )
            finally:
                await self._events.emit(
                    RunEvent(
                        type=EventType.STEP_COMPLETED,
                        run_id=state["run_id"],
                        ts=utcnow().isoformat(),
                        phase=self.phase,
                        step_id=step_id,
                        node_name=self.name,
                        payload={"status": "failed", "error": str(e)[:500]},
                    )
                )
            raise StepFailed(f"{self.name}: {e}") from e

    @abstractmethod
    async def _do(self, state: CascadeState) -> CascadeState: ...

    def _iteration_of(self, state: CascadeState) -> int:
        return 0

    def _summary(self, state: CascadeState) -> dict[str, Any]:
        return {}


class HandlerStep(BasePipelineStep):
    """Phase1 责任链 Handler 基类。新 Handler 只需:
    - 继承本类,设定 `name / handler_order`
    - 实现 `_handle(state, trace) -> "pass" | "fail"`
    """

    phase = 1
    handler_order: ClassVar[int] = 0

    async def _do(self, state: CascadeState) -> CascadeState:
        state["current_handler"] = self.name
        await self._events.emit(
            RunEvent(
                type=EventType.HANDLER_STARTED,
                run_id=state["run_id"],
                ts=utcnow().isoformat(),
                phase=1,
                handler_name=self.name,
            )
        )
        trace: dict[str, Any] = {
            "handler_name": self.name,
            "started_at": utcnow().isoformat(),
            "status": "pass",
            "summary": "",
            "details": {},
            "errors": [],
        }
        try:
            outcome = await self._handle(state, trace)
            trace["finished_at"] = utcnow().isoformat()
            trace["status"] = "pass" if outcome == "pass" else "fail"
            state.setdefault("handler_traces", []).append(trace)
            state["decision"] = "handler_pass" if outcome == "pass" else "handler_fail"
            await self._events.emit(
                RunEvent(
                    type=EventType.HANDLER_COMPLETED,
                    run_id=state["run_id"],
                    ts=utcnow().isoformat(),
                    phase=1,
                    handler_name=self.name,
                    payload={"status": trace["status"]},
                )
            )
            return state
        except Exception as e:
            trace["status"] = "error"
            trace["errors"].append({"kind": "exception", "msg": str(e)})
            trace["finished_at"] = utcnow().isoformat()
            state.setdefault("handler_traces", []).append(trace)
            raise

    @abstractmethod
    async def _handle(self, state: CascadeState, trace: dict[str, Any]) -> str: ...
