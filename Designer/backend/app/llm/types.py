import json
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolUseRequest:
    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolUseResult:
    tool_use_id: str
    content: str
    is_error: bool = False


Role = Literal["system", "user", "assistant", "tool_result"]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    text: str | None = None
    tool_uses: tuple[ToolUseRequest, ...] = ()
    tool_results: tuple[ToolUseResult, ...] = ()


@dataclass(frozen=True, slots=True)
class LLMRequest:
    system: str
    messages: tuple[Message, ...] = ()
    user: str | None = None
    tools: tuple[ToolSpec, ...] = ()
    model: str | None = None
    temperature: float = 0.0
    max_tokens: int = 4096
    output_schema: dict[str, Any] | None = None
    node_name: str = "unknown"
    timeout_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0


@dataclass(slots=True)
class LLMResponse:
    call_id: str
    model: str
    text: str
    tool_uses: tuple[ToolUseRequest, ...]
    stop_reason: Literal["end_turn", "max_tokens", "tool_use", "stop_sequence", "error"]
    usage: LLMUsage
    thinking: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    @property
    def parsed_json(self) -> dict[str, Any]:
        """在 output_schema 模式下,`text` 应为 JSON。"""
        return json.loads(self.text)
