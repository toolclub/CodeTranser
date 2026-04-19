from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession


class SqlRepoBase(ABC):
    """所有 SQL 实现 Repo 的共享基类。"""

    __slots__ = ("_s",)

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    @property
    def session(self) -> AsyncSession:
        return self._s
