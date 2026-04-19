from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class CodeGeneratorStep(BasePipelineStep):
    name = "code_generator"
    phase = 2

    async def _do(self, state: CascadeState) -> CascadeState:
        state["code_units"] = state.get("code_units") or []
        return state
