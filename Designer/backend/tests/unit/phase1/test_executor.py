"""executor 单测:在真实 ToolRegistry(带 IndexTableLookupSim)基础上验证路由。"""

import json

import pytest

from app.domain.graph.builders import FrozenResolver, build_forest, template_to_snapshot_dict
from app.langgraph.steps.phase1.executor import (
    NodeExecContext,
    build_tool_specs,
    make_executor,
)
from app.langgraph.trace_sink import ToolCallTraceContext
from app.llm.types import ToolUseRequest
from app.tool_runtime.factory import SimulatorFactory
from app.tool_runtime.loader import ToolLoader
from app.tool_runtime.registry import ToolRegistry
from tests.unit.graph._fixtures import make_tpl


def _forest_with_index_tpl():
    # 构造一个节点实例引用 IndexTableLookup 模板快照(scope=global,engine=pure_python,python_impl=IndexTableLookup)
    tpl = make_tpl("IndexTableLookup", edges=["next_on_hit", "next_on_miss"])
    tpl_dict = template_to_snapshot_dict(tpl)
    tpl_dict["simulator"] = {
        "engine": "pure_python",
        "python_impl": "IndexTableLookup",
        "llm_fallback": False,
    }
    snap = {
        "bundles": [],
        "node_instances": [
            {
                "instance_id": "n_parse",
                "template_id": tpl_dict["id"],
                "template_version": 1,
                "template_snapshot": tpl_dict,
                "instance_name": "parse",
                "field_values": {"EntrySize": 4, "MaxEntryNum": 2, "Mask": None},
            }
        ],
        "edges": [],
        "metadata": {},
    }
    return build_forest(
        graph_version_id="gv", version_number=1, snapshot=snap, resolver=FrozenResolver()
    )


@pytest.mark.asyncio
async def test_executor_hits_simulator_and_returns_outgoing_edges() -> None:
    forest = _forest_with_index_tpl()
    registry = ToolRegistry(ToolLoader(lambda: None), SimulatorFactory(), redis=None)  # type: ignore[arg-type]
    trace = ToolCallTraceContext()
    trace.begin_scope()

    ctx = NodeExecContext(
        forest=forest,
        tables={"entries": [{"key": 1, "value": "a"}, {"key": 2, "value": "b"}]},
        run_id="r",
        tool_registry=registry,
        llm_client=None,
        tool_trace=trace,
        per_node_limit=5,
    )
    exec_ = make_executor(ctx)
    r = await exec_(
        ToolUseRequest(
            id="tu_1",
            name="IndexTableLookup",
            input={"instance_id": "n_parse", "input_json": {"key": 2}},
        )
    )
    assert not r.is_error
    payload = json.loads(r.content)
    assert payload["output_json"]["hit"] is True
    assert payload["outgoing_edges"] == []
    trace.end_scope()


@pytest.mark.asyncio
async def test_executor_rejects_unknown_instance() -> None:
    forest = _forest_with_index_tpl()
    registry = ToolRegistry(ToolLoader(lambda: None), SimulatorFactory(), redis=None)  # type: ignore[arg-type]
    trace = ToolCallTraceContext()
    trace.begin_scope()
    ctx = NodeExecContext(
        forest=forest,
        tables={},
        run_id="r",
        tool_registry=registry,
        llm_client=None,
        tool_trace=trace,
    )
    exec_ = make_executor(ctx)
    r = await exec_(
        ToolUseRequest(
            id="tu_1",
            name="IndexTableLookup",
            input={"instance_id": "n_unknown", "input_json": {}},
        )
    )
    assert r.is_error
    trace.end_scope()


def test_build_tool_specs_dedupes_per_template() -> None:
    forest = _forest_with_index_tpl()
    specs = build_tool_specs(forest)
    assert [s.name for s in specs] == ["IndexTableLookup"]
