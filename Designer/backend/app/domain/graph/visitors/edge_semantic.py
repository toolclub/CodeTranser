from app.domain.graph.errors import EdgeSemanticInvalid
from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitor import ForestVisitor


class EdgeSemanticVisitor(ForestVisitor):
    """每条边的 semantic 必须是 src 节点模板的 edge_semantics 里的 field。"""

    def visit_forest(self, f: CascadeForest) -> None:
        by_id = {n.instance_id: n for n in f.node_instances}
        for e in f.edges:
            src = by_id.get(e.src)
            if src is None:
                continue
            allowed = {es.field for es in src.template_snapshot.edge_semantics}
            if e.semantic not in allowed:
                raise EdgeSemanticInvalid(
                    f"edge semantic '{e.semantic}' not in {sorted(allowed)}",
                    edge=e.edge_id,
                    src=e.src,
                )
