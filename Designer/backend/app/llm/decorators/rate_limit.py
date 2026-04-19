import asyncio

from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse


class RateLimitDecorator:
    """全局并发上限。超过 max_concurrency 则阻塞等待。"""

    def __init__(self, inner: LLMProvider, *, max_concurrency: int) -> None:
        self._inner = inner
        self.name = inner.name
        self._sem = asyncio.Semaphore(max_concurrency)

    async def call(self, req: LLMRequest) -> LLMResponse:
        async with self._sem:
            return await self._inner.call(req)
