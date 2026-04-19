from enum import Enum

from app.domain.fsm.base import FSM


class WorkflowRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowRunSM(FSM[WorkflowRunStatus]):
    """WorkflowRun 生命周期。

    pending ─start→ running ─finish→ success
                              ├─fail──→ failed
                              └─cancel→ cancelled
    """

    STATUS_ENUM = WorkflowRunStatus
    TRANSITIONS = {
        (WorkflowRunStatus.PENDING, "start"): WorkflowRunStatus.RUNNING,
        (WorkflowRunStatus.RUNNING, "finish"): WorkflowRunStatus.SUCCESS,
        (WorkflowRunStatus.RUNNING, "fail"): WorkflowRunStatus.FAILED,
        (WorkflowRunStatus.RUNNING, "cancel"): WorkflowRunStatus.CANCELLED,
    }


class Phase1HandlerStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "pass"
    FAILED = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


PHASE1_TERMINAL_HANDLER_STATUSES = frozenset(
    {Phase1HandlerStatus.PASSED, Phase1HandlerStatus.FAILED, Phase1HandlerStatus.ERROR, Phase1HandlerStatus.SKIPPED}
)


class Phase1HandlerSM(FSM[Phase1HandlerStatus]):
    """Phase1 Handler 执行态(替换 handler_traces[*].status 的裸字符串)。

    pending ─start→ running ─pass/fail/error/skip→ terminal
    """

    STATUS_ENUM = Phase1HandlerStatus
    TRANSITIONS = {
        (Phase1HandlerStatus.PENDING, "start"): Phase1HandlerStatus.RUNNING,
        (Phase1HandlerStatus.RUNNING, "pass"): Phase1HandlerStatus.PASSED,
        (Phase1HandlerStatus.RUNNING, "fail"): Phase1HandlerStatus.FAILED,
        (Phase1HandlerStatus.RUNNING, "error"): Phase1HandlerStatus.ERROR,
        (Phase1HandlerStatus.RUNNING, "skip"): Phase1HandlerStatus.SKIPPED,
        (Phase1HandlerStatus.PENDING, "skip"): Phase1HandlerStatus.SKIPPED,
    }
