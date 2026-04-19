"""SandboxClient:Phase3 / 业务层使用的最小 facade。

包装 SandboxManager,提供常用便捷方法:exec / write_file / read_file / mkdir / cleanup。
所有命令注入安全靠 `shlex.quote`(对齐 ChatFlow `sandbox_download` 修复)。
"""

from __future__ import annotations

import shlex
from typing import Any

from app.infra.sandbox.manager import SandboxManager
from app.infra.sandbox.worker import ExecuteResult


class SandboxClient:
    def __init__(self, manager: SandboxManager) -> None:
        self._mgr = manager

    @property
    def available(self) -> bool:
        return self._mgr.available

    async def exec(
        self,
        run_id: str,
        cmd: str,
        *,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> ExecuteResult:
        """执行任意 shell 命令。注意:cmd 由调用方负责拼接,内部不再 shlex.quote。"""
        return await self._mgr.exec_for_run(run_id, cmd, cwd=cwd, timeout=timeout)

    async def mkdir(self, run_id: str, path: str) -> ExecuteResult:
        safe = shlex.quote(self._safe_path(path))
        return await self._mgr.exec_for_run(run_id, f"mkdir -p {safe}")

    async def write_file(
        self,
        run_id: str,
        path: str,
        content: str,
    ) -> ExecuteResult:
        """写文件(用 base64 + decode,避免 shell 转义问题)。"""
        import base64

        b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        safe = shlex.quote(self._safe_path(path))
        cmd = f"mkdir -p $(dirname {safe}) && echo {shlex.quote(b64)} | base64 -d > {safe}"
        return await self._mgr.exec_for_run(run_id, cmd)

    async def read_file(
        self,
        run_id: str,
        path: str,
        *,
        max_bytes: int = 65536,
    ) -> ExecuteResult:
        safe = shlex.quote(self._safe_path(path))
        return await self._mgr.exec_for_run(
            run_id, f"head -c {max_bytes} {safe}"
        )

    async def cleanup(self, run_id: str, *, sandbox_root: str = "/sandbox") -> ExecuteResult:
        safe = shlex.quote(f"{sandbox_root}/{run_id}")
        # 防误删:必须包含 run_id 前缀
        return await self._mgr.exec_for_run(run_id, f"rm -rf {safe}")

    async def release(self, run_id: str) -> None:
        await self._mgr.release_run(run_id)

    @staticmethod
    def _safe_path(path: str) -> str:
        """禁止绝对路径以外的 .. / 注入。"""
        if ".." in path.split("/"):
            raise ValueError(f"path contains '..': {path}")
        return path

    def status(self) -> dict[str, Any]:
        return self._mgr.status()
