from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DagView:
    """从 forest 计算出来的一个 DAG 视图(04 章 DagComputeVisitor 产出)。"""

    dag_index: int
    root: str
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    spans_bundles: tuple[str, ...]
