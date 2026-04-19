from enum import Enum

from app.domain.fsm.base import FSM


class RunStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStepSM(FSM[RunStepStatus]):
    """单个 PipelineStep(`t_run_step`)的状态机。对齐 Ch01 DDL 里的 status 枚举。"""

    STATUS_ENUM = RunStepStatus
    TRANSITIONS = {
        (RunStepStatus.PENDING, "start"): RunStepStatus.RUNNING,
        (RunStepStatus.RUNNING, "finish"): RunStepStatus.SUCCESS,
        (RunStepStatus.RUNNING, "fail"): RunStepStatus.FAILED,
        (RunStepStatus.PENDING, "skip"): RunStepStatus.SKIPPED,
    }
