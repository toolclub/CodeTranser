from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.langgraph.events import RunEventBus
from app.langgraph.run_step_store import RunStepStore
from app.langgraph.steps import STEP_REGISTRY
from app.langgraph.steps.base import BasePipelineStep, HandlerStep
from app.langgraph.trace_sink import ToolCallTraceContext, TraceSink
from app.llm.decorators.trace import LLMTraceContext


@dataclass(slots=True)
class StepDeps:
    """StepFactory 的全量依赖袋。"""

    event_bus: RunEventBus
    trace_sink: TraceSink
    tool_trace_ctx: ToolCallTraceContext
    llm_trace_ctx: LLMTraceContext
    run_step_store: RunStepStore
    settings: Settings

    # 由 Ch03/04 提供的运行时依赖(可 None,但 depends_on 声明了就必须有)
    llm_client: Any | None = None
    tool_registry: Any | None = None
    design_validator: Any | None = None
    forest_parser: Any | None = None

    def kwargs_for(self, cls: type[BasePipelineStep]) -> dict[str, Any]:
        base: dict[str, Any] = dict(
            event_bus=self.event_bus,
            trace_sink=self.trace_sink,
            llm_trace_ctx=self.llm_trace_ctx,
            tool_trace_ctx=self.tool_trace_ctx,
            run_step_store=self.run_step_store,
        )
        extra: dict[str, Any] = {}
        for dep in getattr(cls, "depends_on", ()):
            if dep == "llm":
                extra["llm"] = self.llm_client
            elif dep == "tool_registry":
                extra["tool_registry"] = self.tool_registry
            elif dep == "design_validator":
                extra["design_validator"] = self.design_validator
            elif dep == "forest_parser":
                extra["forest_parser"] = self.forest_parser
            elif dep == "settings":
                extra["settings"] = self.settings
            else:
                raise ValueError(f"unknown dep {dep!r} for {cls.__name__}")
        return {**base, **extra}


class PipelineStepFactory:
    def __init__(self, deps: StepDeps) -> None:
        self._deps = deps

    def make(self, step_name: str) -> BasePipelineStep:
        cls = STEP_REGISTRY.get(step_name)
        if cls is None:
            raise KeyError(f"unknown step {step_name}")
        return cls(**self._deps.kwargs_for(cls))

    def list_phase(self, phase: int) -> list[type[BasePipelineStep]]:
        return [c for c in STEP_REGISTRY.values() if c.phase == phase]

    def list_phase1_handlers(self) -> list[type[HandlerStep]]:
        hs = [c for c in STEP_REGISTRY.values() if issubclass(c, HandlerStep)]
        return sorted(hs, key=lambda c: c.handler_order)
