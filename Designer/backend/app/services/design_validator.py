from dataclasses import dataclass, field
from typing import Any

from app.domain.errors import BusinessError
from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitors.cycle_checker import CycleCheckerVisitor
from app.domain.graph.visitors.duplicate_edge import DuplicateEdgeVisitor
from app.domain.graph.visitors.edge_semantic import EdgeSemanticVisitor
from app.domain.graph.visitors.node_ref import NodeRefCheckerVisitor
from app.domain.graph.visitors.orphan import OrphanReportVisitor
from app.domain.graph.visitors.schema_validation import SchemaValidationVisitor


@dataclass
class ValidationReport:
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class DesignValidator:
    """被 Ch07 Phase1 Handler 1 调用。

    调度顺序:
      1. NodeRefChecker(致命:任何引用不存在 → short circuit)
      2. CycleChecker   (致命:有环 → short circuit)
      3. EdgeSemantic / DuplicateEdge / SchemaValidation(并列收集)
      4. OrphanReport(仅 warning,不阻断)
    """

    def run(self, forest: CascadeForest) -> ValidationReport:
        rep = ValidationReport()

        try:
            NodeRefCheckerVisitor().visit_forest(forest)
        except BusinessError as e:
            rep.errors.append(_err(e))
            return rep

        try:
            CycleCheckerVisitor().visit_forest(forest)
        except BusinessError as e:
            rep.errors.append(_err(e))
            return rep

        for visitor in (
            EdgeSemanticVisitor(),
            DuplicateEdgeVisitor(),
            SchemaValidationVisitor(),
        ):
            try:
                visitor.visit_forest(forest)
            except BusinessError as e:
                rep.errors.append(_err(e))

        orphan = OrphanReportVisitor()
        orphan.visit_forest(forest)
        for iid in orphan.isolated:
            rep.warnings.append({"code": "ISOLATED_NODE", "instance_id": iid})
        for iid in orphan.orphans:
            rep.warnings.append({"code": "BUNDLE_FREE_NODE", "instance_id": iid})
        return rep


def _err(e: BusinessError) -> dict[str, Any]:
    return {"code": e.code, "message": e.message, "extra": dict(e.extra)}
