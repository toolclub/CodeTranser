import asyncio

import pytest

from app.llm.adapters.mock import MockProvider, MockStep
from app.llm.decorators.metrics import MetricsDecorator
from app.llm.decorators.rate_limit import RateLimitDecorator
from app.llm.decorators.retry import RetryDecorator
from app.llm.decorators.timeout import TimeoutDecorator
from app.llm.decorators.trace import LLMTraceContext, TraceDecorator
from app.llm.errors import LLMTimeout, LLMUnavailable, TransientLLMError
from app.llm.types import LLMRequest


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient() -> None:
    mp = MockProvider(
        [
            MockStep(match={"any": True}, raise_exception=TransientLLMError("x")),
            MockStep(match={"any": True}, raise_exception=TransientLLMError("x")),
            MockStep(match={"any": True}, text="ok"),
        ]
    )
    dec = RetryDecorator(mp, max_attempts=3, base=0.01, cap=0.01)
    r = await dec.call(LLMRequest(system="", user="x"))
    assert r.text == "ok"


@pytest.mark.asyncio
async def test_retry_gives_up_after_max() -> None:
    mp = MockProvider([MockStep(match={"any": True}, raise_exception=TransientLLMError("x"))] * 3)
    dec = RetryDecorator(mp, max_attempts=3, base=0.01, cap=0.01)
    with pytest.raises(LLMUnavailable):
        await dec.call(LLMRequest(system="", user="x"))


@pytest.mark.asyncio
async def test_retry_does_not_retry_non_transient() -> None:
    mp = MockProvider([MockStep(match={"any": True}, raise_exception=RuntimeError("boom"))])
    dec = RetryDecorator(mp, max_attempts=3, base=0.01)
    with pytest.raises(RuntimeError):
        await dec.call(LLMRequest(system="", user="x"))


class _SlowProvider:
    name = "slow"

    async def call(self, req: LLMRequest):  # type: ignore[no-untyped-def]
        await asyncio.sleep(5)
        raise AssertionError("should not reach")


@pytest.mark.asyncio
async def test_timeout_raises() -> None:
    dec = TimeoutDecorator(_SlowProvider(), default_timeout=0.05)
    with pytest.raises(LLMTimeout):
        await dec.call(LLMRequest(system="", user="x"))


@pytest.mark.asyncio
async def test_metrics_counter_inc() -> None:
    mp = MockProvider([MockStep(match={"any": True}, text="x")])
    dec = MetricsDecorator(mp)
    await dec.call(LLMRequest(system="", user="x", node_name="t"))


@pytest.mark.asyncio
async def test_rate_limit_enforces_concurrency() -> None:
    running = 0
    max_running = 0

    class _P:
        name = "p"

        async def call(self, req: LLMRequest):  # type: ignore[no-untyped-def]
            nonlocal running, max_running
            running += 1
            max_running = max(max_running, running)
            await asyncio.sleep(0.05)
            running -= 1
            mp = MockProvider([MockStep(match={"any": True}, text="x")])
            return await mp.call(req)

    dec = RateLimitDecorator(_P(), max_concurrency=2)
    await asyncio.gather(
        *[dec.call(LLMRequest(system="", user=str(i))) for i in range(5)]
    )
    assert max_running <= 2


@pytest.mark.asyncio
async def test_trace_scope_collects_entries() -> None:
    mp = MockProvider(
        [
            MockStep(match={"any": True}, text="r1"),
            MockStep(match={"any": True}, text="r2"),
        ]
    )
    ctx = LLMTraceContext()
    dec = TraceDecorator(mp, ctx)
    ctx.begin_scope()
    await dec.call(LLMRequest(system="s", user="u1", node_name="a"))
    await dec.call(LLMRequest(system="s", user="u2", node_name="b"))
    entries = ctx.end_scope()
    assert len(entries) == 2
    assert {e["node_name"] for e in entries} == {"a", "b"}


@pytest.mark.asyncio
async def test_trace_outside_scope_silent() -> None:
    mp = MockProvider([MockStep(match={"any": True}, text="x")])
    ctx = LLMTraceContext()
    dec = TraceDecorator(mp, ctx)
    # 未 begin_scope,不应报错
    await dec.call(LLMRequest(system="", user="u"))
    assert ctx.snapshot() == []
