import asyncio
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.session import session_scope
from app.infra.logging import get_logger
from app.repositories.app_setting_repo import SqlAppSettingRepo

log = get_logger(__name__)


class SettingsService:
    """运行时动态配置服务。

    - `get(key, default)`:10s 本地缓存 + DB 兜底
    - `set(key, value, user_id, note)`:写 DB + 发 Redis pub/sub 让所有实例清缓存
    - Redis 不可用时降级为纯 DB(仍可工作,仅缺失跨实例同步)
    """

    CHANNEL = "app_setting:invalidate"
    TTL = 10.0

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis: Any | None,
    ) -> None:
        self._sf = session_factory
        self._redis = redis
        self._cache: dict[str, tuple[Any, float]] = {}
        self._listener_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._redis is None:
            return
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(self.CHANNEL)
        except Exception as e:
            log.warning("settings_service_pubsub_unavailable", error=str(e))
            return
        self._listener_task = asyncio.create_task(self._listen(pubsub))

    async def stop(self) -> None:
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except (asyncio.CancelledError, Exception):
                pass
            self._listener_task = None

    async def _listen(self, pubsub: Any) -> None:
        try:
            async for msg in pubsub.listen():
                if msg.get("type") == "message":
                    key = msg.get("data")
                    if isinstance(key, str):
                        self._cache.pop(key, None)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("settings_pubsub_listen_error", error=str(e))

    async def get(self, key: str, default: Any = None) -> Any:
        cached = self._cache.get(key)
        if cached and (time.time() - cached[1]) < self.TTL:
            return cached[0]
        async with session_scope(self._sf) as s:
            raw = await SqlAppSettingRepo(s).get(key)
        value = raw.get("v", default) if raw else default
        self._cache[key] = (value, time.time())
        return value

    async def set(
        self, key: str, value: Any, user_id: int = 0, note: str = ""
    ) -> None:
        async with session_scope(self._sf) as s:
            await SqlAppSettingRepo(s).set(key, {"v": value}, note=note, updated_by=user_id)
        self._cache.pop(key, None)
        if self._redis is not None:
            try:
                await asyncio.wait_for(self._redis.publish(self.CHANNEL, key), timeout=2.0)
            except asyncio.TimeoutError:
                log.warning("settings_publish_timeout", key=key)
            except Exception as e:
                log.warning("settings_publish_failed", key=key, error=str(e))
