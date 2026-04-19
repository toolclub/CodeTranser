import pytest

from app.config import Settings
from app.llm.adapters.mock import MockProvider, MockStep
from app.llm.client import LLMClient
from app.llm.types import LLMRequest


def _settings() -> Settings:
    return Settings(LLM_API_KEY="test", LLM_PROVIDER="mock", LLM_MAX_CONCURRENCY=5)


@pytest.mark.asyncio
async def test_client_uses_injected_provider() -> None:
    mp = MockProvider([MockStep(match={"any": True}, text="hello")])
    client = LLMClient(_settings(), provider=mp)
    resp = await client.call(LLMRequest(system="", user="x"))
    assert resp.text == "hello"


@pytest.mark.asyncio
async def test_client_coerces_json_output_when_schema_given() -> None:
    mp = MockProvider([MockStep(match={"any": True}, text='{"n": 42}')])
    client = LLMClient(_settings(), provider=mp)
    resp = await client.call(
        LLMRequest(
            system="",
            user="x",
            output_schema={
                "type": "object",
                "required": ["n"],
                "properties": {"n": {"type": "integer"}},
            },
        )
    )
    assert resp.parsed_json == {"n": 42}
