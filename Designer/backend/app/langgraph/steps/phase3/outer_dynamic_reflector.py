from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class OuterDynamicReflectorStep(BasePipelineStep):
    name = "outer_dynamic_reflector"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        state["decision"] = "done"
        return state
