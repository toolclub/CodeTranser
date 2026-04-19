import json
from typing import Any

from app.llm.errors import LLMSchemaError
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse, Message
from app.tool_runtime.errors import SimulatorOutputInvalid
from app.tool_runtime.json_schema import validate_output


async def coerce_json_output(provider: LLMProvider, req: LLMRequest) -> LLMResponse:
    """确保 response.text 是合法 JSON 且符合 output_schema。

    - 若第一次失败,给一次修复重试(把失败原因塞回 user 让 LLM 自修)
    - 再失败 → LLMSchemaError
    """
    if req.output_schema is None:
        return await provider.call(req)

    resp = await provider.call(req)
    parsed, err = _try_parse_and_validate(resp.text, req.output_schema)
    if parsed is not None:
        resp.text = json.dumps(parsed, ensure_ascii=False)
        return resp

    fix_msg = Message(
        role="user",
        text=(
            f"Your previous output was INVALID: {err}\n"
            "Return ONLY a valid JSON object conforming to the schema. No prose."
        ),
    )
    assistant_echo = Message(role="assistant", text=resp.text)
    prev_msgs = (
        tuple(req.messages)
        if req.messages
        else (Message(role="user", text=req.user or ""),)
    )
    fix_req = LLMRequest(
        system=req.system,
        messages=prev_msgs + (assistant_echo, fix_msg),
        tools=(),
        model=req.model,
        temperature=0.0,
        max_tokens=req.max_tokens,
        output_schema=req.output_schema,
        node_name=req.node_name + ":fix",
        timeout_seconds=req.timeout_seconds,
    )
    resp2 = await provider.call(fix_req)
    parsed, err = _try_parse_and_validate(resp2.text, req.output_schema)
    if parsed is None:
        raise LLMSchemaError(f"still invalid after fix: {err}")
    resp2.text = json.dumps(parsed, ensure_ascii=False)
    return resp2


def _try_parse_and_validate(
    text: str, schema: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        obj = json.loads(cleaned)
    except Exception as e:
        return None, f"json parse: {e}"
    try:
        validate_output(schema, obj)
    except SimulatorOutputInvalid as e:
        return None, str(e)
    return obj, None
