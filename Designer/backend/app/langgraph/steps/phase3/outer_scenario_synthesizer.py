from app.langgraph.state import CascadeState
from app.langgraph.steps.base import BasePipelineStep


class OuterScenarioSynthesizerStep(BasePipelineStep):
    name = "outer_scenario_synthesizer"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        state["sandbox_cases"] = state.get("sandbox_cases") or []
        return state
