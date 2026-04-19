from typing import Any

import pytest

from app.domain.run.sim import SimContext, SimResult
from app.domain.tool.tool import Engine
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.simulators.hybrid import HybridSimulator


class _OK(ToolSimulator):
    tool_name = "OK"
    engine = Engine.PURE_PYTHON

    def __init__(self, value: str = "primary"):
        self._v = value

    def run(self, fields: dict[str, Any], input_json: dict[str, Any], ctx: SimContext) -> SimResult:
        return SimResult(output={"v": self._v}, engine_used=Engine.PURE_PYTHON)


class _Boom(ToolSimulator):
    tool_name = "Boom"
    engine = Engine.PURE_PYTHON

    def run(self, fields: dict[str, Any], input_json: dict[str, Any], ctx: SimContext) -> SimResult:
        raise RuntimeError("boom")


def _ctx() -> SimContext:
    return SimContext(run_id="r", instance_id="n", table_data={})


def test_primary_success_no_fallback() -> None:
    sim = HybridSimulator(_OK("p"), None)
    r = sim.run({}, {}, _ctx())
    assert r.output == {"v": "p"}


def test_primary_raises_falls_back() -> None:
    sim = HybridSimulator(_Boom(), _OK("fb"))
    r = sim.run({}, {}, _ctx())
    assert r.output == {"v": "fb"}


def test_both_fail_raises() -> None:
    sim = HybridSimulator(_Boom(), None)
    with pytest.raises(RuntimeError):
        sim.run({}, {}, _ctx())
