from app.domain.graph.paste import rebuild_ids


def test_rebuild_ids_rewires_internals() -> None:
    pasted = {
        "bundles": [{"bundle_id": "bnd_old", "name": "B", "node_instance_ids": ["n_old_a", "n_old_b"]}],
        "node_instances": [
            {"instance_id": "n_old_a", "template_id": "tpl_1", "template_version": 1, "field_values": {}},
            {"instance_id": "n_old_b", "template_id": "tpl_1", "template_version": 1, "field_values": {}},
        ],
        "edges": [
            {"edge_id": "e_old", "from": "n_old_a", "to": "n_old_b", "edge_semantic": "next"},
        ],
    }
    out = rebuild_ids(pasted)
    assert out["bundles"][0]["bundle_id"] != "bnd_old"
    new_iids = [n["instance_id"] for n in out["node_instances"]]
    assert set(new_iids) == set(out["bundles"][0]["node_instance_ids"])
    e = out["edges"][0]
    assert e["from"] in new_iids and e["to"] in new_iids


def test_rebuild_ids_idempotent_per_call() -> None:
    from copy import deepcopy

    original = {
        "bundles": [],
        "node_instances": [
            {"instance_id": "n_1", "template_id": "tpl_1", "template_version": 1, "field_values": {}}
        ],
        "edges": [],
    }
    a = rebuild_ids(deepcopy(original))
    b = rebuild_ids(deepcopy(original))
    # 两次独立调用得到不同的新 id(uuid4 随机)
    assert a["node_instances"][0]["instance_id"] != b["node_instances"][0]["instance_id"]
    assert a["node_instances"][0]["instance_id"].startswith("n_")
