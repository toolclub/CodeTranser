"""Finalize 节点:在 END 之前做 state 变更(设 final_verdict / phase1_verdict ...)。

LangGraph 的 `conditional_edges` 里对 state 的变更不一定持久化,因此把收尾动作集中在这些
step 里——step 执行后 LangGraph 会合并返回的 state。
"""

from typing import Any

from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class _Phase1EndValid(BasePipelineStep):
    name = "_phase1_end_valid"
    phase = 1

    async def _do(self, state: CascadeState) -> CascadeState:
        state["phase1_verdict"] = "valid"
        state["final_verdict"] = "valid"
        state["decision"] = "done"
        return state


class _Phase1EndInvalid(BasePipelineStep):
    name = "_phase1_end_invalid"
    phase = 1

    async def _do(self, state: CascadeState) -> CascadeState:
        state["phase1_verdict"] = "invalid"
        state["final_verdict"] = "invalid"
        return state


class _Phase1Bridge(BasePipelineStep):
    """Phase1 pass 后、进入 Phase2 之前的过渡节点(设 phase1_verdict=valid)。"""

    name = "_phase1_bridge"
    phase = 1

    async def _do(self, state: CascadeState) -> CascadeState:
        state["phase1_verdict"] = "valid"
        state["decision"] = "done"
        return state


class _Phase2EndValid(BasePipelineStep):
    name = "_phase2_end_valid"
    phase = 2

    async def _do(self, state: CascadeState) -> CascadeState:
        state["final_verdict"] = "valid"
        return state


class _Phase3EndValid(BasePipelineStep):
    name = "_phase3_end_valid"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        state["phase3_verdict"] = "done"
        state["final_verdict"] = "valid"
        return state


class _Phase3EndInvalid(BasePipelineStep):
    name = "_phase3_end_invalid"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        state["phase3_verdict"] = "design_bug"
        state["final_verdict"] = "invalid"
        return state


class _Phase3EndInconclusive(BasePipelineStep):
    name = "_phase3_end_inconclusive"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        state["phase3_verdict"] = state.get("phase3_verdict") or "fix_exhausted"
        state["final_verdict"] = "inconclusive"
        return state
