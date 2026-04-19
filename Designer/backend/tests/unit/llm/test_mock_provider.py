import pytest

from app.llm.adapters.mock import MockProvider, MockStep
from app.llm.types import LLMRequest


@pytest.mark.asyncio
async def test_mock_match_and_pop() -> None:
    mp = MockProvider(
        [
            MockStep(match={"user_contains": "hello"}, text="hi"),
            MockStep(match={"any": True}, text="default"),
        ]
    )
    r1 = await mp.call(LLMRequest(system="", user="hello world"))
    assert r1.text == "hi"
    r2 = await mp.call(LLMRequest(system="", user="whatever"))
    assert r2.text == "default"


@pytest.mark.asyncio
async def test_mock_no_match_raises() -> None:
    mp = MockProvider([MockStep(match={"user_contains": "nope"}, text="x")])
    with pytest.raises(AssertionError):
        await mp.call(LLMRequest(system="", user="yes"))
