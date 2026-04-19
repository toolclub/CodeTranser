"""Cross validator skeleton.

节点模板的 `code_hints.example_fragment` 与其 Python 模拟器的行为应对齐。
v1 先做骨架,等 09 章沙箱就绪后接入真编译 + 批量用例跑通,此处仅提供接口约束。
"""

from typing import Any

from app.domain.tool.tool import NodeTemplate


class CrossValidator:
    def validate(self, tpl: NodeTemplate, samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """返回差异报告列表(v1:空列表占位,等 09 章接入沙箱后实装)。"""
        return []
