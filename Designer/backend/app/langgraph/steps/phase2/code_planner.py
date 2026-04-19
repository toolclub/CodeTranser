from typing import Any

from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class CodePlannerStep(BasePipelineStep):
    """Ch08 会重写。骨架:给 state 一个空 code_skeleton。"""

    name = "code_planner"
    phase = 2

    async def _do(self, state: CascadeState) -> CascadeState:
        state["code_skeleton"] = state.get("code_skeleton") or {"modules": []}
        return state

    def _summary(self, state: CascadeState) -> dict[str, Any]:
        return {"modules": len((state.get("code_skeleton") or {}).get("modules", []))}
