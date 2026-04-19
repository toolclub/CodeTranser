from typing import Any

import pytest

from app.config import Settings
from app.langgraph.events import RunEventBus
from app.langgraph.run_step_store import NoopRunStepStore
from app.langgraph.state import initial_state
from app.langgraph.steps.phase1.structure_check import StructureCheckHandler
from app.langgraph.trace_sink import ToolCallTraceContext, TraceSink
from app.llm.decorators.trace import LLMTraceContext
from app.services.design_validator import DesignValidator
from app.services.forest_parser import ForestParser
from tests.unit.graph._fixtures import make_tpl
from app.domain.graph.builders import template_to_snapshot_dict


class _FakeRegistry:
    async def get_by_id(self, tid: str, v: Any = None):  # pragma: no cover
        raise NotImplementedError


def _handler() -> StructureCheckHandler:
    return StructureCheckHandler(
        design_validator=DesignValidator(),
        forest_parser=ForestParser(_FakeRegistry()),
        event_bus=RunEventBus(None),
        trace_sink=TraceSink(None),
        llm_trace_ctx=LLMTraceContext(),
        tool_trace_ctx=ToolCallTraceContext(),
        run_step_store=NoopRunStepStore(),
    )


def _raw_valid() -> dict:
    tpl = template_to_snapshot_dict(make_tpl("Foo", edges=["next"]))
    return {
        "bundles": [
            {"bundle_id": "bnd_1", "name": "B", "node_instance_ids": ["n_1"]},
        ],
        "node_instances": [
            {
                "instance_id": "n_1",
                "template_id": tpl["id"],
                "template_version": 1,
                "template_snapshot": tpl,
                "instance_name": "n1",
                "field_values": {},
            },
            {
                "instance_id": "n_2",
                "template_id": tpl["id"],
                "template_version": 1,
                "template_snapshot": tpl,
                "instance_name": "n2",
                "field_values": {},
            },
        ],
        "edges": [
            {"edge_id": "e_1", "from": "n_1", "to": "n_2", "edge_semantic": "next"}
        ],
        "metadata": {},
    }


@pytest.mark.asyncio
async def test_structure_check_accepts_valid() -> None:
    h = _handler()
    state = initial_state("r_1", "gv_1", _raw_valid())
    out = await h.execute(state)
    assert out["decision"] == "handler_pass"
    assert out["handler_traces"][-1]["status"] == "pass"


@pytest.mark.asyncio
async def test_structure_check_rejects_cycle() -> None:
    h = _handler()
    raw = _raw_valid()
    raw["edges"].append(
        {"edge_id": "e_2", "from": "n_2", "to": "n_1", "edge_semantic": "next"}
    )
    state = initial_state("r_1", "gv_1", raw)
    out = await h.execute(state)
    assert out["decision"] == "handler_fail"
    assert out["handler_traces"][-1]["status"] == "fail"
