from dataclasses import dataclass, field
from typing import Protocol

from app.llm.provider import LLMProvider
from app.llm.types import (
    LLMRequest,
    LLMResponse,
    Message,
    ToolSpec,
    ToolUseRequest,
    ToolUseResult,
)


class ToolExecutor(Protocol):
    """调用方提供的工具执行器。Ch07 Handler 2 里把 ToolUseRequest 路由到对应 ToolSimulator。"""

    async def __call__(self, req: ToolUseRequest) -> ToolUseResult: ...


@dataclass
class AgentStep:
    iteration: int
    request: LLMRequest
    response: LLMResponse
    tool_results: list[ToolUseResult] = field(default_factory=list)


@dataclass
class AgentResult:
    steps: list[AgentStep]
    final_text: str
    tool_call_count: int
    stopped_reason: str  # "end_turn" / "max_iterations" / "error"


async def run_agent_loop(
    *,
    provider: LLMProvider,
    system: str,
    initial_user: str,
    tools: list[ToolSpec],
    tool_executor: ToolExecutor,
    max_iterations: int = 20,
    model: str | None = None,
    temperature: float = 0.0,
    node_name: str = "agent_loop",
) -> AgentResult:
    messages: list[Message] = [Message(role="user", text=initial_user)]
    steps: list[AgentStep] = []
    tool_calls_total = 0

    for i in range(max_iterations):
        req = LLMRequest(
            system=system,
            messages=tuple(messages),
            tools=tuple(tools),
            model=model,
            temperature=temperature,
            node_name=f"{node_name}#{i}",
        )
        resp = await provider.call(req)
        messages.append(
            Message(role="assistant", text=resp.text, tool_uses=resp.tool_uses)
        )

        step = AgentStep(iteration=i, request=req, response=resp)

        if resp.stop_reason == "end_turn":
            steps.append(step)
            return AgentResult(
                steps=steps,
                final_text=resp.text,
                tool_call_count=tool_calls_total,
                stopped_reason="end_turn",
            )

        if resp.stop_reason != "tool_use" or not resp.tool_uses:
            steps.append(step)
            return AgentResult(
                steps=steps,
                final_text=resp.text,
                tool_call_count=tool_calls_total,
                stopped_reason="error",
            )

        results: list[ToolUseResult] = []
        for tu in resp.tool_uses:
            try:
                r = await tool_executor(tu)
            except Exception as e:
                r = ToolUseResult(
                    tool_use_id=tu.id,
                    content=f"executor error: {e}",
                    is_error=True,
                )
            results.append(r)
            tool_calls_total += 1
        step.tool_results = results
        steps.append(step)
        messages.append(Message(role="tool_result", tool_results=tuple(results)))

    return AgentResult(
        steps=steps,
        final_text="",
        tool_call_count=tool_calls_total,
        stopped_reason="max_iterations",
    )
