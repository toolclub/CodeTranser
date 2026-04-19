import json
from functools import lru_cache
from typing import Any

from jsonschema.validators import Draft202012Validator

from app.tool_runtime.errors import (
    SimulatorInputInvalid,
    SimulatorOutputInvalid,
    TemplateDefinitionInvalid,
)


def _key(schema: dict[str, Any]) -> str:
    return json.dumps(schema, sort_keys=True, ensure_ascii=False)


@lru_cache(maxsize=512)
def _compile(schema_json: str) -> Draft202012Validator:
    schema = json.loads(schema_json)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_schema_self(schema: dict[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as e:
        raise TemplateDefinitionInvalid(str(e)) from e


def validate_input(input_schema: dict[str, Any], data: Any) -> None:
    v = _compile(_key(input_schema))
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if errs:
        raise SimulatorInputInvalid("; ".join(e.message for e in errs))


def validate_output(output_schema: dict[str, Any], data: Any) -> None:
    v = _compile(_key(output_schema))
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if errs:
        raise SimulatorOutputInvalid("; ".join(e.message for e in errs))
