# 05 · LLM 适配层

> 依赖:02(配置、日志、metrics、redis)
> 交付物:LLMProvider 抽象 + 具体适配器(Claude / OpenAI / Mock) + 装饰器链(Retry/Trace/Metrics/RateLimit) + LLMClient 门面 + tool-call 多轮原语 + 单元/集成测试
> 验收:
> 1. `await container.llm_client.call(LLMRequest(system=..., user=...))` 对真实 Claude 能返回结构化响应(contract test 条件:`LLM_API_KEY` 存在)
> 2. `container.llm_client.call_sync(...)` 能被同步代码调用(给 03 章 LLMSimulator 用),底层自动桥接 async
> 3. 失败退避 3 次、超时 120s、全失败抛 `LLMUnavailable`
> 4. Trace 装饰器把每次调用完整落到 MongoDB(`run_step_details.llm_calls[]`)
> 5. Mock Provider 让下游章节的单测完全离线

---

## 5.1 模块总览

```
app/llm/
├── __init__.py
├── errors.py                 LLMUnavailable / LLMSchemaError / TransientLLMError ...
├── types.py                  LLMRequest / LLMResponse / ToolUseRequest / ToolUseResult
├── provider.py               LLMProvider 抽象 Protocol
├── adapters/
│   ├── __init__.py
│   ├── claude.py             ClaudeAdapter(anthropic SDK)
│   ├── openai.py             OpenAIAdapter(openai SDK,备选)
│   └── mock.py               MockProvider(测试用)
├── decorators/
│   ├── __init__.py
│   ├── retry.py              RetryDecorator
│   ├── trace.py              TraceDecorator
│   ├── metrics.py            MetricsDecorator
│   ├── rate_limit.py         RateLimitDecorator
│   └── timeout.py            TimeoutDecorator
├── client.py                 LLMClient(组合根,对外唯一入口)
├── schema_coerce.py          把 LLM 输出强制符合 output_schema(retry 1 次 + 修复提示)
└── agent_loop.py             tool-call 多轮原语(给 07 章 Handler 2 用)

app/middlewares/... 不动
app/bootstrap.py  追加:llm_client 装配
```

---

## 5.2 异常体系

```python
# app/llm/errors.py
from app.domain.errors import DependencyError, BusinessError

class LLMUnavailable(DependencyError):
    code = "DEPENDENCY_LLM_UNAVAILABLE"
    http_status = 503

class LLMTimeout(DependencyError):
    code = "DEPENDENCY_LLM_TIMEOUT"

class LLMRateLimited(DependencyError):
    code = "DEPENDENCY_LLM_RATE_LIMITED"

class LLMSchemaError(BusinessError):
    code = "DEPENDENCY_LLM_SCHEMA_MISMATCH"
    http_status = 422

class LLMProtocolError(BusinessError):
    code = "DEPENDENCY_LLM_PROTOCOL_ERROR"

class TransientLLMError(Exception):
    """内部用:可重试的网络/5xx/限流类错误。装饰器重试耗尽后转为 LLMUnavailable。"""
    def __init__(self, msg: str, retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after
```

---

## 5.3 请求/响应值对象

```python
# app/llm/types.py
from dataclasses import dataclass, field
from typing import Any, Literal

@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Anthropic / OpenAI 通用 tool 规约。仅含名字 + description + input_schema"""
    name: str
    description: str
    input_schema: dict

@dataclass(frozen=True, slots=True)
class ToolUseRequest:
    """LLM 想调一个 tool 时在响应里告诉我们的内容"""
    id: str                         # LLM 生成的调用 id;回传结果时要带
    name: str                       # tool name = Tool.name = 节点类型
    input: dict

@dataclass(frozen=True, slots=True)
class ToolUseResult:
    """我们把 tool 的执行结果回给 LLM"""
    tool_use_id: str                # 匹配 ToolUseRequest.id
    content: str                    # 文本或 JSON 字符串
    is_error: bool = False

Role = Literal["system", "user", "assistant", "tool_result"]

@dataclass(frozen=True, slots=True)
class Message:
    """一条 conversation 消息。
    - role=system:一般只一条,放 instructions
    - role=user:用户内容
    - role=assistant:LLM 产出(含 text + tool_uses)
    - role=tool_result:我们向 LLM 回传 tool 执行结果
    """
    role: Role
    text: str | None = None
    tool_uses: tuple[ToolUseRequest, ...] = ()
    tool_results: tuple[ToolUseResult, ...] = ()

@dataclass(frozen=True, slots=True)
class LLMRequest:
    """单轮请求。多轮走 agent_loop.py(见 §5.12)"""
    system: str
    messages: tuple[Message, ...] = ()
    user: str | None = None                 # 便捷:如果 messages 为空,则把 user 包成一条 user message
    tools: tuple[ToolSpec, ...] = ()
    model: str | None = None                # None = 用默认模型
    temperature: float = 0.0
    max_tokens: int = 4096
    output_schema: dict | None = None       # 要求 LLM 返回符合 schema 的 JSON(强制模式,见 §5.11)
    node_name: str = "unknown"              # 调用方标识(放 metrics/trace)
    timeout_seconds: float | None = None

@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0

@dataclass(slots=True)
class LLMResponse:
    """单轮响应"""
    call_id: str                            # 我们自己生成的 id,贯穿 trace
    model: str
    text: str                               # 合并后的文本内容(去掉 tool-use 块)
    tool_uses: tuple[ToolUseRequest, ...]
    stop_reason: Literal["end_turn", "max_tokens", "tool_use", "stop_sequence", "error"]
    usage: LLMUsage
    thinking: str | None = None
    raw: dict = field(default_factory=dict) # 原始 provider 响应(排 bug 用,落 trace)
    duration_ms: int = 0

    @property
    def parsed_json(self) -> dict:
        """在 output_schema 模式下,文本本应是一段 JSON。用该属性取。"""
        import json
        return json.loads(self.text)
```

---

## 5.4 LLMProvider 抽象

```python
# app/llm/provider.py
from typing import Protocol, runtime_checkable
from app.llm.types import LLMRequest, LLMResponse

@runtime_checkable
class LLMProvider(Protocol):
    """所有具体供应商(Claude / OpenAI / Mock)都实现这个协议。
    装饰器也实现这个协议,从而可以套在任何一层。"""
    name: str
    async def call(self, req: LLMRequest) -> LLMResponse: ...
```

**关键**:`LLMProvider` 用 `Protocol`,让装饰器不需要继承,只需结构匹配即可。避免"继承装饰器继承适配器"的耦合。

---

## 5.5 ClaudeAdapter

```python
# app/llm/adapters/claude.py
import json
import time
import uuid
import anthropic
from anthropic import APIStatusError, APITimeoutError, RateLimitError, APIConnectionError
from app.llm.provider import LLMProvider
from app.llm.types import (
    LLMRequest, LLMResponse, LLMUsage, Message,
    ToolUseRequest, ToolUseResult, ToolSpec,
)
from app.llm.errors import TransientLLMError, LLMProtocolError, LLMUnavailable

class ClaudeAdapter(LLMProvider):
    name = "claude"

    def __init__(self, *, api_key: str, default_model: str,
                 timeout_seconds: float = 120.0) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)
        self._default_model = default_model

    async def call(self, req: LLMRequest) -> LLMResponse:
        t0 = time.monotonic()
        params = self._build_params(req)
        try:
            raw = await self._client.messages.create(**params)
        except (APIConnectionError, APITimeoutError) as e:
            raise TransientLLMError(f"network: {e}") from e
        except RateLimitError as e:
            raise TransientLLMError(f"rate limit: {e}", retry_after=5.0) from e
        except APIStatusError as e:
            if 500 <= e.status_code < 600:
                raise TransientLLMError(f"5xx: {e}") from e
            if e.status_code == 429:
                raise TransientLLMError(f"429: {e}", retry_after=5.0) from e
            raise LLMUnavailable(str(e)) from e

        return self._parse(req, raw, t0)

    def _build_params(self, req: LLMRequest) -> dict:
        params: dict = {
            "model": req.model or self._default_model,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "system": req.system,
        }
        msgs: list[dict] = []
        # 便捷模式
        if not req.messages and req.user is not None:
            msgs.append({"role": "user", "content": req.user})
        else:
            for m in req.messages:
                msgs.append(self._encode_message(m))
        # output_schema 强制模式:让模型必须返回 JSON
        if req.output_schema is not None:
            msgs = self._inject_output_schema(msgs, req.output_schema)
        params["messages"] = msgs
        if req.tools:
            params["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in req.tools
            ]
        return params

    def _encode_message(self, m: Message) -> dict:
        if m.role == "assistant":
            blocks: list[dict] = []
            if m.text: blocks.append({"type": "text", "text": m.text})
            for tu in m.tool_uses:
                blocks.append({"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input})
            return {"role": "assistant", "content": blocks}
        if m.role == "tool_result":
            blocks = [{
                "type": "tool_result",
                "tool_use_id": r.tool_use_id,
                "content": r.content,
                "is_error": r.is_error,
            } for r in m.tool_results]
            return {"role": "user", "content": blocks}
        # user / system(system 应在 params.system,不应作为 message)
        return {"role": m.role if m.role != "system" else "user",
                "content": m.text or ""}

    @staticmethod
    def _inject_output_schema(msgs: list[dict], schema: dict) -> list[dict]:
        """在最后一条 user message 里附加 JSON Schema 指令。
        防御:如果最后一条不是 user,则追加一条 user。"""
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

    def _parse(self, req: LLMRequest, raw, t0: float) -> LLMResponse:
        call_id = f"llm_{uuid.uuid4().hex[:16]}"
        text_parts: list[str] = []
        tool_uses: list[ToolUseRequest] = []
        thinking_parts: list[str] = []
        for block in raw.content:
            t = getattr(block, "type", None)
            if t == "text":
                text_parts.append(block.text)
            elif t == "thinking":
                thinking_parts.append(getattr(block, "thinking", ""))
            elif t == "tool_use":
                tool_uses.append(ToolUseRequest(id=block.id, name=block.name, input=block.input))
            else:
                # 未知类型,忽略但记 raw
                pass
        text = "\n".join(p for p in text_parts if p).strip()

        stop = raw.stop_reason or "end_turn"
        if stop not in ("end_turn", "max_tokens", "tool_use", "stop_sequence"):
            raise LLMProtocolError(f"unknown stop_reason {stop}")

        usage = LLMUsage(
            input_tokens=getattr(raw.usage, "input_tokens", 0),
            output_tokens=getattr(raw.usage, "output_tokens", 0),
            thinking_tokens=0,
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
    def _raw_to_dict(raw) -> dict:
        # anthropic 对象有 .model_dump() / .dict();兼容两种
        for m in ("model_dump", "dict"):
            if hasattr(raw, m): return getattr(raw, m)()
        return {"repr": repr(raw)}
```

---

## 5.6 OpenAIAdapter(备选)

```python
# app/llm/adapters/openai.py
import json
import time
import uuid
import openai
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse, LLMUsage, ToolUseRequest
from app.llm.errors import TransientLLMError, LLMUnavailable

class OpenAIAdapter(LLMProvider):
    name = "openai"

    def __init__(self, *, api_key: str, default_model: str,
                 timeout_seconds: float = 120.0) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)
        self._default_model = default_model

    async def call(self, req: LLMRequest) -> LLMResponse:
        t0 = time.monotonic()
        msgs = [{"role": "system", "content": req.system}]
        if req.user is not None and not req.messages:
            msgs.append({"role": "user", "content": req.user})
        else:
            for m in req.messages:
                msgs.append(self._encode(m))

        params: dict = {
            "model": req.model or self._default_model,
            "messages": msgs,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.output_schema is not None:
            # OpenAI structured outputs
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "strict": True, "schema": req.output_schema},
            }
        if req.tools:
            params["tools"] = [{
                "type": "function",
                "function": {
                    "name": t.name, "description": t.description, "parameters": t.input_schema,
                },
            } for t in req.tools]

        try:
            raw = await self._client.chat.completions.create(**params)
        except openai.APITimeoutError as e:
            raise TransientLLMError(f"timeout: {e}") from e
        except openai.RateLimitError as e:
            raise TransientLLMError(f"rate limit: {e}", retry_after=5.0) from e
        except openai.APIConnectionError as e:
            raise TransientLLMError(f"network: {e}") from e
        except openai.APIStatusError as e:
            if 500 <= e.status_code < 600:
                raise TransientLLMError(f"5xx: {e}") from e
            raise LLMUnavailable(str(e)) from e

        choice = raw.choices[0]
        tool_uses = tuple(
            ToolUseRequest(id=c.id, name=c.function.name, input=json.loads(c.function.arguments))
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
            thinking=None,
            raw=raw.model_dump() if hasattr(raw, "model_dump") else {},
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    def _encode(self, m):
        # OpenAI 和 Anthropic 的 tool-call 协议略不同,这里对齐(略)
        ...
```

> v1 主用 Claude;OpenAI 适配器保留但不进关键路径。只需最少可工作版本。

---

## 5.7 MockProvider(测试用)

```python
# app/llm/adapters/mock.py
import uuid
import re
from dataclasses import dataclass, field
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse, LLMUsage, ToolUseRequest

@dataclass
class MockStep:
    """一次 mock 响应的脚本:
    - match: 匹配条件(user_contains / system_contains / any)
    - text:  回复文本
    - tool_uses: 要模拟调用的 tools
    """
    match: dict
    text: str = ""
    tool_uses: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"

class MockProvider(LLMProvider):
    """按顺序脚本回放。默认每个步骤匹配一次,匹配到就 pop。"""
    name = "mock"

    def __init__(self, steps: list[MockStep]) -> None:
        self._steps = list(steps)
        self.call_log: list[LLMRequest] = []

    async def call(self, req: LLMRequest) -> LLMResponse:
        self.call_log.append(req)
        for i, s in enumerate(self._steps):
            if self._match(req, s.match):
                self._steps.pop(i)
                return self._make_response(req, s)
        raise AssertionError(f"no mock step matched. user={req.user[:100] if req.user else '?'}")

    def _match(self, req: LLMRequest, m: dict) -> bool:
        if "any" in m: return True
        if "user_contains" in m:
            u = req.user or ""
            if m["user_contains"] not in u: return False
        if "system_contains" in m:
            if m["system_contains"] not in req.system: return False
        if "user_regex" in m:
            if not re.search(m["user_regex"], req.user or ""): return False
        return True

    def _make_response(self, req: LLMRequest, s: MockStep) -> LLMResponse:
        return LLMResponse(
            call_id=f"mock_{uuid.uuid4().hex[:8]}",
            model=req.model or "mock",
            text=s.text,
            tool_uses=tuple(ToolUseRequest(id=f"tu_{i}", name=t["name"], input=t.get("input", {}))
                            for i, t in enumerate(s.tool_uses)),
            stop_reason=s.stop_reason,           # type: ignore[arg-type]
            usage=LLMUsage(),
            raw={"mock": True},
            duration_ms=0,
        )
```

---

## 5.8 RetryDecorator

```python
# app/llm/decorators/retry.py
import asyncio
import random
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse
from app.llm.errors import TransientLLMError, LLMUnavailable
from app.infra.logging import get_logger

log = get_logger(__name__)

class RetryDecorator(LLMProvider):
    """指数退避 + 抖动。transient 才重试,其他错误直接抛。"""
    def __init__(self, inner: LLMProvider, *, max_attempts: int = 3,
                 base: float = 1.0, cap: float = 30.0) -> None:
        self._inner = inner; self.name = inner.name
        self._max = max_attempts; self._base = base; self._cap = cap

    async def call(self, req: LLMRequest) -> LLMResponse:
        last_err: Exception | None = None
        for i in range(self._max):
            try:
                return await self._inner.call(req)
            except TransientLLMError as e:
                last_err = e
                if i == self._max - 1: break
                delay = min(self._cap, self._base * (2 ** i)) + random.random()
                if e.retry_after is not None:
                    delay = max(delay, e.retry_after)
                log.warning("llm_retry", attempt=i + 1, max=self._max, delay=delay, err=str(e))
                await asyncio.sleep(delay)
        raise LLMUnavailable(f"after {self._max} retries: {last_err}")
```

---

## 5.9 TraceDecorator

```python
# app/llm/decorators/trace.py
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse
from app.utils.hash import sha256_json
from app.utils.sanitize import sanitize

class TraceDecorator(LLMProvider):
    """每次 LLM 调用落一条 trace 到 context 里的"current llm_calls buffer"。

    buffer 由 06 章 BasePipelineStep 在每个 step 执行时绑定到 contextvar。
    本装饰器只写,不读 - 让 step 基类负责把 buffer 转存 MongoDB。
    """
    def __init__(self, inner: LLMProvider, trace_context: "LLMTraceContext") -> None:
        self._inner = inner; self.name = inner.name
        self._ctx = trace_context

    async def call(self, req: LLMRequest) -> LLMResponse:
        try:
            resp = await self._inner.call(req)
            self._ctx.record({
                "call_id": resp.call_id,
                "model": resp.model,
                "node_name": req.node_name,
                "system_prompt": sanitize(req.system),
                "system_prompt_hash": sha256_json({"s": req.system}),
                "user_prompt": sanitize(req.user or ""),
                "messages": [sanitize(m.__dict__) for m in req.messages],
                "tools": [{"name": t.name} for t in req.tools],
                "thinking": sanitize(resp.thinking or ""),
                "response": sanitize(resp.text),
                "tool_uses": [sanitize(tu.__dict__) for tu in resp.tool_uses],
                "stop_reason": resp.stop_reason,
                "tokens": {
                    "input": resp.usage.input_tokens,
                    "output": resp.usage.output_tokens,
                    "thinking": resp.usage.thinking_tokens,
                },
                "duration_ms": resp.duration_ms,
                "error": None,
            })
            return resp
        except Exception as e:
            self._ctx.record({
                "call_id": None, "node_name": req.node_name,
                "error": str(e), "duration_ms": 0,
            })
            raise
```

```python
# app/llm/decorators/trace.py (续)
import contextvars
from typing import Any

class LLMTraceContext:
    """contextvar 包装的 buffer,Step 基类通过它拿到/清空当前调用的 llm_calls。"""
    _buf: contextvars.ContextVar[list[dict] | None] = contextvars.ContextVar("llm_trace_buf", default=None)

    def begin_scope(self) -> None:
        self._buf.set([])

    def record(self, entry: dict) -> None:
        b = self._buf.get()
        if b is None:
            # step 作用域外的调用(比如 Tool simulate 预览),忽略
            return
        b.append(entry)

    def snapshot(self) -> list[dict]:
        return list(self._buf.get() or [])

    def end_scope(self) -> list[dict]:
        out = list(self._buf.get() or [])
        self._buf.set(None)
        return out
```

---

## 5.10 MetricsDecorator / RateLimitDecorator / TimeoutDecorator

```python
# app/llm/decorators/metrics.py
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse
from app.infra.metrics import LLM_CALLS, LLM_TOKENS

class MetricsDecorator(LLMProvider):
    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner; self.name = inner.name
    async def call(self, req: LLMRequest) -> LLMResponse:
        resp = await self._inner.call(req)
        LLM_CALLS.labels(model=resp.model, node_name=req.node_name).inc()
        LLM_TOKENS.labels(model=resp.model, kind="input").inc(resp.usage.input_tokens)
        LLM_TOKENS.labels(model=resp.model, kind="output").inc(resp.usage.output_tokens)
        return resp
```

```python
# app/llm/decorators/rate_limit.py
import asyncio
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse

class RateLimitDecorator(LLMProvider):
    """全局并发上限。超过 MAX_CONCURRENCY 则阻塞等待。"""
    def __init__(self, inner: LLMProvider, *, max_concurrency: int) -> None:
        self._inner = inner; self.name = inner.name
        self._sem = asyncio.Semaphore(max_concurrency)
    async def call(self, req: LLMRequest) -> LLMResponse:
        async with self._sem:
            return await self._inner.call(req)
```

```python
# app/llm/decorators/timeout.py
import asyncio
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse
from app.llm.errors import LLMTimeout

class TimeoutDecorator(LLMProvider):
    """per-request 超时;provider 自己也有超时,这里是兜底。"""
    def __init__(self, inner: LLMProvider, *, default_timeout: float) -> None:
        self._inner = inner; self.name = inner.name
        self._default = default_timeout
    async def call(self, req: LLMRequest) -> LLMResponse:
        t = req.timeout_seconds or self._default
        try:
            return await asyncio.wait_for(self._inner.call(req), timeout=t)
        except asyncio.TimeoutError:
            raise LLMTimeout(f"timeout after {t}s")
```

---

## 5.11 schema_coerce:强制结构化输出

```python
# app/llm/schema_coerce.py
"""LLM 返回的 text 应该是合法 JSON 且符合 output_schema。
如果第一次不合法,给一次"修复"重试(把错误信息塞回 user 让 LLM 自修)。
再失败 → 抛 LLMSchemaError。"""

import json
from app.llm.types import LLMRequest, LLMResponse, Message
from app.llm.errors import LLMSchemaError
from app.tool_runtime.json_schema import validate_output
from app.tool_runtime.errors import SimulatorOutputInvalid

async def coerce_json_output(provider, req: LLMRequest) -> LLMResponse:
    """确保 response.text 是合法 JSON 并符合 req.output_schema。
    用法:代替直接调 provider.call(req),用这个包一层。"""
    if req.output_schema is None:
        return await provider.call(req)

    resp = await provider.call(req)
    parsed, err = _try_parse_and_validate(resp.text, req.output_schema)
    if parsed is not None:
        resp.text = json.dumps(parsed, ensure_ascii=False)
        return resp

    # 修复提示
    fix_msg = Message(
        role="user",
        text=(f"Your previous output was INVALID: {err}\n"
              f"Return ONLY a valid JSON object conforming to the schema. No prose."),
    )
    assistant_echo = Message(role="assistant", text=resp.text)
    new_msgs = tuple(req.messages) + (assistant_echo, fix_msg) if req.messages \
               else (Message(role="user", text=req.user or ""), assistant_echo, fix_msg)
    fix_req = LLMRequest(
        system=req.system, messages=new_msgs,
        tools=(), model=req.model, temperature=0.0,
        max_tokens=req.max_tokens, output_schema=req.output_schema,
        node_name=req.node_name + ":fix", timeout_seconds=req.timeout_seconds,
    )
    resp2 = await provider.call(fix_req)
    parsed, err = _try_parse_and_validate(resp2.text, req.output_schema)
    if parsed is None:
        raise LLMSchemaError(f"still invalid after fix: {err}")
    resp2.text = json.dumps(parsed, ensure_ascii=False)
    return resp2

def _try_parse_and_validate(text: str, schema: dict) -> tuple[dict | None, str | None]:
    # 允许 LLM 套 ```json ... ``` 代码块
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"): cleaned = cleaned[4:]
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
```

---

## 5.12 agent_loop:tool-call 多轮原语

> 这是第一阶段 Handler 2("LLM 驱动森林执行")的底层原语。
> 07 章的 Handler 2 不直接管协议细节,而是组合这个 loop + 注入自己的 tool 执行器。

```python
# app/llm/agent_loop.py
"""让 LLM 在一个 system + 一个初始 user 的基础上,通过 tool-call 多轮交互,
  直到 stop_reason=end_turn 或到达最大轮数。

用法:
    result = await run_agent_loop(
        provider=llm_client,
        system="你是级跳设计执行者...",
        initial_user=json.dumps(initial_input),
        tools=[ToolSpec(...)],
        tool_executor=my_executor,          # 接 ToolUseRequest,返回 ToolUseResult
        max_iterations=20,
        model=None,
    )
"""
from dataclasses import dataclass, field
from typing import Protocol, Callable, Awaitable
from app.llm.types import (
    LLMRequest, LLMResponse, Message,
    ToolSpec, ToolUseRequest, ToolUseResult,
)
from app.llm.errors import LLMProtocolError

class ToolExecutor(Protocol):
    """调用方提供的工具执行器。Handler 2 里就是"把 ToolUseRequest 路由到对应 ToolSimulator"。"""
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
    stopped_reason: str                     # "end_turn" / "max_iterations" / "error"

async def run_agent_loop(
    *,
    provider,                                # LLMProvider 兼容对象(通常是 LLMClient)
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

        # 追加 assistant 响应到历史
        messages.append(Message(role="assistant", text=resp.text, tool_uses=resp.tool_uses))

        step = AgentStep(iteration=i, request=req, response=resp)

        if resp.stop_reason == "end_turn":
            steps.append(step)
            return AgentResult(steps=steps, final_text=resp.text,
                               tool_call_count=tool_calls_total, stopped_reason="end_turn")

        if resp.stop_reason != "tool_use" or not resp.tool_uses:
            # 未知停止或无 tool_use 却没 end_turn
            steps.append(step)
            return AgentResult(steps=steps, final_text=resp.text,
                               tool_call_count=tool_calls_total, stopped_reason="error")

        # 执行所有 tool_use 并把结果作为单条 tool_result 消息回送
        results: list[ToolUseResult] = []
        for tu in resp.tool_uses:
            try:
                r = await tool_executor(tu)
            except Exception as e:
                r = ToolUseResult(tool_use_id=tu.id, content=f"executor error: {e}", is_error=True)
            results.append(r)
            tool_calls_total += 1
        step.tool_results = results
        steps.append(step)
        messages.append(Message(role="tool_result", tool_results=tuple(results)))

    return AgentResult(steps=steps, final_text="",
                       tool_call_count=tool_calls_total, stopped_reason="max_iterations")
```

**要点**:
- `tool_executor` 是一个**纯函数式依赖**,不绑定任何具体实现。07 章 Handler 2 会提供一个把 `ToolUseRequest.name` 路由到 `ToolSimulator` 的 executor
- loop 本身不做语义判定,只负责协议往返
- `AgentResult.steps` 里记录了**每一轮的请求/响应/tool 结果**,Handler 2 据此完成自己的 trace 和判定

---

## 5.13 LLMClient(组合根,对外唯一入口)

```python
# app/llm/client.py
import asyncio
import threading
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse
from app.llm.adapters.claude import ClaudeAdapter
from app.llm.adapters.openai import OpenAIAdapter
from app.llm.decorators.retry import RetryDecorator
from app.llm.decorators.trace import TraceDecorator, LLMTraceContext
from app.llm.decorators.metrics import MetricsDecorator
from app.llm.decorators.rate_limit import RateLimitDecorator
from app.llm.decorators.timeout import TimeoutDecorator
from app.llm.schema_coerce import coerce_json_output

def build_provider(settings) -> LLMProvider:
    """根据配置构造底层适配器(不含装饰器)。"""
    if settings.LLM_PROVIDER == "claude":
        return ClaudeAdapter(
            api_key=settings.LLM_API_KEY,
            default_model=settings.LLM_MODEL_DEFAULT,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )
    if settings.LLM_PROVIDER == "openai":
        return OpenAIAdapter(
            api_key=settings.LLM_API_KEY,
            default_model=settings.LLM_MODEL_DEFAULT,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )
    raise ValueError(f"unknown LLM_PROVIDER {settings.LLM_PROVIDER}")

class LLMClient:
    """外部唯一入口。内部是装饰器链:
       raw provider → Retry → Timeout → Metrics → Trace → RateLimit
    (构造顺序从内到外)
    """
    def __init__(self, settings, *, provider: LLMProvider | None = None) -> None:
        self.trace_ctx = LLMTraceContext()
        base = provider or build_provider(settings)
        chain: LLMProvider = base
        chain = RetryDecorator(chain, max_attempts=3)
        chain = TimeoutDecorator(chain, default_timeout=settings.LLM_TIMEOUT_SECONDS)
        chain = MetricsDecorator(chain)
        chain = TraceDecorator(chain, self.trace_ctx)
        chain = RateLimitDecorator(chain, max_concurrency=settings.LLM_MAX_CONCURRENCY)
        self._chain = chain

    async def call(self, req: LLMRequest) -> LLMResponse:
        """异步主接口。强制结构化输出的场景自动走 schema_coerce。"""
        if req.output_schema is not None:
            return await coerce_json_output(self._chain, req)
        return await self._chain.call(req)

    def call_sync(self, *,
                  system: str, user: str,
                  model: str | None = None,
                  output_schema: dict | None = None,
                  node_name: str = "sync",
                  **kw) -> LLMResponse:
        """给同步代码(例如 ToolSimulator.run)调的桥接。
        策略:
          - 如果当前协程里已有 event loop → 用 asyncio.run_coroutine_threadsafe 打到专用 loop
          - 否则 → 直接 asyncio.run(...)
        """
        req = LLMRequest(system=system, user=user, model=model,
                         output_schema=output_schema, node_name=node_name, **kw)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.call(req))
        # running loop 存在,必须从另一个线程 schedule
        return _run_in_background_loop(self.call(req))

    @property
    def provider_name(self) -> str:
        # 穿透拿底层 provider 名字
        p: LLMProvider = self._chain
        while hasattr(p, "_inner"):
            p = p._inner      # type: ignore[attr-defined]
        return p.name

# 后台专用 loop(懒启动,跨线程调度)
_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_thread: threading.Thread | None = None
_bg_lock = threading.Lock()

def _ensure_bg_loop() -> asyncio.AbstractEventLoop:
    global _bg_loop, _bg_thread
    with _bg_lock:
        if _bg_loop is None:
            _bg_loop = asyncio.new_event_loop()
            _bg_thread = threading.Thread(
                target=_bg_loop.run_forever, daemon=True, name="llm-bg-loop"
            )
            _bg_thread.start()
    return _bg_loop

def _run_in_background_loop(coro):
    loop = _ensure_bg_loop()
    fut = asyncio.run_coroutine_threadsafe(coro, loop)
    return fut.result()
```

**设计要点**:

1. **装饰器顺序(从里到外)** = Retry → Timeout → Metrics → Trace → RateLimit。意味着真实调用时外→里为 RateLimit→Trace→Metrics→Timeout→Retry→Provider。
2. **schema_coerce 不放进装饰器链**,而是在 `call()` 方法里按 `output_schema` 条件触发——它会发两次 request,装饰器链会对**每一次** request 独立计数和 trace
3. **call_sync**:给 03 章 `LLMSimulator.run()` 这种运行在 Python 线程里的同步代码用。后端主流程是 async,但 ToolSimulator 为了 CPU-bound 友好,保持 sync 签名
4. **trace_ctx**:暴露给上层(06 章 BasePipelineStep),每个 step 执行前 `begin_scope()`,执行后 `end_scope()` 取出所有 llm_calls 落 Mongo

---

## 5.14 Bootstrap 装配

```python
# app/bootstrap.py (追加)
from app.llm.client import LLMClient

def build_container(settings):
    # ... 前面
    llm_client = LLMClient(settings)
    container.llm_client = llm_client
    # tool_service_factory 的 llm_client 现在能真正用了
    ...
```

03 章 `LLMSimulator` 调用的 `ctx.llm.call_sync(...)`——`ctx.llm` 指向的就是这个 `LLMClient`。

---

## 5.15 测试要点

### 5.15.1 纯单元(用 MockProvider)

```python
# tests/unit/llm/test_mock_provider.py
import pytest
from app.llm.adapters.mock import MockProvider, MockStep
from app.llm.types import LLMRequest

async def test_mock_match_and_pop():
    mp = MockProvider([
        MockStep(match={"user_contains": "hello"}, text="hi"),
        MockStep(match={"any": True}, text="default"),
    ])
    r1 = await mp.call(LLMRequest(system="", user="hello world"))
    assert r1.text == "hi"
    r2 = await mp.call(LLMRequest(system="", user="whatever"))
    assert r2.text == "default"
```

### 5.15.2 装饰器

- `test_retry.py`:
  - TransientLLMError 连抛 2 次后成功 → 返回成功响应
  - 连抛 3 次 → LLMUnavailable
  - 非 transient 错误不重试
  - `retry_after` 优先于指数退避
- `test_timeout.py`:
  - 内部调用慢 → 装饰器超时,抛 LLMTimeout
- `test_metrics.py`:
  - 调一次 → Counter +1;tokens 累加正确
- `test_rate_limit.py`:
  - max_concurrency=2,三个并发调,第三个要等前面至少一个完成
- `test_trace.py`:
  - `begin_scope` 后调两次 call → `end_scope` 返回 2 条记录;敏感字段被 sanitize

### 5.15.3 schema_coerce

```python
async def test_coerce_first_shot_ok():
    provider = MockProvider([MockStep(match={"any": True}, text='{"a": 1}')])
    req = LLMRequest(system="", user="x", output_schema={"type":"object","required":["a"],"properties":{"a":{"type":"integer"}}})
    resp = await coerce_json_output(provider, req)
    assert resp.parsed_json == {"a": 1}

async def test_coerce_fixes_on_second():
    provider = MockProvider([
        MockStep(match={"any": True}, text='not json'),
        MockStep(match={"any": True}, text='{"a": 1}'),
    ])
    req = LLMRequest(system="", user="x", output_schema={"type":"object","required":["a"],"properties":{"a":{"type":"integer"}}})
    resp = await coerce_json_output(provider, req)
    assert resp.parsed_json == {"a": 1}

async def test_coerce_gives_up():
    provider = MockProvider([
        MockStep(match={"any": True}, text='not json'),
        MockStep(match={"any": True}, text='still not'),
    ])
    with pytest.raises(LLMSchemaError):
        await coerce_json_output(provider, LLMRequest(system="", user="x",
            output_schema={"type":"object","required":["a"],"properties":{"a":{"type":"integer"}}}))
```

### 5.15.4 agent_loop

```python
async def test_agent_loop_end_turn():
    provider = MockProvider([MockStep(match={"any": True}, text="done", stop_reason="end_turn")])
    async def exec_(tu): raise AssertionError("should not be called")
    r = await run_agent_loop(provider=provider, system="", initial_user="hi",
                             tools=[], tool_executor=exec_, max_iterations=5)
    assert r.stopped_reason == "end_turn" and r.final_text == "done"

async def test_agent_loop_tool_use():
    provider = MockProvider([
        MockStep(match={"any": True}, stop_reason="tool_use",
                 tool_uses=[{"name": "add", "input": {"a": 1, "b": 2}}]),
        MockStep(match={"any": True}, text="answer is 3", stop_reason="end_turn"),
    ])
    async def exec_(tu):
        assert tu.name == "add"
        return ToolUseResult(tool_use_id=tu.id, content="3")
    r = await run_agent_loop(provider=provider, system="", initial_user="hi",
                             tools=[ToolSpec(name="add", description="", input_schema={})],
                             tool_executor=exec_, max_iterations=5)
    assert r.stopped_reason == "end_turn"
    assert r.tool_call_count == 1
    assert r.final_text == "answer is 3"

async def test_agent_loop_max_iter():
    # 永远 tool_use 的 mock → 最终 max_iterations
    provider = MockProvider([MockStep(match={"any": True}, stop_reason="tool_use",
                                       tool_uses=[{"name":"x","input":{}}])] * 10)
    async def exec_(tu): return ToolUseResult(tool_use_id=tu.id, content="ok")
    r = await run_agent_loop(provider=provider, system="", initial_user="hi",
                             tools=[ToolSpec(name="x", description="", input_schema={})],
                             tool_executor=exec_, max_iterations=3)
    assert r.stopped_reason == "max_iterations"
    assert r.tool_call_count == 3
```

### 5.15.5 集成(contract test,需真实 API key)

```python
# tests/integration/test_claude_contract.py
import os, pytest
pytestmark = pytest.mark.skipif(not os.environ.get("LLM_API_KEY"), reason="no real key")

async def test_claude_simple(real_llm_client):
    r = await real_llm_client.call(LLMRequest(
        system="You are a math assistant.",
        user="What is 1+1? Output only the number.",
        max_tokens=16,
    ))
    assert r.text.strip() in {"2", "2."}

async def test_claude_structured_output(real_llm_client):
    schema = {"type":"object","required":["sum"],"properties":{"sum":{"type":"integer"}}}
    r = await real_llm_client.call(LLMRequest(
        system="Return JSON.",
        user="Compute 2+3.",
        output_schema=schema,
    ))
    assert r.parsed_json == {"sum": 5}
```

CI 只在 nightly 或手动触发时跑这一组;PR 阶段只跑 Mock。

### 5.15.6 call_sync 桥接

- 无运行中 loop 时能正常工作
- 运行中 loop(比如在 pytest-asyncio 里)里调用 `call_sync` 不死锁(因为走后台 loop)

---

## 5.16 一些易错点(必须读完再写代码)

1. **不要**把 `output_schema` 的 coerce 塞进装饰器链。装饰器链应该对"一次 LLM 调用"透明;coerce 本身就是一次"最多两次调用"的**业务动作**
2. **不要**在适配器里自己加重试。重试交给 `RetryDecorator`,否则双重重试会把超时放大 N 倍
3. **`TraceDecorator.record`** 必须对 `begin_scope` 外的调用静默丢弃,否则单测 / 预览调用会写脏 Mongo
4. **`call_sync` 的后台 loop 是进程级单例**,整个进程寿命只启一次,不要每次 call 新起
5. **`agent_loop` 的 `tool_executor`** 必须 async;它可能阻塞时间较长(调 ToolSimulator,甚至继续调 LLM),要保证没有 GIL 锁主 loop
6. **敏感信息**:system prompt 里**绝对**不能带 API key、DB 凭证。这不是装饰器能兜住的,是业务层的纪律
7. **Anthropic SDK 的 stop_reason 枚举**未来可能扩展,`_parse` 里做了白名单检查,遇到新值抛 `LLMProtocolError`,**不要**悄悄 fallback 成 `end_turn`

---

## 5.17 本章交付物清单

- [ ] `app/llm/errors.py`
- [ ] `app/llm/types.py`
- [ ] `app/llm/provider.py`
- [ ] `app/llm/adapters/claude.py`
- [ ] `app/llm/adapters/openai.py`
- [ ] `app/llm/adapters/mock.py`
- [ ] `app/llm/decorators/retry.py` / `trace.py` / `metrics.py` / `rate_limit.py` / `timeout.py`
- [ ] `app/llm/schema_coerce.py`
- [ ] `app/llm/agent_loop.py`
- [ ] `app/llm/client.py`
- [ ] `app/bootstrap.py` 装配追加
- [ ] `tests/unit/llm/*` 覆盖 §5.15.1-5.15.4 全部
- [ ] `tests/integration/test_claude_contract.py`(可选,CI nightly)
- [ ] 03 章 `LLMSimulator` 实际接入 `ctx.llm.call_sync` 后能跑通(回归测试)

---

下一份:[06_LangGraph骨架.md](./06_LangGraph骨架.md)
