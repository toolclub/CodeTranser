import pytest

from app.tool_runtime.errors import TemplateDefinitionInvalid
from app.tool_runtime.json_parser import join_description, parse_definition


def _def(**overrides: object) -> dict:
    base = {
        "description": ["line1"],
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "simulator": {"engine": "llm", "python_impl": None, "llm_fallback": False},
        "edge_semantics": [],
        "code_hints": {},
        "extensions": {},
    }
    base.update(overrides)
    return base


def test_parse_valid() -> None:
    dto = parse_definition(_def())
    assert dto.simulator.engine == "llm"


def test_parse_bad_schema_raises() -> None:
    with pytest.raises(TemplateDefinitionInvalid):
        parse_definition(_def(input_schema={"type": "not_a_real_type"}))


def test_join_description() -> None:
    assert join_description(["a", "b"]) == "a\nb"
