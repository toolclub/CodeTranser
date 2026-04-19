from abc import ABC
from typing import Any

from app.domain.graph.nodes import Bundle, CascadeForest, Edge, NodeInstance


class ForestVisitor(ABC):
    """对森林的只读遍历。默认 visit_* 是 noop;子类按需覆盖。

    visit_forest 默认实现:先遍历 bundles,再遍历 nodes,再遍历 edges。
    绝大多数 Visitor 会覆盖 visit_forest 自己决定遍历。
    """

    def visit_forest(self, f: CascadeForest) -> Any:
        for b in f.bundles:
            b.accept(self)
        for n in f.node_instances:
            n.accept(self)
        for e in f.edges:
            e.accept(self)

    def visit_bundle(self, b: Bundle) -> Any:
        pass

    def visit_node(self, n: NodeInstance) -> Any:
        pass

    def visit_edge(self, e: Edge) -> Any:
        pass
