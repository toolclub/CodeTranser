from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class Scenario:
    """Phase1 Handler 2 消费的最小单元:一次"输入 → 期望输出"的整森林跑动预期。"""

    scenario_id: str
    name: str
    input_json: Mapping[str, Any]
    expected_output: Mapping[str, Any]
    tables: Mapping[str, list[Any]] = field(default_factory=dict)
    description: str = ""
    target_root: str | None = None


@dataclass(slots=True)
class ScenarioResult:
    scenario_id: str
    actual_output: Any
    match: bool
    mismatch_detail: dict[str, Any] | None = None
    node_outputs: dict[str, Any] = field(default_factory=dict)
    tool_call_count: int = 0
    llm_call_count: int = 0
    duration_ms: int = 0
    attribution: str | None = None
    attribution_reason: str | None = None
    agent_stopped_reason: str = ""
    error: str | None = None
