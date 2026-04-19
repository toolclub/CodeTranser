import pytest
from pydantic import ValidationError

from app.schemas.tool import (
    CodeHintsDTO,
    JsonSimulatorDTO,
    NodeTemplateCreateDTO,
    NodeTemplateDefinitionDTO,
)


def _definition() -> NodeTemplateDefinitionDTO:
    return NodeTemplateDefinitionDTO(
        description=["line1"],
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        simulator=JsonSimulatorDTO(engine="pure_python", python_impl="Foo"),
        edge_semantics=[],
        code_hints=CodeHintsDTO(),
        extensions={"arbitrary": {"a": 1}},
    )


def test_create_dto_name_must_match_pattern() -> None:
    with pytest.raises(ValidationError):
        NodeTemplateCreateDTO(
            name="lowercase_start",  # 违反 ^[A-Z]...
            display_name="L",
            category="c",
            scope="global",
            definition=_definition(),
        )


def test_create_dto_accepts_valid_name_and_extensions() -> None:
    dto = NodeTemplateCreateDTO(
        name="Foo_Bar",
        display_name="Foo",
        category="c",
        scope="global",
        definition=_definition(),
    )
    assert dto.definition.extensions == {"arbitrary": {"a": 1}}
