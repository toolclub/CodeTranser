from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import select

from app.models.mysql.app_setting import AppSettingRow
from app.repositories.base import SqlRepoBase


class AppSettingRepo(ABC):
    @abstractmethod
    async def get(self, key: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def set(self, key: str, value: dict[str, Any], note: str, updated_by: int) -> None: ...


class SqlAppSettingRepo(SqlRepoBase, AppSettingRepo):
    async def get(self, key: str) -> dict[str, Any] | None:
        r = await self._s.execute(select(AppSettingRow).where(AppSettingRow.key == key))
        row = r.scalar_one_or_none()
        return row.value if row else None

    async def set(
        self, key: str, value: dict[str, Any], note: str = "", updated_by: int = 0
    ) -> None:
        r = await self._s.execute(select(AppSettingRow).where(AppSettingRow.key == key))
        row = r.scalar_one_or_none()
        if row is None:
            self._s.add(AppSettingRow(key=key, value=value, note=note, updated_by=updated_by))
        else:
            row.value = value
            row.note = note
            row.updated_by = updated_by
