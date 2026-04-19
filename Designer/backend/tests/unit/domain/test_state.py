from app.domain.run.state import initial_state


def test_initial_state_independent_lists() -> None:
    s1 = initial_state("r_1", "gv_1", {"bundles": []})
    s2 = initial_state("r_2", "gv_2", {"bundles": []})
    s1["handler_traces"].append({"handler_name": "x"})
    assert s2["handler_traces"] == []
    s1["node_outputs"]["n_1"] = {"ok": True}
    assert s2["node_outputs"] == {}


def test_initial_state_defaults() -> None:
    s = initial_state("r_1", "gv_1", {"bundles": []})
    assert s["decision"] == "in_progress"
    assert s["phase1_verdict"] is None
    assert s["inner_sdd_iter"] == 0
