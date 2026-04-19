"""跨 pod 的 Run 生命周期协调服务(分布式优先)。

灵感来源:ChatFlow 把 `_stop_events / _active_sessions` 全部升级到 Redis 的经验。
核心 API 全部是幂等的,任何 pod 都可以调用。

三个关键抽象:
  1. **StopRegistry** — 请求停止某个 Run;任何 pod 可发起,所有运行该 Run 的 pod 在下次
     调度点看到 flag 就退出
  2. **SessionRegistry** — 追踪"此刻哪个 worker_id 在跑 run_id",heartbeat 超时自动过期
  3. **Heartbeat** — 长任务 pod 定期续期,方便运维判断是否还活着

设计决策:
  - Redis SET/TTL 作为 source of truth,进程内 dict 只做 **热路径加速缓存**
  - Redis 不可用时全部降级为 noop + warning,系统仍可跑(只是失去跨 pod 协调)
  - 所有 Redis 调用均包 `asyncio.wait_for(timeout=2)`
"""

from __future__ import annotations

import asyncio
import os
import socket
import time
from typing import Any

from app.infra.logging import get_logger

log = get_logger(__name__)

_REDIS_OP_TIMEOUT = 2.0
_STOP_TTL = 600  # 停止请求 10 分钟过期;足够传达 + 不污染
_SESSION_TTL = 60  # session 活跃 TTL;pod 每 20s 续期


def current_worker_id() -> str:
    """生成当前 pod 标识。K8S 下来自 HOSTNAME(pod name);本地回退到 hostname+pid。"""
    return os.environ.get("HOSTNAME") or f"{socket.gethostname()}-{os.getpid()}"


def _stop_key(run_id: str) -> str:
    return f"cascade:run:stop:{run_id}"


def _session_key(run_id: str) -> str:
    return f"cascade:run:session:{run_id}"


class StopRegistry:
    """跨 pod 的 Run 停止信号。

    - `request_stop(run_id)`:任意 pod 设置 flag,所有 pod 的 `is_stopped` 都会看到
    - `is_stopped(run_id)`:热路径(步骤间 / iteration 间)调用,1s 本地缓存防打爆 Redis
    - `clear(run_id)`:Run 结束时清理
    """

    def __init__(self, redis: Any | None) -> None:
        self._r = redis
        # 本地热缓存:{run_id: (value, cached_at)};1s TTL 避免 Redis 打爆
        self._local: dict[str, tuple[bool, float]] = {}
        self._local_ttl = 1.0

    async def request_stop(self, run_id: str) -> bool:
        if self._r is None:
            log.warning("stop_registry_no_redis", run_id=run_id)
            self._local[run_id] = (True, time.time())
            return False
        try:
            await asyncio.wait_for(
                self._r.set(_stop_key(run_id), "1", ex=_STOP_TTL),
                timeout=_REDIS_OP_TIMEOUT,
            )
            self._local[run_id] = (True, time.time())
            return True
        except asyncio.TimeoutError:
            log.warning("stop_registry_timeout", run_id=run_id)
            return False
        except Exception as e:
            log.warning("stop_registry_error", run_id=run_id, error=str(e))
            return False

    async def is_stopped(self, run_id: str) -> bool:
        cached = self._local.get(run_id)
        if cached and (time.time() - cached[1]) < self._local_ttl:
            return cached[0]
        if self._r is None:
            return cached[0] if cached else False
        try:
            raw = await asyncio.wait_for(
                self._r.get(_stop_key(run_id)),
                timeout=_REDIS_OP_TIMEOUT,
            )
            stopped = raw is not None
            self._local[run_id] = (stopped, time.time())
            return stopped
        except asyncio.TimeoutError:
            log.warning("is_stopped_timeout", run_id=run_id)
            return False
        except Exception as e:
            log.warning("is_stopped_error", run_id=run_id, error=str(e))
            return False

    async def clear(self, run_id: str) -> None:
        self._local.pop(run_id, None)
        if self._r is None:
            return
        try:
            await asyncio.wait_for(
                self._r.delete(_stop_key(run_id)),
                timeout=_REDIS_OP_TIMEOUT,
            )
        except Exception as e:
            log.warning("stop_clear_error", run_id=run_id, error=str(e))


class SessionRegistry:
    """跨 pod 的"哪个 worker 在跑哪个 Run"登记表。

    用法:
        async with registry.session(run_id):   # 自动 register + heartbeat + cleanup
            await pipeline.ainvoke(...)

    运维可以从 Redis 看到 `cascade:run:session:r_xxx = worker_id`,DB 同步有 `t_workflow_run.worker_id`。
    """

    def __init__(self, redis: Any | None, worker_id: str | None = None) -> None:
        self._r = redis
        self._wid = worker_id or current_worker_id()

    @property
    def worker_id(self) -> str:
        return self._wid

    async def register(self, run_id: str) -> None:
        if self._r is None:
            return
        try:
            await asyncio.wait_for(
                self._r.set(_session_key(run_id), self._wid, ex=_SESSION_TTL),
                timeout=_REDIS_OP_TIMEOUT,
            )
        except Exception as e:
            log.warning("session_register_error", run_id=run_id, error=str(e))

    async def heartbeat(self, run_id: str) -> None:
        """续期 TTL。长任务每 < _SESSION_TTL 秒调一次。"""
        if self._r is None:
            return
        try:
            await asyncio.wait_for(
                self._r.expire(_session_key(run_id), _SESSION_TTL),
                timeout=_REDIS_OP_TIMEOUT,
            )
        except Exception as e:
            log.warning("session_heartbeat_error", run_id=run_id, error=str(e))

    async def who_owns(self, run_id: str) -> str | None:
        if self._r is None:
            return None
        try:
            raw = await asyncio.wait_for(
                self._r.get(_session_key(run_id)),
                timeout=_REDIS_OP_TIMEOUT,
            )
            return str(raw) if raw else None
        except Exception as e:
            log.warning("session_who_owns_error", run_id=run_id, error=str(e))
            return None

    async def release(self, run_id: str) -> None:
        if self._r is None:
            return
        try:
            await asyncio.wait_for(
                self._r.delete(_session_key(run_id)),
                timeout=_REDIS_OP_TIMEOUT,
            )
        except Exception as e:
            log.warning("session_release_error", run_id=run_id, error=str(e))
