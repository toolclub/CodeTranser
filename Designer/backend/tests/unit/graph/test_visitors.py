import pytest

from app.domain.graph.errors import (
    BundleMembershipConflict,
    DuplicateEdge,
    EdgeSemanticInvalid,
    FieldValueInvalid,
    GraphHasCycle,
    NodeRefInvalid,
    SelfLoopEdge,
)
from app.domain.graph.visitors.cycle_checker import CycleCheckerVisitor
from app.domain.graph.visitors.diff import diff
from app.domain.graph.visitors.duplicate_edge import DuplicateEdgeVisitor
from app.domain.graph.visitors.edge_map import EdgeMapVisitor
from app.domain.graph.visitors.edge_semantic import EdgeSemanticVisitor
from app.domain.graph.visitors.metrics import MetricsVisitor
from app.domain.graph.visitors.node_ref import NodeRefCheckerVisitor
from app.domain.graph.visitors.orphan import OrphanReportVisitor
from app.domain.graph.visitors.schema_validation import SchemaValidationVisitor
from tests.unit.graph._fixtures import (
    make_bundle,
    make_edge,
    make_forest,
    make_inst,
    make_tpl,
)


def test_cycle_checker_simple() -> None:
    f = make_forest(
        instances=[make_inst("a"), make_inst("b")],
        edges=[make_edge("e1", "a", "b"), make_edge("e2", "b", "a")],
    )
    with pytest.raises(GraphHasCycle):
        CycleCheckerVisitor().visit_forest(f)


def test_cycle_checker_dag_ok() -> None:
    f = make_forest(
        instances=[make_inst("a"), make_inst("b")],
        edges=[make_edge("e1", "a", "b")],
    )
    CycleCheckerVisitor().visit_forest(f)  # no raise


def test_node_ref_missing_dst() -> None:
    f = make_forest(
        instances=[make_inst("a")],
        edges=[make_edge("e1", "a", "missing")],
    )
    with pytest.raises(NodeRefInvalid):
        NodeRefCheckerVisitor().visit_forest(f)


def test_self_loop_rejected() -> None:
    f = make_forest(
        instances=[make_inst("a")],
        edges=[make_edge("e1", "a", "a")],
    )
    with pytest.raises(SelfLoopEdge):
        NodeRefCheckerVisitor().visit_forest(f)


def test_bundle_ref_missing() -> None:
    f = make_forest(
        bundles=[make_bundle("bnd_1", ["missing"])],
        instances=[make_inst("a")],
    )
    with pytest.raises(NodeRefInvalid):
        NodeRefCheckerVisitor().visit_forest(f)


def test_edge_semantic_invalid() -> None:
    tpl = make_tpl("Foo", edges=["yes"])
    f = make_forest(
        instances=[make_inst("a", tpl=tpl), make_inst("b", tpl=tpl)],
        edges=[make_edge("e1", "a", "b", semantic="no")],
    )
    with pytest.raises(EdgeSemanticInvalid):
        EdgeSemanticVisitor().visit_forest(f)


def test_duplicate_edge() -> None:
    f = make_forest(
        instances=[make_inst("a"), make_inst("b")],
        edges=[
            make_edge("e1", "a", "b"),
            make_edge("e2", "a", "b"),
        ],
    )
    with pytest.raises(DuplicateEdge):
        DuplicateEdgeVisitor().visit_forest(f)


def test_schema_validation_rejects_bad_field_values() -> None:
    tpl = make_tpl(
        "Foo",
        input_schema={
            "type": "object",
            "required": ["n"],
            "properties": {"n": {"type": "integer"}},
        },
    )
    f = make_forest(instances=[make_inst("a", tpl=tpl, field_values={"n": "not-int"})])
    with pytest.raises(FieldValueInvalid):
        SchemaValidationVisitor().visit_forest(f)


def test_orphan_detects_free_and_isolated() -> None:
    f = make_forest(
        bundles=[make_bundle("bnd_1", ["a"])],
        instances=[
            make_inst("a", bundle="bnd_1"),
            make_inst("b", bundle=None),  # free
            make_inst("c", bundle=None),  # free + isolated
        ],
        edges=[make_edge("e1", "a", "b")],
    )
    v = OrphanReportVisitor()
    v.visit_forest(f)
    assert set(v.orphans) == {"b", "c"}
    assert v.isolated == ["c"]


def test_metrics_counts() -> None:
    f = make_forest(
        bundles=[make_bundle("bnd_1", ["a"])],
        instances=[make_inst("a", bundle="bnd_1"), make_inst("b")],
        edges=[make_edge("e1", "a", "b")],
    )
    v = MetricsVisitor()
    v.visit_forest(f)
    assert v.node_count == 2
    assert v.edge_count == 1
    assert v.bundle_count == 1
    assert v.orphan_count == 1


def test_edge_map_emits_wirings() -> None:
    f = make_forest(
        instances=[make_inst("a"), make_inst("b")],
        edges=[make_edge("e1", "a", "b", semantic="next")],
    )
    v = EdgeMapVisitor()
    v.visit_forest(f)
    assert v.wirings == [("a", "next", "b")]


def test_diff_add_remove_change() -> None:
    tpl_a = make_tpl("A")
    tpl_b = make_tpl("B")
    f1 = make_forest(instances=[make_inst("n1", tpl=tpl_a), make_inst("n2", tpl=tpl_a)])
    f2 = make_forest(instances=[make_inst("n2", tpl=tpl_b), make_inst("n3", tpl=tpl_b)])
    d = diff(f1, f2)
    assert d.added_nodes == ["n3"]
    assert d.removed_nodes == ["n1"]
    assert any(c["iid"] == "n2" for c in d.changed_nodes)
