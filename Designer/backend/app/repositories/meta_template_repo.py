from abc import ABC, abstractmethod
from typing import Any


class MetaTemplateRepo(ABC):
    """元模板读写(单例 id=1)。03 章落地。"""

    @abstractmethod
    async def get(self) -> dict[str, Any]: ...

    @abstractmethod
    async def update(self, content: dict[str, Any], note: str, updated_by: int) -> dict[str, Any]: ...
