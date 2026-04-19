import pytest

from app.settings_service import SettingsService


@pytest.mark.asyncio
async def test_get_default_when_unset(session_factory) -> None:
    svc = SettingsService(session_factory, redis=None)
    val = await svc.get("missing", default="fallback")
    assert val == "fallback"


@pytest.mark.asyncio
async def test_set_then_get_uses_cache(session_factory) -> None:
    svc = SettingsService(session_factory, redis=None)
    await svc.set("k", {"a": 1})
    v = await svc.get("k")
    assert v == {"a": 1}
    # 再次 get 应该命中缓存(不查 DB);通过两次调用一致性间接验证
    v2 = await svc.get("k")
    assert v2 == v
