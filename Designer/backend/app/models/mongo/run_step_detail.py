from datetime import datetime
from typing import Any, Literal, Optional, TypedDict


class ToolCallRecord(TypedDict, total=False):
    """Phase1 Handler 2 里每次调 ToolSimulator 的记录。"""

    template_name: str
    template_version: int
    definition_hash: str
    engine: Literal["pure_python", "llm", "hybrid"]
    instance_id: str
    bundle_id: Optional[str]
    field_values: dict[str, Any]
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    duration_ms: int
    error: Optional[str]
    llm_fallback_used: bool
    llm_call_ref: Optional[str]


class LLMCallRecord(TypedDict, total=False):
    call_id: str
    model: str
    system_prompt: str
    user_prompt: str
    thinking: Optional[str]
    response: str
    tool_uses: list[dict[str, Any]]
    tokens: dict[str, Any]
    duration_ms: int
    error: Optional[str]
    system_prompt_hash: str


class RunStepDetail(TypedDict, total=False):
    _id: Any
    run_id: str
    step_id: str
    phase: Literal[1, 2, 3]
    node_name: str
    iteration: int
    handler_name: Optional[str]
    input_state: dict[str, Any]
    output_state: dict[str, Any]
    tool_calls: list[ToolCallRecord]
    llm_calls: list[LLMCallRecord]
    decision: Optional[str]
    decision_reason: Optional[str]
    status: Literal["success", "failed"]
    error: Optional[str]
    schema_version: int
    created_at: datetime
