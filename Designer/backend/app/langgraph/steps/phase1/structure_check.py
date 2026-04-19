from typing import Any

from app.domain.graph.errors import GraphParseError
from app.langgraph.state import CascadeState
from app.langgraph.steps.phase1.base import Phase1HandlerBase
from app.services.design_validator import DesignValidator
from app.services.forest_parser import ForestParser


class StructureCheckHandler(Phase1HandlerBase):
    """Phase1 Handler 1:纯 Python 结构合法性校验(无环、引用、边语义、字段值 schema)。"""

    name = "structure_check"
    handler_order = 10
    depends_on = ("design_validator", "forest_parser")

    def __init__(
        self,
        *,
        design_validator: DesignValidator,
        forest_parser: ForestParser,
        **base_kw: Any,
    ) -> None:
        super().__init__(**base_kw)
        self._validator = design_validator
        self._parser = forest_parser

    async def _handle(self, state: CascadeState, trace: dict[str, Any]) -> str:
        raw = state["raw_graph_json"]
        try:
            forest = self._parser.parse_readonly(
                graph_version_id=state.get("graph_version_id", ""),
                version_number=0,
                snapshot=raw,
            )
        except GraphParseError as e:
            trace["summary"] = "forest parse failed"
            trace["errors"].append(
                {"code": e.code, "message": e.message, "extra": dict(e.extra)}
            )
            return "fail"

        report = self._validator.run(forest)
        trace["details"]["warnings"] = report.warnings
        trace["details"]["bundle_count"] = len(forest.bundles)
        trace["details"]["node_count"] = len(forest.node_instances)
        trace["details"]["edge_count"] = len(forest.edges)
        trace["details"]["orphan_count"] = sum(
            1 for n in forest.node_instances if n.bundle_id is None
        )

        if not report.ok:
            trace["summary"] = f"{len(report.errors)} structural errors"
            trace["errors"] = report.errors
            return "fail"

        state["parsed_forest"] = raw
        trace["summary"] = (
            f"ok: {len(forest.bundles)} bundle(s), "
            f"{len(forest.node_instances)} node(s), "
            f"{len(forest.edges)} edge(s)"
        )
        return "pass"
