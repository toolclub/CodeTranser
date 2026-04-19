import pytest

from app.llm.adapters.mock import MockProvider, MockStep
from app.llm.errors import LLMSchemaError
from app.llm.schema_coerce import coerce_json_output
from app.llm.types import LLMRequest

_SCHEMA = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}


@pytest.mark.asyncio
async def test_first_shot_ok() -> None:
    p = MockProvider([MockStep(match={"any": True}, text='{"a": 1}')])
    req = LLMRequest(system="", user="x", output_schema=_SCHEMA)
    resp = await coerce_json_output(p, req)
    assert resp.parsed_json == {"a": 1}


@pytest.mark.asyncio
async def test_handles_code_fence() -> None:
    p = MockProvider([MockStep(match={"any": True}, text='```json\n{"a": 2}\n```')])
    req = LLMRequest(system="", user="x", output_schema=_SCHEMA)
    resp = await coerce_json_output(p, req)
    assert resp.parsed_json == {"a": 2}


@pytest.mark.asyncio
async def test_fix_on_second_shot() -> None:
    p = MockProvider(
        [
            MockStep(match={"any": True}, text="not json"),
            MockStep(match={"any": True}, text='{"a": 5}'),
        ]
    )
    req = LLMRequest(system="", user="x", output_schema=_SCHEMA)
    resp = await coerce_json_output(p, req)
    assert resp.parsed_json == {"a": 5}


@pytest.mark.asyncio
async def test_gives_up_after_two() -> None:
    p = MockProvider(
        [
            MockStep(match={"any": True}, text="not json"),
            MockStep(match={"any": True}, text="still not"),
        ]
    )
    req = LLMRequest(system="", user="x", output_schema=_SCHEMA)
    with pytest.raises(LLMSchemaError):
        await coerce_json_output(p, req)
