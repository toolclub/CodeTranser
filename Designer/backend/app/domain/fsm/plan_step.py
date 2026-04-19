from enum import Enum

from app.domain.fsm.base import FSM


class PlanStepStatus(str, Enum):
    """对齐 ChatFlow plan_step.py(pending → running → done|failed)。供未来代码生成 planner 用。"""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class PlanStepSM(FSM[PlanStepStatus]):
    STATUS_ENUM = PlanStepStatus
    TRANSITIONS = {
        (PlanStepStatus.PENDING, "start"): PlanStepStatus.RUNNING,
        (PlanStepStatus.RUNNING, "finish"): PlanStepStatus.DONE,
        (PlanStepStatus.RUNNING, "fail"): PlanStepStatus.FAILED,
    }
