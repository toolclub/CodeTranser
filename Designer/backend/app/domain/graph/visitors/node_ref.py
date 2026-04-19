from app.domain.graph.errors import NodeRefInvalid, SelfLoopEdge
from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitor import ForestVisitor


class NodeRefCheckerVisitor(ForestVisitor):
    """边/Bundle 引用的 instance_id 必须存在;自环禁止。"""

    def visit_forest(self, f: CascadeForest) -> None:
        ids = {n.instance_id for n in f.node_instances}
        for e in f.edges:
            if e.src not in ids:
                raise NodeRefInvalid("edge src missing", edge=e.edge_id, missing=e.src)
            if e.dst not in ids:
                raise NodeRefInvalid("edge dst missing", edge=e.edge_id, missing=e.dst)
            if e.src == e.dst:
                raise SelfLoopEdge("edge points to itself", edge=e.edge_id)
        for b in f.bundles:
            for iid in b.node_instance_ids:
                if iid not in ids:
                    raise NodeRefInvalid(
                        "bundle ref missing", bundle=b.bundle_id, missing=iid
                    )
