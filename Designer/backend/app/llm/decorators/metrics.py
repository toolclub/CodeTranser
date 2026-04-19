from app.infra.metrics import LLM_CALLS, LLM_TOKENS
from app.llm.provider import LLMProvider
from app.llm.types import LLMRequest, LLMResponse


class MetricsDecorator:
    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.name = inner.name

    async def call(self, req: LLMRequest) -> LLMResponse:
        resp = await self._inner.call(req)
        LLM_CALLS.labels(model=resp.model, node_name=req.node_name).inc()
        LLM_TOKENS.labels(model=resp.model, kind="input").inc(resp.usage.input_tokens)
        LLM_TOKENS.labels(model=resp.model, kind="output").inc(resp.usage.output_tokens)
        return resp
