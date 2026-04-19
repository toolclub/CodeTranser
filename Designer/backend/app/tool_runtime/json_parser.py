from typing import Any

from app.schemas.tool import NodeTemplateDefinitionDTO
from app.tool_runtime.errors import TemplateDefinitionInvalid
from app.tool_runtime.json_schema import validate_schema_self


def parse_definition(raw: dict[str, Any]) -> NodeTemplateDefinitionDTO:
    try:
        dto = NodeTemplateDefinitionDTO.model_validate(raw)
    except Exception as e:
        raise TemplateDefinitionInvalid(str(e)) from e
    validate_schema_self(dto.input_schema)
    validate_schema_self(dto.output_schema)
    return dto


def join_description(description: list[str]) -> str:
    """description 以 list[str] 进 DB;值对象里是 "\n".join 后的单串。"""
    return "\n".join(description)
