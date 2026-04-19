"""端到端:WorkflowRuntime 必须把 run/step 写 DB(分布式必须)。"""

import pytest
from sqlalchemy import select

from app.config import Settings
from app.langgraph.events import RunEventBus
from app.langgraph.pipeline import PipelineBuilder, PipelineVariant
from app.langgraph.router import PhaseRouter
from app.langgraph.run_step_store import SqlRunStepStore
from app.langgraph.runtime import WorkflowRuntime
from app.langgraph.steps.factory import PipelineStepFactory, StepDeps
from app.langgraph.trace_sink import ToolCallTraceContext, TraceSink
from app.llm.decorators.trace import LLMTraceContext
from app.models.mysql.run_step import RunStepRow
from app.models.mysql.workflow_run import WorkflowRunRow
from app.repositories.run_repo import SqlWorkflowRunRepo
from app.utils.clock import utcnow


class _NullRegistry:
    async def get_by_id(self, tid, v=None):  # pragma: no cover
        raise NotImplementedError

    def simulator_of(self, tpl):  # pragma: no cover
        raise NotImplementedError


@pytest.mark.asyncio
async def test_runtime_writes_run_and_steps_to_db(session_factory) -> None:
    from app.services.design_validator import DesignValidator
    from app.services.forest_parser import ForestParser

    settings = Settings(LLM_API_KEY="t", WORKFLOW_GLOBAL_TIMEOUT=30)
    deps = StepDeps(
        event_bus=RunEventBus(None),
        trace_sink=TraceSink(None),
        tool_trace_ctx=ToolCallTraceContext(),
        llm_trace_ctx=LLMTraceContext(),
        run_step_store=SqlRunStepStore(session_factory),  # ← 真 SQL 写
        settings=settings,
        llm_client=None,
        tool_registry=_NullRegistry(),
        design_validator=DesignValidator(),
        forest_parser=ForestParser(_NullRegistry()),
    )
    factory = PipelineStepFactory(deps)
    router = PhaseRouter(factory, settings)
    builder = PipelineBuilder(factory, router)
    runtime = WorkflowRuntime(
        builder=builder,
        events=RunEventBus(None),
        settings=settings,
        session_factory=session_factory,
        worker_id="test-pod-1",
    )

    # 执行 Phase1_Only(空场景 → scenario_run fail → Pipeline 正常收尾,final_verdict=invalid)
    run_id = "r_db_test_01"
    final = await runtime.run(
        run_id=run_id,
        graph_version_id="gv_x",
        raw_graph_json={"bundles": [], "node_instances": [], "edges": []},
        variant=PipelineVariant.PHASE1_ONLY,
        triggered_by=1,
    )
    assert final["final_verdict"] == "invalid"

    # t_workflow_run 必须写入
    async with session_factory() as s:
        run_row = (
            await s.execute(select(WorkflowRunRow).where(WorkflowRunRow.id == run_id))
        ).scalar_one_or_none()
        assert run_row is not None, "runtime 必须写入 t_workflow_run"
        assert run_row.status == "success"  # pipeline 正常收尾,verdict 和 status 解耦
        assert run_row.final_verdict == "invalid"
        assert run_row.worker_id == "test-pod-1"
        assert run_row.started_at is not None
        assert run_row.finished_at is not None

        # t_run_step 至少 2 行(structure_check + scenario_run + 终止节点)
        step_rows = (
            await s.execute(select(RunStepRow).where(RunStepRow.run_id == run_id))
        ).scalars().all()
        assert len(step_rows) >= 2, "至少 2 个 step 应该入 t_run_step"
        names = {r.node_name for r in step_rows}
        assert "structure_check" in names
        assert "scenario_run" in names


@pytest.mark.asyncio
async def test_sql_workflow_run_repo_roundtrip(session_factory) -> None:
    repo = SqlWorkflowRunRepo(session_factory)
    await repo.create(
        run_id="r_crud",
        graph_version_id="gv",
        triggered_by=1,
        options={"variant": "phase1_only"},
        worker_id="w-1",
    )
    got = await repo.get("r_crud")
    assert got is not None
    assert got["status"] == "pending"
    assert got["worker_id"] == "w-1"

    await repo.update_status("r_crud", status="running", started_at=utcnow())
    got = await repo.get("r_crud")
    assert got["status"] == "running"

    await repo.heartbeat("r_crud", "w-2")
    got = await repo.get("r_crud")
    assert got["worker_id"] == "w-2"
    assert got["heartbeat_at"] is not None
