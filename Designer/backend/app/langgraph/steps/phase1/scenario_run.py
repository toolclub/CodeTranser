import json
from dataclasses import asdict
from time import perf_counter_ns
from typing import Any

from app.config import Settings
from app.domain.run.scenario import ScenarioResult
from app.langgraph.state import CascadeState
from app.langgraph.steps.phase1.attribution import attribute_failure
from app.langgraph.steps.phase1.base import Phase1HandlerBase
from app.langgraph.steps.phase1.comparator import deep_equal, diff_report
from app.langgraph.steps.phase1.executor import (
    NodeExecContext,
    build_tool_specs,
    make_executor,
)
from app.langgraph.steps.phase1.prompt import build_prompt_bundle
from app.llm.agent_loop import run_agent_loop
from app.llm.errors import LLMUnavailable
from app.services.forest_parser import ForestParser
from app.tool_runtime.registry import ToolRegistry


class ScenarioRunHandler(Phase1HandlerBase):
    """Phase1 Handler 2:LLM 驱动森林执行 + 字段级对比。

    任何场景失败 → Handler fail → Phase1 END → final=invalid。
    """

    name = "scenario_run"
    handler_order = 20
    depends_on = ("llm", "tool_registry", "forest_parser", "settings")

    def __init__(
        self,
        *,
        llm: Any,
        tool_registry: ToolRegistry,
        forest_parser: ForestParser,
        settings: Settings,
        **base_kw: Any,
    ) -> None:
        super().__init__(**base_kw)
        self._llm = llm
        self._registry = tool_registry
        self._parser = forest_parser
        self._settings = settings

    async def _handle(self, state: CascadeState, trace: dict[str, Any]) -> str:
        parsed = state.get("parsed_forest") or state.get("raw_graph_json")
        forest = self._parser.parse_readonly(
            graph_version_id=state.get("graph_version_id", ""),
            version_number=0,
            snapshot=parsed,
        )
        scenarios: list[dict[str, Any]] = (
            state.get("scenarios") or state.get("provided_scenarios") or []
        )
        state["scenarios"] = scenarios

        if not scenarios:
            trace["summary"] = "no scenarios provided"
            trace["errors"].append(
                {
                    "code": "NO_SCENARIO",
                    "message": "Phase1 Handler 2 requires at least one scenario",
                }
            )
            return "fail"

        results: list[dict[str, Any]] = []
        any_fail = False

        for s in scenarios:
            r = await self._run_one(forest, s, run_id=state["run_id"])
            results.append(asdict(r))
            if not r.match or r.error:
                any_fail = True

        state["scenario_results"] = results
        merged: dict[str, Any] = {}
        for r_dict in results:
            merged.update(r_dict.get("node_outputs", {}))
        state["node_outputs"] = merged

        if any_fail:
            failed = sum(1 for r in results if not r["match"] or r.get("error"))
            trace["summary"] = f"{failed}/{len(results)} scenarios failed"
            trace["details"]["scenario_results"] = results
            trace["errors"] = [
                {
                    "code": "SCENARIO_FAIL",
                    "scenario_id": r["scenario_id"],
                    "mismatch_detail": r.get("mismatch_detail"),
                    "attribution": r.get("attribution"),
                    "attribution_reason": r.get("attribution_reason"),
                }
                for r in results
                if not r["match"] or r.get("error")
            ]
            return "fail"

        trace["summary"] = f"{len(results)}/{len(results)} scenarios passed"
        trace["details"]["scenario_results"] = results
        return "pass"

    async def _run_one(
        self, forest: Any, scenario: dict[str, Any], *, run_id: str
    ) -> ScenarioResult:
        t0 = perf_counter_ns()
        max_iter = self._settings.PHASE1_AGENT_MAX_ITER
        pb = build_prompt_bundle(
            forest=forest,
            scenario_input=scenario["input_json"],
            scenario_description=scenario.get("description", ""),
            max_iterations=max_iter,
        )
        tools = build_tool_specs(forest)
        exec_ctx = NodeExecContext(
            forest=forest,
            tables=dict(scenario.get("tables") or {}),
            run_id=run_id,
            tool_registry=self._registry,
            llm_client=self._llm,
            tool_trace=self._tool_ctx,
            per_node_limit=self._settings.PHASE1_PER_NODE_CALL_LIMIT,
        )
        executor = make_executor(exec_ctx)

        try:
            agent_result = await run_agent_loop(
                provider=self._llm,
                system=pb.system,
                initial_user=pb.initial_user,
                tools=tools,
                tool_executor=executor,
                max_iterations=max_iter,
                model=self._settings.PHASE1_LLM_MODEL,
                temperature=0.0,
                node_name=f"scenario:{scenario.get('scenario_id', scenario['name'])}",
            )
        except LLMUnavailable as e:
            return ScenarioResult(
                scenario_id=scenario.get("scenario_id", ""),
                actual_output=None,
                match=False,
                error=f"llm unavailable: {e}",
                duration_ms=(perf_counter_ns() - t0) // 1_000_000,
                agent_stopped_reason="llm_error",
            )

        try:
            actual = _parse_final_json(agent_result.final_text)
        except Exception as e:
            return ScenarioResult(
                scenario_id=scenario.get("scenario_id", ""),
                actual_output=agent_result.final_text,
                match=False,
                error=f"final_text not json: {e}",
                duration_ms=(perf_counter_ns() - t0) // 1_000_000,
                agent_stopped_reason=agent_result.stopped_reason,
                tool_call_count=agent_result.tool_call_count,
                llm_call_count=len(agent_result.steps),
                node_outputs=dict(exec_ctx.node_outputs),
            )

        expected = scenario["expected_output"]
        match = deep_equal(expected, actual)
        mismatch = None if match else diff_report(expected, actual)

        attribution = None
        attribution_reason = None
        if not match:
            try:
                attr = await attribute_failure(
                    llm=self._llm,
                    scenario=scenario,
                    actual=actual,
                    diff=mismatch or [],
                    tool_call_trace=[],
                    run_id=run_id,
                )
                attribution = attr.get("attribution")
                attribution_reason = attr.get("reason")
            except Exception:
                attribution = "unknown"
                attribution_reason = None

        return ScenarioResult(
            scenario_id=scenario.get("scenario_id", ""),
            actual_output=actual,
            match=match,
            mismatch_detail={"diff": mismatch} if mismatch else None,
            node_outputs=dict(exec_ctx.node_outputs),
            tool_call_count=agent_result.tool_call_count,
            llm_call_count=len(agent_result.steps),
            duration_ms=(perf_counter_ns() - t0) // 1_000_000,
            attribution=attribution,
            attribution_reason=attribution_reason,
            agent_stopped_reason=agent_result.stopped_reason,
        )


def _parse_final_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return json.loads(cleaned)
