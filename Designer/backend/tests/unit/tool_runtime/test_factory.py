import pytest

from app.domain.tool.tool import (
    CodeGenerationHints,
    EdgeSemantic,
    Engine,
    JsonSimulatorSpec,
    NodeTemplate,
    Scope,
)
from app.tool_runtime.errors import SimulatorNotRegistered
from app.tool_runtime.factory import SimulatorFactory
from app.tool_runtime.simulators.hybrid import HybridSimulator
from app.tool_runtime.simulators.llm_generic import LLMSimulator
from app.tool_runtime.simulators.pure_python.index_table_lookup import IndexTableLookupSim


def _tpl(engine: Engine, python_impl: str | None, llm_fallback: bool = False) -> NodeTemplate:
    return NodeTemplate(
        id="tpl_x",
        name="IndexTableLookup",
        display_name="t",
        category="c",
        scope=Scope.GLOBAL,
        version=1,
        description="",
        input_schema={},
        output_schema={},
        simulator=JsonSimulatorSpec(
            engine=engine, python_impl=python_impl, llm_fallback=llm_fallback
        ),
        edge_semantics=(EdgeSemantic("next"),),
        code_hints=CodeGenerationHints(),
        extensions={},
        definition_hash="h",
    )


def test_factory_pure_python_routes_to_registered_class() -> None:
    f = SimulatorFactory()
    sim = f.create(_tpl(Engine.PURE_PYTHON, "IndexTableLookup"))
    assert isinstance(sim, IndexTableLookupSim)


def test_factory_llm_routes_to_llm_simulator() -> None:
    f = SimulatorFactory()
    sim = f.create(_tpl(Engine.LLM, None))
    assert isinstance(sim, LLMSimulator)


def test_factory_hybrid_wraps() -> None:
    f = SimulatorFactory()
    sim = f.create(_tpl(Engine.HYBRID, "IndexTableLookup", llm_fallback=True))
    assert isinstance(sim, HybridSimulator)


def test_factory_missing_pure_python_impl_raises() -> None:
    f = SimulatorFactory()
    with pytest.raises(SimulatorNotRegistered):
        f.create(_tpl(Engine.PURE_PYTHON, "NonExistent"))


def test_factory_hybrid_without_any_impl_raises() -> None:
    f = SimulatorFactory()
    with pytest.raises(SimulatorNotRegistered):
        f.create(_tpl(Engine.HYBRID, None, llm_fallback=False))
