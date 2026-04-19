from app.services.design_validator import DesignValidator
from tests.unit.graph._fixtures import make_edge, make_forest, make_inst, make_tpl


def test_clean_forest_ok_with_orphan_warning() -> None:
    f = make_forest(
        instances=[make_inst("a"), make_inst("b")],
        edges=[make_edge("e1", "a", "b")],
    )
    r = DesignValidator().run(f)
    assert r.ok
    assert any(w["code"] == "BUNDLE_FREE_NODE" for w in r.warnings)


def test_cycle_short_circuits() -> None:
    f = make_forest(
        instances=[make_inst("a"), make_inst("b")],
        edges=[make_edge("e1", "a", "b"), make_edge("e2", "b", "a")],
    )
    r = DesignValidator().run(f)
    assert not r.ok
    assert r.errors[0]["code"] == "VALIDATION_GRAPH_HAS_CYCLE"


def test_field_invalid_not_fatal() -> None:
    tpl = make_tpl(
        "Foo",
        input_schema={
            "type": "object",
            "required": ["n"],
            "properties": {"n": {"type": "integer"}},
        },
    )
    f = make_forest(instances=[make_inst("a", tpl=tpl, field_values={"n": "x"})])
    r = DesignValidator().run(f)
    assert not r.ok
    assert any(e["code"] == "VALIDATION_FIELD_VALUE_INVALID" for e in r.errors)
