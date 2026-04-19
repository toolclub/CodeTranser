"""沙箱单元测试:Manager 调度逻辑 + Client 命令拼装。

不连真实 SSH(沙箱依赖外部容器);全部走 mock。
"""

from typing import Any

import pytest

from app.infra.sandbox import ExecuteResult, SandboxClient, SandboxManager


class _FakeWorker:
    def __init__(self, wid: str = "w1") -> None:
        self.worker_id = wid
        self.address = "fake:22"
        self.calls: list[tuple[str, str | None, float | None]] = []
        self._healthy = True

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def healthy(self) -> bool:
        return self._healthy

    async def exec_command(
        self,
        cmd: str,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> ExecuteResult:
        self.calls.append((cmd, cwd, timeout))
        return ExecuteResult(
            stdout="ok\n", stderr="", exit_code=0, duration_ms=1, cwd=cwd or ""
        )


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}

    async def get(self, k: str) -> str | None:
        return self._kv.get(k)

    async def set(self, k: str, v: str, ex: int | None = None) -> bool:
        self._kv[k] = v
        return True

    async def delete(self, k: str) -> int:
        return 1 if self._kv.pop(k, None) else 0


@pytest.mark.asyncio
async def test_manager_unavailable_when_no_workers() -> None:
    mgr = SandboxManager(redis=None)
    await mgr.init([])
    assert mgr.available is False
    r = await mgr.exec_for_run("r_x", "echo hi")
    assert r.exit_code == -1
    assert "unavailable" in r.error or "unavailable" in r.stderr


@pytest.mark.asyncio
async def test_manager_picks_worker_and_caches_session() -> None:
    mgr = SandboxManager(redis=None)
    fake = _FakeWorker("w1")
    # 跳过真 SSH:手工注入
    mgr._workers["w1"] = fake  # type: ignore[assignment]
    mgr._healthy.add("w1")
    mgr._initialized = True

    r1 = await mgr.exec_for_run("r_42", "ls")
    assert r1.exit_code == 0
    assert mgr._sessions.get("r_42") == "w1"

    # 第二次同 run_id 走缓存,落在同一 worker
    r2 = await mgr.exec_for_run("r_42", "pwd")
    assert r2.exit_code == 0
    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_manager_cross_pod_session_via_redis() -> None:
    redis = _FakeRedis()
    mgr_a = SandboxManager(redis=redis)
    mgr_b = SandboxManager(redis=redis)
    fake_a = _FakeWorker("w1")
    fake_b = _FakeWorker("w1")
    for mgr, fake in [(mgr_a, fake_a), (mgr_b, fake_b)]:
        mgr._workers["w1"] = fake  # type: ignore[assignment]
        mgr._healthy.add("w1")
        mgr._initialized = True

    # pod A 上为 r_99 分配
    await mgr_a.exec_for_run("r_99", "touch /sandbox/r_99/init")
    # pod B 重启或路由切走,Redis 记录让 B 看到同一个 worker
    assert (await redis.get("cascade:sandbox:run:r_99")) == "w1"
    await mgr_b.exec_for_run("r_99", "echo hi")
    assert mgr_b._sessions.get("r_99") == "w1"


@pytest.mark.asyncio
async def test_client_write_file_uses_base64_and_quotes() -> None:
    mgr = SandboxManager(redis=None)
    fake = _FakeWorker("w1")
    mgr._workers["w1"] = fake  # type: ignore[assignment]
    mgr._healthy.add("w1")
    mgr._initialized = True
    client = SandboxClient(mgr)

    await client.write_file("r_x", "/sandbox/r_x/main.cpp", "int main(){}")
    cmd = fake.calls[-1][0]
    assert "base64 -d" in cmd
    assert "/sandbox/r_x/main.cpp" in cmd


@pytest.mark.asyncio
async def test_client_safe_path_rejects_dotdot() -> None:
    mgr = SandboxManager(redis=None)
    fake = _FakeWorker("w1")
    mgr._workers["w1"] = fake  # type: ignore[assignment]
    mgr._healthy.add("w1")
    mgr._initialized = True
    client = SandboxClient(mgr)

    with pytest.raises(ValueError):
        await client.write_file("r_x", "/sandbox/../etc/passwd", "x")


@pytest.mark.asyncio
async def test_status_reports_workers_and_sessions() -> None:
    mgr = SandboxManager(redis=None)
    mgr._workers["w1"] = _FakeWorker("w1")  # type: ignore[assignment]
    mgr._workers["w2"] = _FakeWorker("w2")  # type: ignore[assignment]
    mgr._healthy = {"w1"}
    mgr._initialized = True
    mgr._sessions["r_a"] = "w1"

    s = mgr.status()
    assert s["total_workers"] == 2
    assert s["healthy_workers"] == 1
    assert s["active_sessions"] == 1
    by_id = {w["id"]: w for w in s["workers"]}
    assert by_id["w1"]["sessions"] == 1
    assert by_id["w2"]["healthy"] is False
