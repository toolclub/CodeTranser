from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class CodeAssemblerStep(BasePipelineStep):
    name = "code_assembler"
    phase = 2

    async def _do(self, state: CascadeState) -> CascadeState:
        state["composite_code"] = state.get("composite_code") or {"files": {}}
        return state
