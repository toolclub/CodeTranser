from app.domain.graph.dag_compute import DagComputeVisitor
from app.domain.graph.iteration import TopologicalIterator
from tests.unit.graph._fixtures import make_bundle, make_edge, make_forest, make_inst


def test_topological_order() -> None:
    # a -> b -> c, 独立 d
    f = make_forest(
        instances=[make_inst("a"), make_inst("b"), make_inst("c"), make_inst("d")],
        edges=[make_edge("e1", "a", "b"), make_edge("e2", "b", "c")],
    )
    ids = [n.instance_id for n in TopologicalIterator(f)]
    # ready 每次按字典序取最小;a 最先,然后 b(a 的后继),再 c(b 的后继),最后 d(孤立)
    assert ids == ["a", "b", "c", "d"]


def test_dag_two_roots() -> None:
    f = make_forest(
        instances=[make_inst("A"), make_inst("B"), make_inst("C")],
        edges=[
            make_edge("e1", "A", "B"),
            make_edge("e2", "C", "B"),
        ],
    )
    v = DagComputeVisitor()
    v.visit_forest(f)
    assert {d.root for d in v.dags} == {"A", "C"}
    # B 被两 DAG 共享
    dag_a = next(d for d in v.dags if d.root == "A")
    dag_c = next(d for d in v.dags if d.root == "C")
    assert "B" in dag_a.node_ids and "B" in dag_c.node_ids


def test_dag_spans_bundles() -> None:
    f = make_forest(
        bundles=[make_bundle("bnd_1", ["A"]), make_bundle("bnd_2", ["B"])],
        instances=[
            make_inst("A", bundle="bnd_1"),
            make_inst("B", bundle="bnd_2"),
            make_inst("C"),
        ],
        edges=[make_edge("e1", "A", "B"), make_edge("e2", "B", "C")],
    )
    v = DagComputeVisitor()
    v.visit_forest(f)
    assert len(v.dags) == 1
    d = v.dags[0]
    assert d.root == "A"
    assert set(d.spans_bundles) == {"bnd_1", "bnd_2"}
