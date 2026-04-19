import pytest

from app.domain.tool.tool import (
    CodeGenerationHints,
    EdgeSemantic,
    Engine,
    JsonSimulatorSpec,
    NodeTemplate,
    Scope,
)


def _build(
    scope: Scope = Scope.GLOBAL,
    engine: Engine = Engine.PURE_PYTHON,
    python_impl: str | None = "Foo",
) -> NodeTemplate:
    return NodeTemplate(
        id="tpl_00000001",
        name="Foo",
        display_name="Foo",
        category="util",
        scope=scope,
        version=1,
        description="x",
        input_schema={},
        output_schema={},
        simulator=JsonSimulatorSpec(engine=engine, python_impl=python_impl),
        edge_semantics=(EdgeSemantic("next"),),
        code_hints=CodeGenerationHints(),
        extensions={},
        definition_hash="deadbeef",
    )


def test_global_pure_python_ok() -> None:
    tpl = _build(scope=Scope.GLOBAL, engine=Engine.PURE_PYTHON)
    assert tpl.simulator.engine is Engine.PURE_PYTHON


def test_private_must_be_llm() -> None:
    with pytest.raises(ValueError):
        _build(scope=Scope.PRIVATE, engine=Engine.PURE_PYTHON)


def test_private_llm_ok() -> None:
    tpl = _build(scope=Scope.PRIVATE, engine=Engine.LLM, python_impl=None)
    assert tpl.scope is Scope.PRIVATE
