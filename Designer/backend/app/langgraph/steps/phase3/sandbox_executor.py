from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class SandboxExecutorStep(BasePipelineStep):
    name = "sandbox_executor"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        state["execution_results"] = []
        return state
