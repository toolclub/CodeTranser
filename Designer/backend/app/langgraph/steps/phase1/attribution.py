import json
from typing import Any

from app.llm.client import LLMClient
from app.llm.types import LLMRequest

_SYSTEM = """\
你是设计审查助理。下面给你一次森林执行的完整轨迹(工具调用链 + 每步输出) + 预期输出 + 实际输出。
请用一个 JSON 告诉我失败归因:

{
  "attribution": "design_bug" | "scenario_bug" | "simulator_bug" | "unknown",
  "reason": "一两句中文说明",
  "offending_instances": ["n_xxx"]
}

- design_bug:森林/节点配置错(最常见)
- scenario_bug:expected 不合理
- simulator_bug:解释器 bug(罕见)
- unknown:拿不准
仅回 JSON,无其他文字。
"""

_OUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["attribution", "reason"],
    "properties": {
        "attribution": {
            "type": "string",
            "enum": ["design_bug", "scenario_bug", "simulator_bug", "unknown"],
        },
        "reason": {"type": "string"},
        "offending_instances": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}


async def attribute_failure(
    *,
    llm: LLMClient,
    scenario: dict[str, Any],
    actual: Any,
    diff: list[dict[str, Any]],
    tool_call_trace: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "scenario_name": scenario["name"],
        "input_json": scenario["input_json"],
        "expected_output": scenario["expected_output"],
        "actual_output": actual,
        "diff": diff,
        "tool_calls": [
            {
                "instance_id": tc.get("instance_id"),
                "template": tc.get("template_name"),
                "bundle": tc.get("bundle_id"),
                "input": tc.get("input_json"),
                "output": tc.get("output_json"),
            }
            for tc in tool_call_trace
        ],
    }
    try:
        resp = await llm.call(
            LLMRequest(
                system=_SYSTEM,
                user=json.dumps(summary, ensure_ascii=False, indent=2),
                output_schema=_OUT_SCHEMA,
                node_name=f"attribute:{run_id}",
                temperature=0.0,
                max_tokens=512,
            )
        )
        return resp.parsed_json
    except Exception as e:
        return {
            "attribution": "unknown",
            "reason": f"llm_failed: {e}",
            "offending_instances": [],
        }
