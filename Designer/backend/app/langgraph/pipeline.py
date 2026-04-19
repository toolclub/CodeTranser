from enum import Enum
from typing import Any

from langgraph.graph import END, StateGraph

from app.langgraph.state import CascadeState
from app.langgraph.steps.factory import PipelineStepFactory


class PipelineVariant(str, Enum):
    PHASE1_ONLY = "phase1_only"
    UP_TO_PHASE2 = "up_to_phase2"
    FULL = "full"


class PipelineBuilder:
    """按 PipelineVariant 装配 StateGraph 并缓存。

    分布式:接受可选 `checkpointer`(`MemorySaver` / `AsyncRedisSaver` / ...);
    所有 variant 共用同一个 checkpointer 实例。
    """

    def __init__(
        self,
        factory: PipelineStepFactory,
        router: "PhaseRouter",
        *,
        checkpointer: Any | None = None,
    ) -> None:
        self._f = factory
        self._r = router
        self._checkpointer = checkpointer
        self._cache: dict[PipelineVariant, Any] = {}

    def get(self, variant: PipelineVariant) -> Any:
        if variant not in self._cache:
            self._cache[variant] = self._build(variant)
        return self._cache[variant]

    def _compile(self, g: "StateGraph") -> Any:
        if self._checkpointer is not None:
            return g.compile(checkpointer=self._checkpointer)
        return g.compile()

    def _build(self, variant: PipelineVariant) -> Any:
        g = StateGraph(CascadeState)

        # Phase1 finalize 节点(所有 variant 都挂;未被引用的 LangGraph 允许存在)
        g.add_node("_phase1_end_valid", self._f.make("_phase1_end_valid").execute)
        g.add_node("_phase1_end_invalid", self._f.make("_phase1_end_invalid").execute)
        g.add_edge("_phase1_end_valid", END)
        g.add_edge("_phase1_end_invalid", END)

        handlers = self._r.phase1_order()
        if handlers:
            for name in handlers:
                g.add_node(name, self._f.make(name).execute)
            g.set_entry_point(handlers[0])
            for name in handlers:
                g.add_conditional_edges(
                    name, self._r.after_phase1_handler(name, variant=variant)
                )
        else:
            # 无 handler:直接进 finalize
            if variant is PipelineVariant.PHASE1_ONLY:
                g.set_entry_point("_phase1_end_valid")
            else:
                g.add_node("_phase1_bridge", self._f.make("_phase1_bridge").execute)
                g.set_entry_point("_phase1_bridge")

        if variant is PipelineVariant.PHASE1_ONLY:
            return self._compile(g)

        # 进入 Phase2 前的过渡(有 handler 时才需要)
        if handlers:
            g.add_node("_phase1_bridge", self._f.make("_phase1_bridge").execute)
        g.add_edge("_phase1_bridge", "code_planner")

        # Phase2
        g.add_node("code_planner", self._f.make("code_planner").execute)
        g.add_node("code_generator", self._f.make("code_generator").execute)
        g.add_node("code_assembler", self._f.make("code_assembler").execute)
        g.add_edge("code_planner", "code_generator")
        g.add_edge("code_generator", "code_assembler")

        if variant is PipelineVariant.UP_TO_PHASE2:
            g.add_node("_phase2_end_valid", self._f.make("_phase2_end_valid").execute)
            g.add_edge("_phase2_end_valid", END)
            g.add_conditional_edges(
                "code_assembler", self._r.after_code_assembler(variant=variant)
            )
            return self._compile(g)

        # Phase3
        g.add_node("outer_static_reflector", self._f.make("outer_static_reflector").execute)
        g.add_node("sandbox_compiler", self._f.make("sandbox_compiler").execute)
        g.add_node(
            "outer_scenario_synthesizer",
            self._f.make("outer_scenario_synthesizer").execute,
        )
        g.add_node("sandbox_executor", self._f.make("sandbox_executor").execute)
        g.add_node(
            "outer_dynamic_reflector", self._f.make("outer_dynamic_reflector").execute
        )

        g.add_node("_phase3_end_valid", self._f.make("_phase3_end_valid").execute)
        g.add_node("_phase3_end_invalid", self._f.make("_phase3_end_invalid").execute)
        g.add_node(
            "_phase3_end_inconclusive",
            self._f.make("_phase3_end_inconclusive").execute,
        )
        g.add_edge("_phase3_end_valid", END)
        g.add_edge("_phase3_end_invalid", END)
        g.add_edge("_phase3_end_inconclusive", END)

        g.add_conditional_edges(
            "code_assembler", self._r.after_code_assembler(variant=variant)
        )
        g.add_conditional_edges("outer_static_reflector", self._r.after_outer_static())
        g.add_conditional_edges(
            "sandbox_compiler", self._r.after_sandbox_compiler()
        )
        g.add_edge("outer_scenario_synthesizer", "sandbox_executor")
        g.add_edge("sandbox_executor", "outer_dynamic_reflector")
        g.add_conditional_edges(
            "outer_dynamic_reflector", self._r.after_outer_dynamic()
        )
        return g.compile()


from app.langgraph.router import PhaseRouter  # noqa: E402
