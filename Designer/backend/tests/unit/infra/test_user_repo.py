import pytest

from app.repositories.user_repo import SqlAdminRepo, SqlUserRepo


@pytest.mark.asyncio
async def test_upsert_creates_then_updates(db) -> None:
    repo = SqlUserRepo(db)
    u1 = await repo.upsert_from_sso(
        {"external_id": "u_abc", "username": "abc", "display_name": "A B", "email": "a@b.com"}
    )
    assert u1["id"] > 0
    u2 = await repo.upsert_from_sso(
        {"external_id": "u_abc", "username": "abc", "display_name": "Updated", "email": "a@b.com"}
    )
    assert u2["id"] == u1["id"]
    assert u2["display_name"] == "Updated"


@pytest.mark.asyncio
async def test_admin_grant_is_idempotent(db) -> None:
    repo = SqlAdminRepo(db)
    await repo.grant("u_admin", "cli")
    await repo.grant("u_admin", "cli")  # 不抛
    assert await repo.is_admin("u_admin") is True
    assert await repo.is_admin("u_someone_else") is False
