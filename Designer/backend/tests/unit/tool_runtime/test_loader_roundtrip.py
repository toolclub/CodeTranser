import pytest

from app.domain.tool.tool import Engine, Scope
from app.models.mysql.node_template import NodeTemplateRow
from app.models.mysql.node_template_version import NodeTemplateVersionRow
from app.tool_runtime.loader import _row_to_tpl, to_anthropic_tool_spec


def test_row_to_tpl_joins_description() -> None:
    row = NodeTemplateRow(
        id="tpl_1",
        name="Foo",
        display_name="F",
        category="c",
        scope="global",
        status="active",
        created_by=0,
        current_version_id="tpv_1",
    )
    ver = NodeTemplateVersionRow(
        id="tpv_1",
        template_id="tpl_1",
        version_number=1,
        definition={
            "description": ["a", "b"],
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "simulator": {"engine": "llm"},
            "edge_semantics": [{"field": "next", "description": "d"}],
            "code_hints": {"style_hints": ["x"]},
            "extensions": {"k": "v"},
        },
        definition_hash="h",
        change_note="",
        created_by=0,
    )
    tpl = _row_to_tpl(row, ver)
    assert tpl.description == "a\nb"
    assert tpl.simulator.engine is Engine.LLM
    assert tpl.scope is Scope.GLOBAL
    assert tpl.edge_semantics[0].field == "next"
    assert tpl.extensions == {"k": "v"}

    spec = to_anthropic_tool_spec(tpl)
    assert spec["name"] == "Foo"
    assert spec["input_schema"] == {"type": "object"}
