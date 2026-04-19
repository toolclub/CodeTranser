import pytest

from app.domain.fsm import (
    FSM,
    IllegalTransition,
    Phase1HandlerSM,
    Phase1HandlerStatus,
    RunStepSM,
    RunStepStatus,
    WorkflowRunSM,
    WorkflowRunStatus,
)


def test_workflow_run_happy_path() -> None:
    sm = WorkflowRunSM.from_status(WorkflowRunStatus.PENDING)
    assert sm.current is WorkflowRunStatus.PENDING
    sm.fire("start")
    assert sm.current is WorkflowRunStatus.RUNNING
    sm.fire("finish")
    assert sm.current is WorkflowRunStatus.SUCCESS


def test_workflow_run_cannot_skip_states() -> None:
    sm = WorkflowRunSM.from_status(WorkflowRunStatus.PENDING)
    with pytest.raises(IllegalTransition):
        sm.fire("finish")  # 直接 pending→success 是非法


def test_workflow_run_transition_to_helper() -> None:
    sm = WorkflowRunSM.from_status(WorkflowRunStatus.PENDING)
    sm.transition_to(WorkflowRunStatus.RUNNING)
    assert sm.current_value == "running"
    sm.transition_to("failed")
    assert sm.current is WorkflowRunStatus.FAILED


def test_from_status_accepts_string() -> None:
    sm: FSM = WorkflowRunSM.from_status("running")
    assert sm.current is WorkflowRunStatus.RUNNING


def test_run_step_transitions() -> None:
    sm = RunStepSM.from_status(RunStepStatus.PENDING)
    sm.fire("start")
    assert sm.current is RunStepStatus.RUNNING
    sm.fire("fail")
    assert sm.current is RunStepStatus.FAILED
    with pytest.raises(IllegalTransition):
        sm.fire("finish")  # 失败态不能再 finish


def test_phase1_handler_pending_to_pass_via_running() -> None:
    sm = Phase1HandlerSM.from_status(Phase1HandlerStatus.PENDING)
    sm.fire("start")
    sm.fire("pass")
    assert sm.current is Phase1HandlerStatus.PASSED


def test_phase1_handler_can_skip_without_running() -> None:
    sm = Phase1HandlerSM.from_status(Phase1HandlerStatus.PENDING)
    sm.fire("skip")
    assert sm.current is Phase1HandlerStatus.SKIPPED
