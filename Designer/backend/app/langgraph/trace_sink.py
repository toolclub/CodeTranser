import contextvars
from typing import Any

from app.infra.mongo.collections import RUN_STEP_DETAILS, SANDBOX_TRACES
from app.utils.clock import utcnow
from app.utils.sanitize import sanitize


class TraceSink:
    """把每一步的全量 trace 写进 MongoDB。`mongo_db=None` 时降级为 noop(写入返回虚拟 id)。"""

    SCHEMA_VERSION = 1

    def __init__(self, mongo_db: Any | None) -> None:
        self._db = mongo_db

    async def write_step_detail(
        self,
        *,
        run_id: str,
        step_id: str,
        phase: int,
        node_name: str,
        iteration: int,
        handler_name: str | None,
        input_state: dict[str, Any],
        output_state: dict[str, Any],
        tool_calls: list[dict[str, Any]],
        llm_calls: list[dict[str, Any]],
        decision: str | None = None,
        decision_reason: str | None = None,
        status: str = "success",
        error: str | None = None,
    ) -> str:
        doc = {
            "schema_version": self.SCHEMA_VERSION,
            "run_id": run_id,
            "step_id": step_id,
            "phase": phase,
            "node_name": node_name,
            "iteration": iteration,
            "handler_name": handler_name,
            "input_state": sanitize(input_state),
            "output_state": sanitize(output_state),
            "tool_calls": sanitize(tool_calls),
            "llm_calls": sanitize(llm_calls),
            "decision": decision,
            "decision_reason": decision_reason,
            "status": status,
            "error": error,
            "created_at": utcnow(),
        }
        if self._db is None:
            return f"noop_{step_id}"
        r = await self._db[RUN_STEP_DETAILS].insert_one(doc)
        return str(r.inserted_id)

    async def write_sandbox_trace(self, **kw: Any) -> str:
        doc = {"schema_version": self.SCHEMA_VERSION, "created_at": utcnow(), **kw}
        if self._db is None:
            return "noop_sandbox"
        r = await self._db[SANDBOX_TRACES].insert_one(doc)
        return str(r.inserted_id)


class ToolCallTraceContext:
    """Tool 调用轨迹 contextvar buffer。和 `LLMTraceContext` 同构。"""

    _buf: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
        "tool_call_buf", default=None
    )

    def begin_scope(self) -> None:
        self._buf.set([])

    def record(self, entry: dict[str, Any]) -> None:
        b = self._buf.get()
        if b is None:
            return
        b.append(entry)

    def end_scope(self) -> list[dict[str, Any]]:
        out = list(self._buf.get() or [])
        self._buf.set(None)
        return out
