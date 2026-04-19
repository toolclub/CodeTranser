"""沙箱接入(复用 ChatFlow 沙箱镜像)。

设计:
  - 沙箱本身是独立部署(ChatFlow 的 `chatflow-sandbox` 镜像,SSH server on :22)
  - Cascade 后端通过 asyncssh 连接;不维护沙箱镜像
  - 配置与 ChatFlow 同构:`SANDBOX_WORKERS=[{id,host,port,user,password|key_file}, ...]`

模块:
  - `SSHWorker`     单 worker 的 SSH 连接池 + exec_command
  - `SandboxManager` 多 worker 健康检查 + 按 run_id 亲和 + Redis 登记
  - `SandboxClient` 业务面对的入口:`exec(run_id, cmd, ...) -> ExecuteResult`
"""

from app.infra.sandbox.client import SandboxClient
from app.infra.sandbox.manager import SandboxManager
from app.infra.sandbox.worker import ExecuteResult, SSHWorker

__all__ = [
    "ExecuteResult",
    "SSHWorker",
    "SandboxClient",
    "SandboxManager",
]
