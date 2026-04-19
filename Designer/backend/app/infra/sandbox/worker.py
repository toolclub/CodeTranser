"""单 worker 的 SSH 连接池(asyncssh)。

精简版,基于 ChatFlow `sandbox/worker.py` 的核心思路:
  - 多个 SSH 连接组成池,轮转使用,避免单连接 channel 过多
  - exec_command 一次性返回(没有流式 yield;Cascade Phase3 是同步性质,不需要)
  - 30s 内复用过的连接跳过探活,降低延迟
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from app.infra.logging import get_logger

log = get_logger(__name__)

_PROBE_SKIP_SECONDS = 30.0


@dataclass(slots=True)
class ExecuteResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    cwd: str = ""
    timed_out: bool = False
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.error is None


class SSHWorker:
    """单个沙箱 worker 的 SSH 连接池。"""

    def __init__(
        self,
        worker_id: str,
        host: str,
        port: int = 22,
        user: str = "root",
        password: str = "",
        key_file: str = "",
        pool_size: int = 3,
        connect_timeout: float = 10.0,
    ) -> None:
        self.worker_id = worker_id
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._key_file = key_file
        self._pool_size = max(1, pool_size)
        self._connect_timeout = connect_timeout
        self._pool: list[Any] = []
        self._pool_lock = asyncio.Lock()
        self._pool_index = 0
        self._pool_last_used: dict[int, float] = {}

    @property
    def address(self) -> str:
        return f"{self._host}:{self._port}"

    async def connect(self) -> None:
        import asyncssh

        kwargs: dict[str, Any] = {
            "host": self._host,
            "port": self._port,
            "username": self._user,
            "known_hosts": None,
            "connect_timeout": self._connect_timeout,
        }
        if self._key_file:
            kwargs["client_keys"] = [self._key_file]
        if self._password:
            kwargs["password"] = self._password

        self._pool = []
        for _ in range(self._pool_size):
            conn = await asyncssh.connect(**kwargs)
            self._pool.append(conn)
        log.info(
            "ssh_pool_connected",
            worker=self.worker_id,
            host=self.address,
            pool=len(self._pool),
        )

    async def close(self) -> None:
        for conn in self._pool:
            try:
                conn.close()
                await conn.wait_closed()
            except Exception:
                pass
        self._pool.clear()
        self._pool_last_used.clear()

    async def _acquire(self) -> tuple[int, Any]:
        async with self._pool_lock:
            idx = self._pool_index
            self._pool_index = (self._pool_index + 1) % len(self._pool)
            conn = self._pool[idx]
        # 复用近 30s 内用过的连接,跳过探活
        if time.time() - self._pool_last_used.get(idx, 0) > _PROBE_SKIP_SECONDS:
            try:
                await asyncio.wait_for(conn.run("echo ok", check=False), timeout=3.0)
            except Exception:
                # 连接坏了,尝试重连
                conn = await self._reconnect_one(idx)
        return idx, conn

    async def _reconnect_one(self, idx: int) -> Any:
        import asyncssh

        kwargs: dict[str, Any] = {
            "host": self._host,
            "port": self._port,
            "username": self._user,
            "known_hosts": None,
            "connect_timeout": self._connect_timeout,
        }
        if self._password:
            kwargs["password"] = self._password
        if self._key_file:
            kwargs["client_keys"] = [self._key_file]
        try:
            self._pool[idx].close()
        except Exception:
            pass
        new_conn = await asyncssh.connect(**kwargs)
        self._pool[idx] = new_conn
        log.info("ssh_conn_reconnected", worker=self.worker_id, idx=idx)
        return new_conn

    async def exec_command(
        self,
        cmd: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> ExecuteResult:
        t0 = time.time()
        idx, conn = await self._acquire()
        # 拼 cwd:`cd <path> && <cmd>`
        full_cmd = f"cd {cwd} && {cmd}" if cwd else cmd
        try:
            result = await asyncio.wait_for(
                conn.run(full_cmd, check=False),
                timeout=timeout,
            )
            self._pool_last_used[idx] = time.time()
            return ExecuteResult(
                stdout=str(result.stdout or ""),
                stderr=str(result.stderr or ""),
                exit_code=int(result.exit_status or 0),
                duration_ms=int((time.time() - t0) * 1000),
                cwd=cwd or "",
            )
        except asyncio.TimeoutError:
            return ExecuteResult(
                stdout="",
                stderr=f"timeout after {timeout}s",
                exit_code=-1,
                duration_ms=int((time.time() - t0) * 1000),
                cwd=cwd or "",
                timed_out=True,
            )
        except Exception as e:
            log.warning("ssh_exec_error", worker=self.worker_id, error=str(e))
            return ExecuteResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration_ms=int((time.time() - t0) * 1000),
                cwd=cwd or "",
                error=str(e),
            )

    async def healthy(self) -> bool:
        try:
            _, conn = await self._acquire()
            await asyncio.wait_for(conn.run("echo ok", check=False), timeout=3.0)
            return True
        except Exception:
            return False
