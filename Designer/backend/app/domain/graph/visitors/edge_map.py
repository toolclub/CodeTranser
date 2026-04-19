from app.domain.graph.nodes import CascadeForest
from app.domain.graph.visitor import ForestVisitor


class EdgeMapVisitor(ForestVisitor):
    """产出 [(src_iid, semantic, dst_iid)] 列表,供 Ch08 code_assembler 生成 wiring。"""

    def __init__(self) -> None:
        self.wirings: list[tuple[str, str, str]] = []

    def visit_forest(self, f: CascadeForest) -> None:
        for e in f.edges:
            self.wirings.append((e.src, e.semantic, e.dst))
