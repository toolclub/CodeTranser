from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitor import ForestVisitor


class MetricsVisitor(ForestVisitor):
    """森林基础统计。Phase1 early-termination 和观测用。"""

    def __init__(self) -> None:
        self.bundle_count = 0
        self.node_count = 0
        self.orphan_count = 0
        self.edge_count = 0
        self.by_template: dict[str, int] = {}

    def visit_forest(self, f: CascadeForest) -> None:
        self.bundle_count = len(f.bundles)
        self.node_count = len(f.node_instances)
        self.edge_count = len(f.edges)
        self.orphan_count = sum(1 for n in f.node_instances if n.bundle_id is None)
        for n in f.node_instances:
            k = n.template_snapshot.name
            self.by_template[k] = self.by_template.get(k, 0) + 1
