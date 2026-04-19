import pytest

from app.domain.graph.nodes import Bundle, CascadeForest, Edge, NodeInstance
from app.domain.tool.tool import (
    CodeGenerationHints,
    EdgeSemantic,
    Engine,
    JsonSimulatorSpec,
    NodeTemplate,
    Scope,
)


def _tpl(name: str = "Foo") -> NodeTemplate:
    return NodeTemplate(
        id="tpl_xxx",
        name=name,
        display_name=name,
        category="c",
        scope=Scope.GLOBAL,
        version=1,
        description="",
        input_schema={},
        output_schema={},
        simulator=JsonSimulatorSpec(engine=Engine.PURE_PYTHON, python_impl=name),
        edge_semantics=(EdgeSemantic("next"),),
        code_hints=CodeGenerationHints(),
        extensions={},
        definition_hash="h",
    )


def _inst(iid: str, bundle_id: str | None = None) -> NodeInstance:
    return NodeInstance(
        instance_id=iid,
        template_snapshot=_tpl(),
        instance_name=iid,
        field_values={},
        bundle_id=bundle_id,
    )


def _forest() -> CascadeForest:
    return CascadeForest(
        graph_version_id="gv_1",
        version_number=1,
        bundles=(Bundle("bnd_1", "B1", "", ("n_1", "n_2")),),
        node_instances=(
            _inst("n_1", "bnd_1"),
            _inst("n_2", "bnd_1"),
            _inst("n_3", None),  # 游离
        ),
        edges=(Edge("e_1", "n_1", "n_2", "next"),),
        metadata={},
    )


def test_node_by_id_and_bundle_by_id() -> None:
    f = _forest()
    assert f.node_by_id("n_2").instance_id == "n_2"
    assert f.bundle_by_id("bnd_1").name == "B1"


def test_node_by_id_missing_raises() -> None:
    with pytest.raises(KeyError):
        _forest().node_by_id("n_missing")


def test_orphans() -> None:
    orphans = _forest().orphans()
    assert [n.instance_id for n in orphans] == ["n_3"]
