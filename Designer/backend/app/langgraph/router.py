"""纯 Router:只读 state 决定下一步;state 变更由 step 负责(见 phase_end.py)。"""

from typing import Any, Callable

from app.config import Settings
from app.langgraph.state import CascadeState
from app.langgraph.steps.factory import PipelineStepFactory


class PhaseRouter:
    def __init__(self, factory: PipelineStepFactory, settings: Settings) -> None:
        self._f = factory
        self._s = settings

    def phase1_order(self) -> list[str]:
        return [c.name for c in self._f.list_phase1_handlers()]

    def after_phase1_handler(
        self, current: str, *, variant: Any = None
    ) -> Callable[[CascadeState], str]:
        from app.langgraph.pipeline import PipelineVariant

        order = self.phase1_order()

        def _route(state: CascadeState) -> str:
            if state.get("decision") == "handler_fail":
                return "_phase1_end_invalid"
            idx = order.index(current)
            if idx + 1 < len(order):
                return order[idx + 1]
            # 最后一个 handler pass
            if variant is PipelineVariant.PHASE1_ONLY:
                return "_phase1_end_valid"
            return "_phase1_bridge"

        return _route

    def after_code_assembler(
        self, *, variant: Any = None
    ) -> Callable[[CascadeState], str]:
        from app.langgraph.pipeline import PipelineVariant

        def _route(state: CascadeState) -> str:
            if variant is PipelineVariant.UP_TO_PHASE2:
                return "_phase2_end_valid"
            return "outer_static_reflector"

        return _route

    def after_outer_static(self) -> Callable[[CascadeState], str]:
        def _route(state: CascadeState) -> str:
            if state.get("static_issues"):
                return "code_generator"
            return "sandbox_compiler"

        return _route

    def after_sandbox_compiler(self) -> Callable[[CascadeState], str]:
        max_fix = self._s.OUTER_FIX_MAX

        def _route(state: CascadeState) -> str:
            cr = state.get("compile_result") or {}
            if not cr.get("ok"):
                if state.get("outer_fix_iter", 0) + 1 >= max_fix:
                    return "_phase3_end_inconclusive"
                return "code_generator"
            return "outer_scenario_synthesizer"

        return _route

    def after_outer_dynamic(self) -> Callable[[CascadeState], str]:
        max_fix = self._s.OUTER_FIX_MAX

        def _route(state: CascadeState) -> str:
            d = state.get("decision")
            if d == "done":
                return "_phase3_end_valid"
            if d == "design_bug":
                return "_phase3_end_invalid"
            if d == "fix_code":
                if state.get("outer_fix_iter", 0) + 1 >= max_fix:
                    return "_phase3_end_inconclusive"
                return "code_generator"
            return "_phase3_end_valid"

        return _route
