from app.tool_runtime.simulators import SIMULATOR_REGISTRY


def test_index_table_lookup_autoscanned() -> None:
    assert "IndexTableLookup" in SIMULATOR_REGISTRY
    cls = SIMULATOR_REGISTRY["IndexTableLookup"]
    assert cls.tool_name == "IndexTableLookup"
