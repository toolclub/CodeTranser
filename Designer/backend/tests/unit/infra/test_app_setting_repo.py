import pytest

from app.repositories.app_setting_repo import SqlAppSettingRepo


@pytest.mark.asyncio
async def test_set_then_get(db) -> None:
    repo = SqlAppSettingRepo(db)
    await repo.set("feature.x", {"v": 42}, note="enable x", updated_by=1)
    got = await repo.get("feature.x")
    assert got == {"v": 42}


@pytest.mark.asyncio
async def test_get_missing_returns_none(db) -> None:
    repo = SqlAppSettingRepo(db)
    assert await repo.get("nope") is None
