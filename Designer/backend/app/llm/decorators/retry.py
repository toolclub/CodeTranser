import asyncio
import random

from app.infra.logging import get_logger
from app.llm.errors import LLMUnavailable, TransientLLMError
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse

log = get_logger(__name__)


class RetryDecorator:
    """指数退避 + 抖动;仅对 TransientLLMError 重试。"""

    def __init__(
        self,
        inner: LLMProvider,
        *,
        max_attempts: int = 3,
        base: float = 1.0,
        cap: float = 30.0,
    ) -> None:
        self._inner = inner
        self.name = inner.name
        self._max = max_attempts
        self._base = base
        self._cap = cap

    async def call(self, req: LLMRequest) -> LLMResponse:
        last_err: Exception | None = None
        for i in range(self._max):
            try:
                return await self._inner.call(req)
            except TransientLLMError as e:
                last_err = e
                if i == self._max - 1:
                    break
                delay = min(self._cap, self._base * (2**i)) + random.random()
                if e.retry_after is not None:
                    delay = max(delay, e.retry_after)
                log.warning(
                    "llm_retry",
                    attempt=i + 1,
                    max=self._max,
                    delay=delay,
                    err=str(e),
                )
                await asyncio.sleep(delay)
        raise LLMUnavailable(f"after {self._max} retries: {last_err}")
