from app.domain.graph.dag_view import DagView
from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitor import ForestVisitor


class DagComputeVisitor(ForestVisitor):
    """按 root(入度 0)分解森林成若干 DagView。允许多 DAG 共享节点。"""

    def __init__(self) -> None:
        self.dags: list[DagView] = []

    def visit_forest(self, f: CascadeForest) -> None:
        by_id = {n.instance_id: n for n in f.node_instances}
        adj: dict[str, list[str]] = {iid: [] for iid in by_id}
        edge_map: dict[tuple[str, str], list[str]] = {}
        in_deg: dict[str, int] = {iid: 0 for iid in by_id}

        for e in f.edges:
            if e.src in adj and e.dst in in_deg:
                adj[e.src].append(e.dst)
                in_deg[e.dst] += 1
                edge_map.setdefault((e.src, e.dst), []).append(e.edge_id)

        roots = sorted(iid for iid, k in in_deg.items() if k == 0)
        for idx, root in enumerate(roots):
            nodes, edges = _reach(root, adj, edge_map)
            spans = sorted({by_id[i].bundle_id for i in nodes if by_id[i].bundle_id})
            self.dags.append(
                DagView(
                    dag_index=idx,
                    root=root,
                    node_ids=tuple(sorted(nodes)),
                    edge_ids=tuple(sorted(edges)),
                    spans_bundles=tuple(spans),
                )
            )


def _reach(
    root: str,
    adj: dict[str, list[str]],
    edge_map: dict[tuple[str, str], list[str]],
) -> tuple[set[str], set[str]]:
    seen_n: set[str] = set()
    seen_e: set[str] = set()
    stack = [root]
    while stack:
        u = stack.pop()
        if u in seen_n:
            continue
        seen_n.add(u)
        for v in adj.get(u, []):
            for eid in edge_map.get((u, v), []):
                seen_e.add(eid)
            if v not in seen_n:
                stack.append(v)
    return seen_n, seen_e
