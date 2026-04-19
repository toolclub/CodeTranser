"""SandboxManager:多 worker 健康检查 + run_id 亲和。

设计:
  - 每 30s 健康检查,故障 worker 摘除,恢复自动加回
  - run_id 第一次 acquire 时分配 worker(选活跃 session 最少),登记到 Redis
    `cascade:sandbox:run:{run_id} -> worker_id`(TTL 1h)
  - 后续同一 run_id 的 acquire 落到同一 worker(保持文件上下文)
  - K8S 多副本时,不同 cascade-backend pod 通过 Redis 看到相同的"哪个 run 在哪个 sandbox worker"

降级:`SANDBOX_WORKERS` 为空 → manager.available=False;调用方静默返回 unavailable 错误。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.infra.logging import get_logger
from app.infra.sandbox.worker import ExecuteResult, SSHWorker

log = get_logger(__name__)

_HEALTH_CHECK_INTERVAL = 30.0
_REDIS_TIMEOUT = 2.0
_RUN_TTL = 3600  # 1h


def _run_session_key(run_id: str) -> str:
    return f"cascade:sandbox:run:{run_id}"


class SandboxManager:
    """跨 pod 的沙箱调度器。"""

    def __init__(self, redis: Any | None = None) -> None:
        self._redis = redis
        self._workers: dict[str, SSHWorker] = {}
        self._healthy: set[str] = set()
        self._sessions: dict[str, str] = {}  # 进程内热缓存 run_id → worker_id
        self._health_task: asyncio.Task[None] | None = None
        self._timeout_default: float = 30.0
        self._initialized = False

    @property
    def available(self) -> bool:
        return self._initialized and len(self._healthy) > 0

    async def init(
        self,
        workers_config: list[dict[str, Any]],
        *,
        timeout: float = 30.0,
    ) -> None:
        self._timeout_default = timeout
        for cfg in workers_config:
            wid = cfg.get("id") or f"sandbox-{len(self._workers)}"
            worker = SSHWorker(
                worker_id=wid,
                host=cfg["host"],
                port=int(cfg.get("port", 22)),
                user=cfg.get("user", "root"),
                password=cfg.get("password", ""),
                key_file=cfg.get("key_file", ""),
                pool_size=int(cfg.get("pool_size", 3)),
            )
            self._workers[wid] = worker
            try:
                await worker.connect()
                self._healthy.add(wid)
                log.info("sandbox_worker_online", worker=wid, host=worker.address)
            except Exception as e:
                log.warning(
                    "sandbox_worker_connect_failed",
                    worker=wid,
                    host=worker.address,
                    error=str(e),
                )
        self._initialized = True
        if not self._healthy:
            log.warning("sandbox_no_healthy_workers")
            return
        self._health_task = asyncio.create_task(self._health_loop())

    async def shutdown(self) -> None:
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except (asyncio.CancelledError, Exception):
                pass
        for w in self._workers.values():
            await w.close()

    async def _health_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(_HEALTH_CHECK_INTERVAL)
                for wid, w in list(self._workers.items()):
                    ok = await w.healthy()
                    if ok and wid not in self._healthy:
                        self._healthy.add(wid)
                        log.info("sandbox_worker_recovered", worker=wid)
                    elif not ok and wid in self._healthy:
                        self._healthy.discard(wid)
                        log.warning("sandbox_worker_unhealthy", worker=wid)
            except asyncio.CancelledError:
                return
            except Exception as e:
                log.warning("sandbox_health_loop_error", error=str(e))

    async def _pick_worker_for_run(self, run_id: str) -> SSHWorker | None:
        """优先按 Redis/进程缓存找已绑定 worker;否则按"活跃 session 最少"分配。"""
        # 1. 进程内缓存
        wid = self._sessions.get(run_id)
        if wid and wid in self._healthy:
            return self._workers[wid]
        # 2. Redis 跨 pod 共享
        if self._redis is not None:
            try:
                raw = await asyncio.wait_for(
                    self._redis.get(_run_session_key(run_id)),
                    timeout=_REDIS_TIMEOUT,
                )
                if raw:
                    wid = str(raw)
                    if wid in self._healthy:
                        self._sessions[run_id] = wid
                        return self._workers[wid]
            except asyncio.TimeoutError:
                log.warning("sandbox_session_redis_timeout", run_id=run_id)
            except Exception as e:
                log.warning("sandbox_session_redis_error", run_id=run_id, error=str(e))
        # 3. 新分配:活跃 session 最少的健康 worker
        if not self._healthy:
            return None
        load: dict[str, int] = {wid: 0 for wid in self._healthy}
        for v in self._sessions.values():
            if v in load:
                load[v] += 1
        best = min(load, key=lambda k: load[k])
        self._sessions[run_id] = best
        # 登记 Redis
        if self._redis is not None:
            try:
                await asyncio.wait_for(
                    self._redis.set(_run_session_key(run_id), best, ex=_RUN_TTL),
                    timeout=_REDIS_TIMEOUT,
                )
            except Exception as e:
                log.warning("sandbox_session_register_failed", run_id=run_id, error=str(e))
        return self._workers[best]

    async def exec_for_run(
        self,
        run_id: str,
        cmd: str,
        *,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> ExecuteResult:
        """供 Phase3 调用:按 run_id 亲和找到 worker,exec 命令。"""
        if not self.available:
            return ExecuteResult(
                stdout="",
                stderr="sandbox unavailable",
                exit_code=-1,
                duration_ms=0,
                error="sandbox_unavailable",
            )
        worker = await self._pick_worker_for_run(run_id)
        if worker is None:
            return ExecuteResult(
                stdout="",
                stderr="no healthy sandbox worker",
                exit_code=-1,
                duration_ms=0,
                error="no_worker",
            )
        return await worker.exec_command(
            cmd, cwd=cwd, timeout=timeout or self._timeout_default
        )

    async def release_run(self, run_id: str) -> None:
        """Run 结束时释放绑定(不删 sandbox 内的文件,后台清理任务做)。"""
        self._sessions.pop(run_id, None)
        if self._redis is not None:
            try:
                await asyncio.wait_for(
                    self._redis.delete(_run_session_key(run_id)),
                    timeout=_REDIS_TIMEOUT,
                )
            except Exception as e:
                log.warning("sandbox_release_failed", run_id=run_id, error=str(e))

    def status(self) -> dict[str, Any]:
        return {
            "total_workers": len(self._workers),
            "healthy_workers": len(self._healthy),
            "active_sessions": len(self._sessions),
            "workers": [
                {
                    "id": wid,
                    "address": w.address,
                    "healthy": wid in self._healthy,
                    "sessions": sum(1 for v in self._sessions.values() if v == wid),
                }
                for wid, w in self._workers.items()
            ],
        }
