from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class OuterStaticReflectorStep(BasePipelineStep):
    name = "outer_static_reflector"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        state["static_issues"] = []
        return state
