from app.domain.graph.errors import DuplicateEdge
from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitor import ForestVisitor


class DuplicateEdgeVisitor(ForestVisitor):
    """同一 (src, semantic, dst) 三元组不允许重复边。"""

    def visit_forest(self, f: CascadeForest) -> None:
        seen: set[tuple[str, str, str]] = set()
        for e in f.edges:
            key = (e.src, e.semantic, e.dst)
            if key in seen:
                raise DuplicateEdge(
                    "duplicate edge",
                    edge=e.edge_id,
                    src=e.src,
                    semantic=e.semantic,
                    dst=e.dst,
                )
            seen.add(key)
