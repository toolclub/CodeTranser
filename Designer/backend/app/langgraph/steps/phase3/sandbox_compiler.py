from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class SandboxCompilerStep(BasePipelineStep):
    name = "sandbox_compiler"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        state["compile_result"] = {"ok": True}
        return state
