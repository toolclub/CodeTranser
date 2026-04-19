from copy import deepcopy
from typing import Any

from app.domain.graph.builders import (
    FrozenResolver,
    build_forest,
    template_to_snapshot_dict,
)
from app.domain.graph.nodes import CascadeForest
from app.tool_runtime.registry import ToolRegistry


class ForestParser:
    """保存路径:freeze_snapshot(async)拉最新模板冻结 → template_snapshot。
    读取路径:parse_readonly(sync)用冻结的 snapshot 还原 CascadeForest。"""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def freeze_snapshot(self, raw_snapshot: dict[str, Any]) -> dict[str, Any]:
        out = deepcopy(raw_snapshot)
        for n in out.get("node_instances", []):
            tpl = await self._registry.get_by_id(
                n["template_id"], n.get("template_version")
            )
            n["template_version"] = tpl.version
            n["template_snapshot"] = template_to_snapshot_dict(tpl)
        return out

    def parse_readonly(
        self,
        *,
        graph_version_id: str,
        version_number: int,
        snapshot: dict[str, Any],
    ) -> CascadeForest:
        return build_forest(
            graph_version_id=graph_version_id,
            version_number=version_number,
            snapshot=snapshot,
            resolver=FrozenResolver(),
        )
