from typing import Any

import pytest

from app.infra.run_control import SessionRegistry, StopRegistry, current_worker_id


class _FakeRedis:
    """最小内存实现,模拟 redis.asyncio.Redis 的 get/set/delete/expire。"""

    def __init__(self) -> None:
        self._kv: dict[str, str] = {}

    async def set(self, k: str, v: str, ex: int | None = None) -> bool:
        self._kv[k] = v
        return True

    async def get(self, k: str) -> str | None:
        return self._kv.get(k)

    async def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self._kv:
                del self._kv[k]
                n += 1
        return n

    async def expire(self, k: str, _t: int) -> bool:
        return k in self._kv


@pytest.mark.asyncio
async def test_stop_registry_noop_without_redis_still_caches_local() -> None:
    reg = StopRegistry(redis=None)
    assert await reg.is_stopped("r_1") is False
    await reg.request_stop("r_1")
    assert await reg.is_stopped("r_1") is True


@pytest.mark.asyncio
async def test_stop_registry_round_trip_via_redis() -> None:
    redis = _FakeRedis()
    reg = StopRegistry(redis=redis)
    assert await reg.is_stopped("r_42") is False
    await reg.request_stop("r_42")
    # 不同实例也能看到(跨 pod 语义)
    other = StopRegistry(redis=redis)
    assert await other.is_stopped("r_42") is True
    await reg.clear("r_42")
    assert "cascade:run:stop:r_42" not in redis._kv


@pytest.mark.asyncio
async def test_session_registry_records_worker_id() -> None:
    redis = _FakeRedis()
    reg = SessionRegistry(redis, worker_id="pod-a")
    await reg.register("r_1")
    assert await reg.who_owns("r_1") == "pod-a"
    # 另一个 pod 同样能看到
    reg_b = SessionRegistry(redis, worker_id="pod-b")
    assert await reg_b.who_owns("r_1") == "pod-a"


def test_current_worker_id_from_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOSTNAME", "cascade-web-xyz")
    assert current_worker_id() == "cascade-web-xyz"


def test_current_worker_id_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOSTNAME", raising=False)
    wid = current_worker_id()
    assert "-" in wid  # hostname-pid
