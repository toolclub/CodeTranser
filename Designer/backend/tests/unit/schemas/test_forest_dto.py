from app.schemas.graph import EdgeDTO, ForestSnapshotDTO


def test_edge_alias_from_to() -> None:
    e = EdgeDTO.model_validate(
        {"edge_id": "e_1", "from": "n_1", "to": "n_2", "edge_semantic": "next"}
    )
    assert e.src == "n_1"
    assert e.dst == "n_2"
    assert e.semantic == "next"


def test_forest_minimal_shape() -> None:
    forest = ForestSnapshotDTO.model_validate(
        {
            "bundles": [],
            "node_instances": [
                {
                    "instance_id": "n_1",
                    "template_id": "tpl_1",
                    "template_version": 1,
                    "instance_name": "n1",
                    "field_values": {},
                }
            ],
            "edges": [],
        }
    )
    assert len(forest.node_instances) == 1
    assert forest.metadata == {}
