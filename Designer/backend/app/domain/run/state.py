from typing import Any, Iterable, Literal, Optional, TypedDict

Decision = Literal[
    "fix_spec",
    "add_scenario",
    "fix_code",
    "design_bug",
    "done",
    "in_progress",
    "handler_pass",
    "handler_fail",
]

Phase1Verdict = Literal["valid", "invalid", "inconclusive"]
Phase3Verdict = Literal["done", "design_bug", "fix_exhausted"]
FinalVerdict = Literal["valid", "invalid", "inconclusive"]


class HandlerTrace(TypedDict, total=False):
    handler_name: str
    status: Literal["pass", "fail", "skipped", "error"]
    started_at: str
    finished_at: str
    summary: str
    details: dict[str, Any]
    errors: list[dict[str, Any]]


class CascadeState(TypedDict, total=False):
    run_id: str
    graph_version_id: str

    raw_graph_json: dict[str, Any]
    parsed_forest: Optional[dict[str, Any]]
    validation_errors: list[dict[str, Any]]
    phase1_verdict: Optional[Phase1Verdict]

    handler_traces: list[HandlerTrace]
    current_handler: Optional[str]

    provided_scenarios: list[dict[str, Any]]
    scenarios: list[dict[str, Any]]
    scenario_results: list[dict[str, Any]]
    node_outputs: dict[str, dict[str, Any]]

    json_spec: Optional[dict[str, Any]]
    inner_sdd_iter: int
    inner_tdd_iter: int

    code_skeleton: Optional[dict[str, Any]]
    code_units: list[dict[str, Any]]
    composite_code: Optional[dict[str, Any]]
    code_snapshot_ids: list[str]
    static_issues: list[dict[str, Any]]
    compile_result: Optional[dict[str, Any]]
    sandbox_cases: list[dict[str, Any]]
    execution_results: list[dict[str, Any]]
    outer_fix_iter: int
    phase3_verdict: Optional[Phase3Verdict]

    decision: Decision
    final_verdict: Optional[FinalVerdict]

    messages: list[dict[str, Any]]
    step_history: list[str]


def initial_state(
    run_id: str,
    graph_version_id: str,
    raw: dict[str, Any],
    provided_scenarios: Iterable[dict[str, Any]] | None = None,
) -> CascadeState:
    return CascadeState(
        run_id=run_id,
        graph_version_id=graph_version_id,
        raw_graph_json=raw,
        parsed_forest=None,
        validation_errors=[],
        phase1_verdict=None,
        handler_traces=[],
        current_handler=None,
        provided_scenarios=list(provided_scenarios or []),
        scenarios=[],
        scenario_results=[],
        node_outputs={},
        json_spec=None,
        inner_sdd_iter=0,
        inner_tdd_iter=0,
        code_skeleton=None,
        code_units=[],
        composite_code=None,
        code_snapshot_ids=[],
        static_issues=[],
        compile_result=None,
        sandbox_cases=[],
        execution_results=[],
        outer_fix_iter=0,
        phase3_verdict=None,
        decision="in_progress",
        final_verdict=None,
        messages=[],
        step_history=[],
    )
