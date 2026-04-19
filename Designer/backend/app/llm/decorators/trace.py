import contextvars
from typing import Any

from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse
from app.utils.hash import sha256_json
from app.utils.sanitize import sanitize


class LLMTraceContext:
    """用 contextvar 管理当前 step 的 LLM 调用 trace buffer。

    Ch06 `BasePipelineStep` 在每个 step 开始时 `begin_scope()`,
    结束时 `end_scope()` 把缓冲取出写入 Mongo。
    scope 外的调用(如预览 simulate)会被静默丢弃。
    """

    _buf: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
        "llm_trace_buf", default=None
    )

    def begin_scope(self) -> None:
        self._buf.set([])

    def record(self, entry: dict[str, Any]) -> None:
        b = self._buf.get()
        if b is None:
            return
        b.append(entry)

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self._buf.get() or [])

    def end_scope(self) -> list[dict[str, Any]]:
        out = list(self._buf.get() or [])
        self._buf.set(None)
        return out


class TraceDecorator:
    def __init__(self, inner: LLMProvider, trace_context: LLMTraceContext) -> None:
        self._inner = inner
        self.name = inner.name
        self._ctx = trace_context

    async def call(self, req: LLMRequest) -> LLMResponse:
        try:
            resp = await self._inner.call(req)
            self._ctx.record(
                {
                    "call_id": resp.call_id,
                    "model": resp.model,
                    "node_name": req.node_name,
                    "system_prompt": sanitize(req.system),
                    "system_prompt_hash": sha256_json({"s": req.system}),
                    "user_prompt": sanitize(req.user or ""),
                    "tools": [{"name": t.name} for t in req.tools],
                    "thinking": sanitize(resp.thinking or ""),
                    "response": sanitize(resp.text),
                    "tool_uses": [
                        {"id": tu.id, "name": tu.name, "input": sanitize(tu.input)}
                        for tu in resp.tool_uses
                    ],
                    "stop_reason": resp.stop_reason,
                    "tokens": {
                        "input": resp.usage.input_tokens,
                        "output": resp.usage.output_tokens,
                        "thinking": resp.usage.thinking_tokens,
                    },
                    "duration_ms": resp.duration_ms,
                    "error": None,
                }
            )
            return resp
        except Exception as e:
            self._ctx.record(
                {
                    "call_id": None,
                    "node_name": req.node_name,
                    "error": str(e),
                    "duration_ms": 0,
                }
            )
            raise
