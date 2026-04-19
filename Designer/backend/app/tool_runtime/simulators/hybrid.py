from time import perf_counter_ns
from typing import Any

from app.domain.run.sim import SimContext, SimResult
from app.domain.tool.tool import Engine
from app.tool_runtime.base import ToolSimulator


class HybridSimulator(ToolSimulator):
    """primary 抛或返回 error 时,若有 fallback 则切到 fallback。"""

    engine = Engine.HYBRID

    def __init__(self, primary: ToolSimulator, fallback: ToolSimulator | None) -> None:
        self._primary = primary
        self._fallback = fallback
        self.tool_name = primary.tool_name  # type: ignore[misc]

    def run(
        self,
        fields: dict[str, Any],
        input_json: dict[str, Any],
        ctx: SimContext,
    ) -> SimResult:
        t0 = perf_counter_ns()
        try:
            r = self._primary.run(fields, input_json, ctx)
            if r.error is None:
                return r
        except Exception:
            if self._fallback is None:
                raise
        if self._fallback is None:
            # primary 跑完有 error 且无 fallback → 原样返回
            return self._primary.run(fields, input_json, ctx)
        r = self._fallback.run(fields, input_json, ctx)
        r.duration_ms = (perf_counter_ns() - t0) // 1_000_000
        return r
