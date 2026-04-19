from app.domain.errors import BusinessError, DependencyError, DomainError


class PipelineError(DomainError):
    code = "PIPELINE_UNEXPECTED"


class StepFailed(PipelineError):
    code = "PIPELINE_STEP_FAILED"


class IterationExhausted(BusinessError):
    code = "PIPELINE_ITERATION_EXHAUSTED"


class WorkflowTimeout(DependencyError):
    code = "PIPELINE_TIMEOUT"


class HandlerRouteError(PipelineError):
    code = "PIPELINE_HANDLER_ROUTE"
