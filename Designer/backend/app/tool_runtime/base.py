from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.domain.run.sim import SimContext, SimResult
from app.domain.tool.tool import Engine


class ToolSimulator(ABC):
    """所有节点模板模拟器的抽象基类。

    约定:
      - **无状态**,同一实例可并发调用;外部数据只通过 `ctx` 注入
      - 入参 fields / input_json 只读
      - 无网络/磁盘 IO(除非通过 ctx)
      - 抛异常 = 节点执行失败;由调用方(Phase1 executor)捕获

    新增一个 pure_python 节点模板:
      1. admin 通过 UI/API 建 global 节点模板,engine=pure_python,python_impl=<TemplateName>
      2. 在 `simulators/pure_python/<name_snake>.py` 新建一个 ToolSimulator 子类,tool_name = <TemplateName>
      3. 写单测;重启或 POST /api/admin/node-templates/registry/reload
    """

    tool_name: ClassVar[str] = ""
    engine: ClassVar[Engine] = Engine.PURE_PYTHON

    @abstractmethod
    def run(
        self, fields: dict[str, Any], input_json: dict[str, Any], ctx: SimContext
    ) -> SimResult: ...

    def validate_input(
        self, fields: dict[str, Any], input_json: dict[str, Any], ctx: SimContext
    ) -> None:
        """可选 hook。默认 no-op。"""
