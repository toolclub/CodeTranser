"""轻量 FSM 基类 + 各业务状态机(ChatFlow spec 派生)。

铁律:**所有 DB status 字段变更必须走 FSM**,非法转换 raise,永远不从外部字符串裸赋值。
"""

from app.domain.fsm.base import FSM, IllegalTransition
from app.domain.fsm.plan_step import PlanStepSM, PlanStepStatus
from app.domain.fsm.run_step import RunStepSM, RunStepStatus
from app.domain.fsm.workflow_run import (
    PHASE1_TERMINAL_HANDLER_STATUSES,
    Phase1HandlerSM,
    Phase1HandlerStatus,
    WorkflowRunSM,
    WorkflowRunStatus,
)

__all__ = [
    "FSM",
    "IllegalTransition",
    "PHASE1_TERMINAL_HANDLER_STATUSES",
    "Phase1HandlerSM",
    "Phase1HandlerStatus",
    "PlanStepSM",
    "PlanStepStatus",
    "RunStepSM",
    "RunStepStatus",
    "WorkflowRunSM",
    "WorkflowRunStatus",
]
