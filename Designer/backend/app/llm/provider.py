from typing import Protocol, runtime_checkable

from app.llm.types import LLMRequest, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """所有具体供应商 + 装饰器都实现此协议(结构类型,无需继承)。"""

    name: str

    async def call(self, req: LLMRequest) -> LLMResponse: ...
