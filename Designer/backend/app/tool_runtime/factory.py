from app.domain.tool.tool import Engine, NodeTemplate
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.errors import SimulatorNotRegistered
from app.tool_runtime.simulators import SIMULATOR_REGISTRY
from app.tool_runtime.simulators.hybrid import HybridSimulator
from app.tool_runtime.simulators.llm_generic import LLMSimulator


class SimulatorFactory:
    """按 NodeTemplate.simulator.engine 路由到对应实现。"""

    def create(self, tpl: NodeTemplate) -> ToolSimulator:
        eng = tpl.simulator.engine
        if eng is Engine.PURE_PYTHON:
            return self._pure(tpl)
        if eng is Engine.LLM:
            return LLMSimulator(tpl)
        if eng is Engine.HYBRID:
            primary = self._pure(tpl) if tpl.simulator.python_impl else None
            fallback = LLMSimulator(tpl) if tpl.simulator.llm_fallback else None
            if primary is None and fallback is None:
                raise SimulatorNotRegistered(
                    f"hybrid template {tpl.name} has neither primary nor fallback"
                )
            if primary is None:
                assert fallback is not None
                return fallback
            return HybridSimulator(primary, fallback)
        raise ValueError(f"unknown engine {eng}")

    def _pure(self, tpl: NodeTemplate) -> ToolSimulator:
        impl_name = tpl.simulator.python_impl or tpl.name
        cls = SIMULATOR_REGISTRY.get(impl_name)
        if cls is None:
            raise SimulatorNotRegistered(f"no python simulator for template {impl_name}")
        return cls()
