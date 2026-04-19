import json
import time
import uuid
from typing import Any

from app.llm.errors import LLMUnavailable, TransientLLMError
from app.llm.types import LLMRequest, LLMResponse, LLMUsage, ToolUseRequest


class OpenAIAdapter:
    """OpenAI 兼容协议适配器。

    支持 `base_url` 自定义 endpoint:MiniMax / DeepSeek / Ollama / vLLM 等任意
    OpenAI 兼容服务都能用。
    """

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str,
        timeout_seconds: float = 120.0,
        base_url: str | None = None,
    ) -> None:
        import openai

        self._openai = openai
        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.AsyncOpenAI(**kwargs)
        self._default_model = default_model

    async def call(self, req: LLMRequest) -> LLMResponse:
        t0 = time.monotonic()
        msgs: list[dict[str, Any]] = [{"role": "system", "content": req.system}]
        if req.user is not None and not req.messages:
            msgs.append({"role": "user", "content": req.user})
        else:
            for m in req.messages:
                msgs.append({"role": m.role, "content": m.text or ""})

        params: dict[str, Any] = {
            "model": req.model or self._default_model,
            "messages": msgs,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.output_schema is not None:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "strict": True,
                    "schema": req.output_schema,
                },
            }
        if req.tools:
            params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in req.tools
            ]

        try:
            raw = await self._client.chat.completions.create(**params)
        except self._openai.APITimeoutError as e:
            raise TransientLLMError(f"timeout: {e}") from e
        except self._openai.RateLimitError as e:
            raise TransientLLMError(f"rate limit: {e}", retry_after=5.0) from e
        except self._openai.APIConnectionError as e:
            raise TransientLLMError(f"network: {e}") from e
        except self._openai.APIStatusError as e:
            status = getattr(e, "status_code", 500)
            if 500 <= status < 600:
                raise TransientLLMError(f"5xx: {e}") from e
            raise LLMUnavailable(str(e)) from e

        choice = raw.choices[0]
        tool_uses = tuple(
            ToolUseRequest(
                id=c.id,
                name=c.function.name,
                input=json.loads(c.function.arguments),
            )
            for c in (choice.message.tool_calls or [])
        )
        return LLMResponse(
            call_id=f"llm_{uuid.uuid4().hex[:16]}",
            model=params["model"],
            text=choice.message.content or "",
            tool_uses=tool_uses,
            stop_reason="tool_use" if tool_uses else "end_turn",
            usage=LLMUsage(
                input_tokens=raw.usage.prompt_tokens,
                output_tokens=raw.usage.completion_tokens,
            ),
            raw=raw.model_dump() if hasattr(raw, "model_dump") else {},
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
