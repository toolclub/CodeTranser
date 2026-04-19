import asyncio

from app.llm.errors import LLMTimeout
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse


class TimeoutDecorator:
    """per-request 软超时。provider 自己也有超时,此处是兜底。"""

    def __init__(self, inner: LLMProvider, *, default_timeout: float) -> None:
        self._inner = inner
        self.name = inner.name
        self._default = default_timeout

    async def call(self, req: LLMRequest) -> LLMResponse:
        t = req.timeout_seconds or self._default
        try:
            return await asyncio.wait_for(self._inner.call(req), timeout=t)
        except asyncio.TimeoutError as e:
            raise LLMTimeout(f"timeout after {t}s") from e
