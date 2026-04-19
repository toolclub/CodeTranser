from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitor import ForestVisitor


class OrphanReportVisitor(ForestVisitor):
    """报告:
    - orphans:不归属任何 bundle 的游离节点(v1 允许)
    - isolated:无入无出的孤立节点(warning)
    """

    def __init__(self) -> None:
        self.orphans: list[str] = []
        self.isolated: list[str] = []

    def visit_forest(self, f: CascadeForest) -> None:
        in_deg = {n.instance_id: 0 for n in f.node_instances}
        out_deg = {n.instance_id: 0 for n in f.node_instances}
        for e in f.edges:
            if e.src in out_deg:
                out_deg[e.src] += 1
            if e.dst in in_deg:
                in_deg[e.dst] += 1
        for n in f.node_instances:
            if n.bundle_id is None:
                self.orphans.append(n.instance_id)
            if in_deg[n.instance_id] == 0 and out_deg[n.instance_id] == 0:
                self.isolated.append(n.instance_id)
