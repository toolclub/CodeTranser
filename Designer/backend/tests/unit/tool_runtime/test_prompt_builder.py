import pytest
from jinja2 import UndefinedError

from app.domain.tool.tool import (
    CodeGenerationHints,
    EdgeSemantic,
    Engine,
    JsonSimulatorSpec,
    NodeTemplate,
    Scope,
)
from app.tool_runtime.prompt_builder import PromptBuilder


def _tpl(desc: str) -> NodeTemplate:
    return NodeTemplate(
        id="tpl_x",
        name="Foo",
        display_name="f",
        category="c",
        scope=Scope.GLOBAL,
        version=1,
        description=desc,
        input_schema={},
        output_schema={},
        simulator=JsonSimulatorSpec(engine=Engine.LLM, python_impl=None),
        edge_semantics=(EdgeSemantic("next"),),
        code_hints=CodeGenerationHints(),
        extensions={},
        definition_hash="h",
    )


def test_renders_fields() -> None:
    pb = (
        PromptBuilder(_tpl("max={{ fields.M }}"))
        .with_fields({"M": 16})
        .with_input({"k": 1})
    )
    out = pb.build()
    assert "max=16" in out.system
    assert '"input":' in out.user


def test_strict_undefined_raises() -> None:
    pb = PromptBuilder(_tpl("{{ fields.not_there }}")).with_fields({})
    with pytest.raises(UndefinedError):
        pb.build()
