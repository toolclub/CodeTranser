import pytest

from app.domain.run.sim import SimContext
from app.tool_runtime.errors import SimulatorInputInvalid
from app.tool_runtime.simulators.pure_python.index_table_lookup import IndexTableLookupSim


def ctx(**tables: list) -> SimContext:
    return SimContext(run_id="t", instance_id="n", table_data=dict(tables), llm=None)


def test_hit() -> None:
    r = IndexTableLookupSim().run(
        {"EntrySize": 4, "MaxEntryNum": 2, "Mask": None},
        {"key": 2},
        ctx(entries=[{"key": 1, "value": "a"}, {"key": 2, "value": "b"}]),
    )
    assert r.output == {"hit": True, "value": "b", "index": 1}


def test_miss() -> None:
    r = IndexTableLookupSim().run(
        {"EntrySize": 4, "MaxEntryNum": 1, "Mask": None},
        {"key": 99},
        ctx(entries=[{"key": 1, "value": "a"}]),
    )
    assert r.output == {"hit": False, "value": None, "index": None}


def test_mask() -> None:
    r = IndexTableLookupSim().run(
        {"EntrySize": 2, "MaxEntryNum": 1, "Mask": 0xFF00},
        {"key": 0xAB99},
        ctx(entries=[{"key": 0xABCD, "value": "x"}]),
    )
    assert r.output["hit"] is True


def test_missing_required_field() -> None:
    with pytest.raises(SimulatorInputInvalid):
        IndexTableLookupSim().run(
            {"EntrySize": 4, "MaxEntryNum": 1, "Mask": None},
            {},  # 缺 key
            ctx(entries=[]),
        )


def test_max_entry_num_truncates() -> None:
    # MaxEntryNum=1 → 只看第一条,即使第二条匹配也 miss
    r = IndexTableLookupSim().run(
        {"EntrySize": 4, "MaxEntryNum": 1, "Mask": None},
        {"key": 2},
        ctx(entries=[{"key": 1, "value": "a"}, {"key": 2, "value": "b"}]),
    )
    assert r.output["hit"] is False
