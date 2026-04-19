import pytest

from app.domain.graph.builders import (
    FrozenResolver,
    build_forest,
    snapshot_dict_to_template,
    template_to_snapshot_dict,
)
from app.domain.graph.errors import BundleMembershipConflict, GraphParseError
from tests.unit.graph._fixtures import make_tpl


def _sample_snapshot() -> dict:
    tpl_snap = template_to_snapshot_dict(make_tpl("Foo", edges=["next"]))
    return {
        "bundles": [
            {"bundle_id": "bnd_1", "name": "B", "node_instance_ids": ["n_1"]},
        ],
        "node_instances": [
            {
                "instance_id": "n_1",
                "template_id": tpl_snap["id"],
                "template_version": 1,
                "template_snapshot": tpl_snap,
                "instance_name": "n_1",
                "field_values": {},
            },
            {
                "instance_id": "n_2",
                "template_id": tpl_snap["id"],
                "template_version": 1,
                "template_snapshot": tpl_snap,
                "instance_name": "n_2",
                "field_values": {},
            },
        ],
        "edges": [
            {"edge_id": "e_1", "from": "n_1", "to": "n_2", "edge_semantic": "next"},
        ],
        "metadata": {},
    }


def test_build_forest_frozen() -> None:
    forest = build_forest(
        graph_version_id="gv_1",
        version_number=1,
        snapshot=_sample_snapshot(),
        resolver=FrozenResolver(),
    )
    assert {n.instance_id for n in forest.node_instances} == {"n_1", "n_2"}
    n1 = forest.node_by_id("n_1")
    assert n1.bundle_id == "bnd_1"
    assert forest.node_by_id("n_2").bundle_id is None


def test_frozen_resolver_raises_without_snapshot() -> None:
    snap = _sample_snapshot()
    snap["node_instances"][0].pop("template_snapshot")
    with pytest.raises(GraphParseError):
        build_forest(
            graph_version_id="gv",
            version_number=1,
            snapshot=snap,
            resolver=FrozenResolver(),
        )


def test_bundle_membership_conflict() -> None:
    snap = _sample_snapshot()
    snap["bundles"].append(
        {"bundle_id": "bnd_2", "name": "B2", "node_instance_ids": ["n_1"]}
    )
    with pytest.raises(BundleMembershipConflict):
        build_forest(
            graph_version_id="gv",
            version_number=1,
            snapshot=snap,
            resolver=FrozenResolver(),
        )


def test_snapshot_dict_roundtrip() -> None:
    tpl = make_tpl("Foo", edges=["next", "miss"])
    snap = template_to_snapshot_dict(tpl)
    back = snapshot_dict_to_template(snap)
    assert back.name == tpl.name
    assert {e.field for e in back.edge_semantics} == {"next", "miss"}
