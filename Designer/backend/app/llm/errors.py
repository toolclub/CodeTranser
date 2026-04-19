from app.domain.errors import BusinessError, DependencyError


class LLMUnavailable(DependencyError):
    code = "DEPENDENCY_LLM_UNAVAILABLE"
    http_status = 503


class LLMTimeout(DependencyError):
    code = "DEPENDENCY_LLM_TIMEOUT"


class LLMRateLimited(DependencyError):
    code = "DEPENDENCY_LLM_RATE_LIMITED"


class LLMSchemaError(BusinessError):
    code = "DEPENDENCY_LLM_SCHEMA_MISMATCH"
    http_status = 422


class LLMProtocolError(BusinessError):
    code = "DEPENDENCY_LLM_PROTOCOL_ERROR"


class TransientLLMError(Exception):
    """内部使用:可重试的网络/5xx/限流错误。RetryDecorator 认识它。"""

    def __init__(self, msg: str, retry_after: float | None = None) -> None:
        super().__init__(msg)
        self.retry_after = retry_after
