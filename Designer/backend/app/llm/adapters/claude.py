import json
import time
import uuid
from typing import Any

from app.llm.errors import LLMProtocolError, LLMUnavailable, TransientLLMError
from app.llm.types import LLMRequest, LLMResponse, LLMUsage, Message, ToolUseRequest


class ClaudeAdapter:
    name = "claude"

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        import anthropic

        self._anthropic = anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)
        self._default_model = default_model

    async def call(self, req: LLMRequest) -> LLMResponse:
        t0 = time.monotonic()
        params = self._build_params(req)
        try:
            raw = await self._client.messages.create(**params)
        except (self._anthropic.APIConnectionError, self._anthropic.APITimeoutError) as e:
            raise TransientLLMError(f"network: {e}") from e
        except self._anthropic.RateLimitError as e:
            raise TransientLLMError(f"rate limit: {e}", retry_after=5.0) from e
        except self._anthropic.APIStatusError as e:
            status = getattr(e, "status_code", 500)
            if 500 <= status < 600:
                raise TransientLLMError(f"5xx: {e}") from e
            if status == 429:
                raise TransientLLMError(f"429: {e}", retry_after=5.0) from e
            raise LLMUnavailable(str(e)) from e

        return self._parse(req, raw, t0)

    def _build_params(self, req: LLMRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": req.model or self._default_model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "system": req.system,
        }
        msgs: list[dict[str, Any]] = []
        if not req.messages and req.user is not None:
            msgs.append({"role": "user", "content": req.user})
        else:
            for m in req.messages:
                msgs.append(self._encode_message(m))
        if req.output_schema is not None:
            msgs = self._inject_output_schema(msgs, req.output_schema)
        params["messages"] = msgs
        if req.tools:
            params["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in req.tools
            ]
        return params

    def _encode_message(self, m: Message) -> dict[str, Any]:
        if m.role == "assistant":
            blocks: list[dict[str, Any]] = []
            if m.text:
                blocks.append({"type": "text", "text": m.text})
            for tu in m.tool_uses:
                blocks.append(
                    {"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input}
                )
            return {"role": "assistant", "content": blocks}
        if m.role == "tool_result":
            blocks = [
                {
                    "type": "tool_result",
                    "tool_use_id": r.tool_use_id,
                    "content": r.content,
                    "is_error": r.is_error,
                }
                for r in m.tool_results
            ]
            return {"role": "user", "content": blocks}
        return {
            "role": "user" if m.role == "system" else m.role,
            "content": m.text or "",
        }

    @staticmethod
    def _inject_output_schema(
        msgs: list[dict[str, Any]], schema: dict[str, Any]
    ) -> list[dict[str, Any]]:
        note = (
            "\n\nReturn ONLY a JSON object that conforms to this JSON Schema:\n"
            f"{json.dumps(schema, ensure_ascii=False)}\n"
            "Do NOT include any explanation, code fences, or non-JSON text."
        )
        if msgs and msgs[-1]["role"] == "user":
            last = msgs[-1]
            if isinstance(last["content"], str):
                last["content"] = last["content"] + note
            elif isinstance(last["content"], list):
                last["content"] = last["content"] + [{"type": "text", "text": note}]
        else:
            msgs.append({"role": "user", "content": note})
        return msgs

    def _parse(self, req: LLMRequest, raw: Any, t0: float) -> LLMResponse:
        call_id = f"llm_{uuid.uuid4().hex[:16]}"
        text_parts: list[str] = []
        tool_uses: list[ToolUseRequest] = []
        thinking_parts: list[str] = []
        for block in raw.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(block.text)
            elif btype == "thinking":
                thinking_parts.append(getattr(block, "thinking", ""))
            elif btype == "tool_use":
                tool_uses.append(
                    ToolUseRequest(id=block.id, name=block.name, input=block.input)
                )
        text = "\n".join(p for p in text_parts if p).strip()
        stop = raw.stop_reason or "end_turn"
        if stop not in ("end_turn", "max_tokens", "tool_use", "stop_sequence"):
            raise LLMProtocolError(f"unknown stop_reason {stop}")
        usage = LLMUsage(
            input_tokens=getattr(raw.usage, "input_tokens", 0),
            output_tokens=getattr(raw.usage, "output_tokens", 0),
        )
        return LLMResponse(
            call_id=call_id,
            model=req.model or self._default_model,
            text=text,
            tool_uses=tuple(tool_uses),
            stop_reason=stop,
            usage=usage,
            thinking="\n".join(thinking_parts) or None,
            raw=self._raw_to_dict(raw),
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    @staticmethod
    def _raw_to_dict(raw: Any) -> dict[str, Any]:
        for method in ("model_dump", "dict"):
            if hasattr(raw, method):
                try:
                    return getattr(raw, method)()
                except Exception:
                    pass
        return {"repr": repr(raw)}
