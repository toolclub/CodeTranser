import asyncio
import threading
from typing import Any

from app.config import Settings
from app.llm.decorators.metrics import MetricsDecorator
from app.llm.decorators.rate_limit import RateLimitDecorator
from app.llm.decorators.retry import RetryDecorator
from app.llm.decorators.timeout import TimeoutDecorator
from app.llm.decorators.trace import LLMTraceContext, TraceDecorator
from app.llm.provider import LLMProvider
from app.llm.schema_coerce import coerce_json_output
from app.llm.types import LLMRequest, LLMResponse


def build_provider(settings: Settings) -> LLMProvider:
    if settings.LLM_PROVIDER == "claude":
        from app.llm.adapters.claude import ClaudeAdapter

        return ClaudeAdapter(
            api_key=settings.LLM_API_KEY,
            default_model=settings.LLM_MODEL_DEFAULT,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )
    if settings.LLM_PROVIDER == "openai":
        from app.llm.adapters.openai import OpenAIAdapter

        return OpenAIAdapter(
            api_key=settings.LLM_API_KEY,
            default_model=settings.LLM_MODEL_DEFAULT,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
            base_url=settings.LLM_BASE_URL,
        )
    if settings.LLM_PROVIDER == "mock":
        from app.llm.adapters.mock import MockProvider

        return MockProvider([])
    raise ValueError(f"unknown LLM_PROVIDER {settings.LLM_PROVIDER}")


class LLMClient:
    """对外唯一入口。

    装饰器链(由里到外):
        raw provider → Retry → Timeout → Metrics → Trace → RateLimit

    调用时 RateLimit 最先生效,Retry 最后才真正触发底层。
    """

    def __init__(
        self,
        settings: Settings,
        *,
        provider: LLMProvider | None = None,
    ) -> None:
        self.trace_ctx = LLMTraceContext()
        base = provider or build_provider(settings)
        chain: LLMProvider = base
        chain = RetryDecorator(chain, max_attempts=3)
        chain = TimeoutDecorator(chain, default_timeout=settings.LLM_TIMEOUT_SECONDS)
        chain = MetricsDecorator(chain)
        chain = TraceDecorator(chain, self.trace_ctx)
        chain = RateLimitDecorator(chain, max_concurrency=settings.LLM_MAX_CONCURRENCY)
        self._chain = chain
        self._base_name = base.name

    async def call(self, req: LLMRequest) -> LLMResponse:
        if req.output_schema is not None:
            return await coerce_json_output(self._chain, req)
        return await self._chain.call(req)

    def call_sync(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        output_schema: dict[str, Any] | None = None,
        node_name: str = "sync",
        **kw: Any,
    ) -> LLMResponse:
        req = LLMRequest(
            system=system,
            user=user,
            model=model,
            output_schema=output_schema,
            node_name=node_name,
            **kw,
        )
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.call(req))
        return _run_in_background_loop(self.call(req))

    @property
    def provider_name(self) -> str:
        return self._base_name


# 进程级后台 loop:给 call_sync 在已有 event loop 场景下使用
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


def _run_in_background_loop(coro: Any) -> Any:
    loop = _ensure_bg_loop()
    fut = asyncio.run_coroutine_threadsafe(coro, loop)
    return fut.result()
