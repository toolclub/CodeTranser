import pytest

from app.llm.adapters.mock import MockProvider, MockStep
from app.llm.agent_loop import run_agent_loop
from app.llm.types import ToolSpec, ToolUseRequest, ToolUseResult


@pytest.mark.asyncio
async def test_end_turn_immediately() -> None:
    p = MockProvider([MockStep(match={"any": True}, text="done", stop_reason="end_turn")])

    async def exec_(tu: ToolUseRequest) -> ToolUseResult:
        raise AssertionError("should not be called")

    r = await run_agent_loop(
        provider=p,
        system="",
        initial_user="hi",
        tools=[],
        tool_executor=exec_,
        max_iterations=5,
    )
    assert r.stopped_reason == "end_turn"
    assert r.final_text == "done"


@pytest.mark.asyncio
async def test_tool_use_then_end_turn() -> None:
    p = MockProvider(
        [
            MockStep(
                match={"any": True},
                stop_reason="tool_use",
                tool_uses=[{"name": "add", "input": {"a": 1, "b": 2}}],
            ),
            MockStep(match={"any": True}, text="answer=3", stop_reason="end_turn"),
        ]
    )

    async def exec_(tu: ToolUseRequest) -> ToolUseResult:
        assert tu.name == "add"
        return ToolUseResult(tool_use_id=tu.id, content="3")

    r = await run_agent_loop(
        provider=p,
        system="",
        initial_user="hi",
        tools=[ToolSpec(name="add", description="", input_schema={})],
        tool_executor=exec_,
        max_iterations=5,
    )
    assert r.stopped_reason == "end_turn"
    assert r.tool_call_count == 1
    assert r.final_text == "answer=3"


@pytest.mark.asyncio
async def test_max_iterations() -> None:
    p = MockProvider(
        [
            MockStep(
                match={"any": True},
                stop_reason="tool_use",
                tool_uses=[{"name": "x", "input": {}}],
            )
        ]
        * 10
    )

    async def exec_(tu: ToolUseRequest) -> ToolUseResult:
        return ToolUseResult(tool_use_id=tu.id, content="ok")

    r = await run_agent_loop(
        provider=p,
        system="",
        initial_user="hi",
        tools=[ToolSpec(name="x", description="", input_schema={})],
        tool_executor=exec_,
        max_iterations=3,
    )
    assert r.stopped_reason == "max_iterations"
    assert r.tool_call_count == 3
