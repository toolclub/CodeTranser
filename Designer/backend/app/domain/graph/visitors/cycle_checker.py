from app.domain.graph.errors import GraphHasCycle
from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitor import ForestVisitor

_WHITE, _GRAY, _BLACK = 0, 1, 2


class CycleCheckerVisitor(ForestVisitor):
    """DFS 三色法。边忽略不存在的 endpoint(NodeRefCheckerVisitor 负责报错)。"""

    def visit_forest(self, f: CascadeForest) -> None:
        ids = {n.instance_id for n in f.node_instances}
        adj: dict[str, list[str]] = {iid: [] for iid in ids}
        for e in f.edges:
            if e.src in adj and e.dst in adj:
                adj[e.src].append(e.dst)

        color = {iid: _WHITE for iid in ids}
        path: list[str] = []

        def dfs(u: str) -> None:
            color[u] = _GRAY
            path.append(u)
            for v in adj[u]:
                if color[v] == _GRAY:
                    cycle = path[path.index(v) :] + [v]
                    raise GraphHasCycle("cycle detected", path=cycle)
                if color[v] == _WHITE:
                    dfs(v)
            color[u] = _BLACK
            path.pop()

        for u in sorted(ids):
            if color[u] == _WHITE:
                dfs(u)
