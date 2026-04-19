from abc import ABC, abstractmethod
from typing import Any, Sequence


class ReviewRepo(ABC):
    @abstractmethod
    async def create(self, run_id: str, reviewer_id: int) -> dict[str, Any]: ...

    @abstractmethod
    async def get(self, review_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def list_by_run(self, run_id: str) -> Sequence[dict[str, Any]]: ...


class CommentRepo(ABC):
    @abstractmethod
    async def insert(self, comment: dict[str, Any]) -> None: ...

    @abstractmethod
    async def list_by_review(self, review_id: str) -> Sequence[dict[str, Any]]: ...
