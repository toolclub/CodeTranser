from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import select

from app.domain.errors import NotFound
from app.models.mysql.user import UserRow
from app.repositories.base import SqlRepoBase


class UserRepo(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> dict[str, Any] | None: ...

    @abstractmethod
    async def get_by_external(self, external_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def upsert_from_sso(self, profile: dict[str, Any]) -> dict[str, Any]: ...


class SqlUserRepo(SqlRepoBase, UserRepo):
    async def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        r = await self._s.execute(select(UserRow).where(UserRow.id == user_id))
        row = r.scalar_one_or_none()
        return _to_dict(row) if row else None

    async def get_by_external(self, external_id: str) -> dict[str, Any]:
        r = await self._s.execute(select(UserRow).where(UserRow.external_id == external_id))
        row = r.scalar_one_or_none()
        if row is None:
            raise NotFound(f"user {external_id}")
        return _to_dict(row)

    async def upsert_from_sso(self, profile: dict[str, Any]) -> dict[str, Any]:
        external_id = profile["external_id"]
        r = await self._s.execute(select(UserRow).where(UserRow.external_id == external_id))
        row = r.scalar_one_or_none()
        if row is None:
            row = UserRow(
                external_id=external_id,
                username=profile.get("username", external_id),
                display_name=profile.get("display_name", external_id),
                email=profile.get("email", ""),
                is_admin=bool(profile.get("is_admin", False)),
            )
            self._s.add(row)
            await self._s.flush()
        else:
            row.username = profile.get("username", row.username)
            row.display_name = profile.get("display_name", row.display_name)
            row.email = profile.get("email", row.email)
            row.is_admin = bool(profile.get("is_admin", row.is_admin))
        return _to_dict(row)


def _to_dict(row: UserRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "external_id": row.external_id,
        "username": row.username,
        "display_name": row.display_name,
        "email": row.email,
        "is_admin": bool(row.is_admin),
    }


class AdminRepo(ABC):
    @abstractmethod
    async def is_admin(self, external_id: str) -> bool: ...

    @abstractmethod
    async def grant(self, external_id: str, granted_by: str) -> None: ...


class SqlAdminRepo(SqlRepoBase, AdminRepo):
    async def is_admin(self, external_id: str) -> bool:
        from app.models.mysql.admin_user import AdminUserRow

        r = await self._s.execute(
            select(AdminUserRow.id).where(AdminUserRow.external_id == external_id)
        )
        return r.scalar_one_or_none() is not None

    async def grant(self, external_id: str, granted_by: str) -> None:
        from app.models.mysql.admin_user import AdminUserRow

        existing = await self._s.execute(
            select(AdminUserRow.id).where(AdminUserRow.external_id == external_id)
        )
        if existing.scalar_one_or_none() is not None:
            return
        self._s.add(AdminUserRow(external_id=external_id, granted_by=granted_by))
