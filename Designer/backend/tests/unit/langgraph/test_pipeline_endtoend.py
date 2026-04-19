import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.infra.db.base import Base
from app.langgraph.events import RunEventBus
from app.langgraph.pipeline import PipelineBuilder, PipelineVariant
from app.langgraph.router import PhaseRouter
from app.langgraph.run_step_store import NoopRunStepStore
from app.langgraph.runtime import WorkflowRuntime
from app.langgraph.steps.factory import PipelineStepFactory, StepDeps
from app.langgraph.trace_sink import ToolCallTraceContext, TraceSink
from app.llm.decorators.trace import LLMTraceContext


@pytest_asyncio.fixture(autouse=True)
async def _session_factory_fixture(session_factory: async_sessionmaker[AsyncSession]):
    global _session_factory
    _session_factory = session_factory
    yield
    _session_factory = None  # type: ignore[assignment]


_session_factory: async_sessionmaker[AsyncSession] | None = None  # type: ignore[assignment]


class _NullRegistry:
    async def get_by_id(self, tid, v=None):  # pragma: no cover
        raise NotImplementedError

    def simulator_of(self, tpl):  # pragma: no cover
        raise NotImplementedError


def _deps() -> StepDeps:
    from app.services.design_validator import DesignValidator
    from app.services.forest_parser import ForestParser

    return StepDeps(
        event_bus=RunEventBus(None),
        trace_sink=TraceSink(None),
        tool_trace_ctx=ToolCallTraceContext(),
        llm_trace_ctx=LLMTraceContext(),
        run_step_store=NoopRunStepStore(),
        settings=Settings(LLM_API_KEY="t"),
        llm_client=None,
        tool_registry=_NullRegistry(),
        design_validator=DesignValidator(),
        forest_parser=ForestParser(_NullRegistry()),
    )


def _factory_router() -> tuple[PipelineStepFactory, PhaseRouter]:
    deps = _deps()
    f = PipelineStepFactory(deps)
    r = PhaseRouter(f, deps.settings)
    return f, r


@pytest.mark.asyncio
async def test_full_variant_empty_scenarios_fails_phase1() -> None:
    """空场景 → ScenarioRunHandler fail → final=invalid(验证责任链路由)。"""
    f, r = _factory_router()
    builder = PipelineBuilder(f, r)
    runtime = WorkflowRuntime(
        builder, RunEventBus(None), Settings(LLM_API_KEY="t"),
        session_factory=_session_factory,
    )
    final = await runtime.run(
        run_id="r_test",
        graph_version_id="gv_x",
        raw_graph_json={"bundles": [], "node_instances": [], "edges": []},
        variant=PipelineVariant.FULL,
    )
    assert final["final_verdict"] == "invalid"
    assert final["phase1_verdict"] == "invalid"


@pytest.mark.asyncio
async def test_phase1_only_variant_empty_scenarios_fails() -> None:
    f, r = _factory_router()
    builder = PipelineBuilder(f, r)
    runtime = WorkflowRuntime(
        builder, RunEventBus(None), Settings(LLM_API_KEY="t"),
        session_factory=_session_factory,
    )
    final = await runtime.run(
        run_id="r_p1",
        graph_version_id="gv_x",
        raw_graph_json={"bundles": [], "node_instances": [], "edges": []},
        variant=PipelineVariant.PHASE1_ONLY,
    )
    assert final["final_verdict"] == "invalid"


@pytest.mark.asyncio
async def test_structure_check_pass_but_scenario_fails() -> None:
    """空森林结构合法(节点 0 边 0 不算结构错),但没场景 → Handler 2 fail。"""
    f, r = _factory_router()
    builder = PipelineBuilder(f, r)
    runtime = WorkflowRuntime(
        builder, RunEventBus(None), Settings(LLM_API_KEY="t"),
        session_factory=_session_factory,
    )
    final = await runtime.run(
        run_id="r_p2",
        graph_version_id="gv_x",
        raw_graph_json={"bundles": [], "node_instances": [], "edges": []},
        variant=PipelineVariant.UP_TO_PHASE2,
    )
    # phase1 fail 来自 scenario_run,不是 structure_check
    fail_trace = final["handler_traces"][-1]
    assert fail_trace["handler_name"] == "scenario_run"
    assert fail_trace["status"] == "fail"
