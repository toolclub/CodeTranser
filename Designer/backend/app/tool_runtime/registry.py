from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from typing import Any

from app.domain.tool.tool import NodeTemplate, Scope
from app.infra.logging import get_logger
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.factory import SimulatorFactory
from app.tool_runtime.loader import ToolLoader, to_anthropic_tool_spec

log = get_logger(__name__)

_REDIS_OP_TIMEOUT = 2.0


class _LruTtlCache:
    """简单 LRU + TTL(ChatFlow 教训:进程内 dict 不加上限会内存泄漏)。

    - capacity: 最多存多少条(LRU 淘汰)
    - ttl: 秒;0 = 不过期
    """

    def __init__(self, capacity: int = 512, ttl: float = 0.0) -> None:
        self._cap = max(1, capacity)
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        val, ts = item
        if self._ttl and (time.time() - ts) > self._ttl:
            del self._data[key]
            return None
        # LRU:hit 时移到末尾
        self._data.move_to_end(key)
        return val

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (value, time.time())
        self._data.move_to_end(key)
        while len(self._data) > self._cap:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


class ToolRegistry:
    """单例节点模板注册表。

    - 懒加载 + 进程内 **LRU + TTL** 缓存(ChatFlow "永远不信任进程内数据" 实践)
    - Redis pub/sub 让多实例清缓存(热重载);Redis 调用均包 `wait_for(timeout=2)`
    - simulator 缓存复用同一实例
    """

    CHANNEL = "tool_registry:invalidate"

    def __init__(
        self,
        loader: ToolLoader,
        factory: SimulatorFactory,
        redis: Any | None = None,
        *,
        cache_size: int = 512,
        cache_ttl: float = 300.0,
    ) -> None:
        self._loader = loader
        self._factory = factory
        self._redis = redis
        self._cache_tpl = _LruTtlCache(cache_size, cache_ttl)
        self._cache_sim = _LruTtlCache(cache_size, cache_ttl)
        self._lock = asyncio.Lock()
        self._listener_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._redis is None:
            return
        try:
            pubsub = self._redis.pubsub()
            await asyncio.wait_for(pubsub.subscribe(self.CHANNEL), timeout=_REDIS_OP_TIMEOUT)
        except asyncio.TimeoutError:
            log.warning("tool_registry_subscribe_timeout")
            return
        except Exception as e:
            log.warning("tool_registry_pubsub_unavailable", error=str(e))
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
                    self._cache_tpl.clear()
                    self._cache_sim.clear()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("tool_registry_listen_error", error=str(e))

    @staticmethod
    def _key(name: str, owner_id: int | None, version: int | None) -> str:
        return f"{name}|{owner_id or 0}|{version or 0}"

    async def get(
        self,
        *,
        name: str,
        owner_id: int | None = None,
        scope: Scope = Scope.GLOBAL,
        version: int | None = None,
    ) -> NodeTemplate:
        k = self._key(name, owner_id, version)
        cached = self._cache_tpl.get(k)
        if cached is not None:
            return cached
        async with self._lock:
            cached = self._cache_tpl.get(k)
            if cached is not None:
                return cached
            t = await self._loader.load(
                name=name, owner_id=owner_id, scope=scope, version=version
            )
            self._cache_tpl.set(k, t)
            return t

    async def get_by_id(self, template_id: str, version: int | None = None) -> NodeTemplate:
        t = await self._loader.load_by_id(template_id, version)
        self._cache_tpl.set(self._key(t.name, t.owner_id, version), t)
        return t

    def simulator_of(self, tpl: NodeTemplate) -> ToolSimulator:
        k = f"{tpl.name}|{tpl.version}|{tpl.owner_id or 0}"
        s = self._cache_sim.get(k)
        if s is None:
            s = self._factory.create(tpl)
            self._cache_sim.set(k, s)
        return s

    def for_llm(self, templates: list[NodeTemplate]) -> list[dict[str, Any]]:
        return [to_anthropic_tool_spec(t) for t in templates]

    async def invalidate(self, template_id: str | None = None) -> None:
        self._cache_tpl.clear()
        self._cache_sim.clear()
        if self._redis is not None:
            try:
                await asyncio.wait_for(
                    self._redis.publish(self.CHANNEL, template_id or "*"),
                    timeout=_REDIS_OP_TIMEOUT,
                )
            except asyncio.TimeoutError:
                log.warning("tool_registry_publish_timeout")
            except Exception as e:
                log.warning("tool_registry_publish_failed", error=str(e))
