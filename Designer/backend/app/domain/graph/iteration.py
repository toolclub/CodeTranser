from typing import Iterator

from app.domain.graph.errors import GraphHasCycle
from app.domain.graph.nodes import CascadeForest, NodeInstance


class TopologicalIterator:
    """Kahn 算法。全森林范围排序(Bundle 不影响顺序)。
    同一层按 instance_id 字典序,结果稳定。"""

    def __init__(self, forest: CascadeForest) -> None:
        self._f = forest

    def __iter__(self) -> Iterator[NodeInstance]:
        by_id = {n.instance_id: n for n in self._f.node_instances}
        indeg: dict[str, int] = {iid: 0 for iid in by_id}
        adj: dict[str, list[str]] = {iid: [] for iid in by_id}
        for e in self._f.edges:
            if e.src in indeg and e.dst in indeg:
                adj[e.src].append(e.dst)
                indeg[e.dst] += 1

        ready = sorted([iid for iid, k in indeg.items() if k == 0])
        order: list[str] = []
        while ready:
            u = ready.pop(0)
            order.append(u)
            nexts: list[str] = []
            for v in adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    nexts.append(v)
            ready = sorted(ready + nexts)
        if len(order) != len(by_id):
            raise GraphHasCycle("cycle detected during topo sort")
        return iter(by_id[i] for i in order)
