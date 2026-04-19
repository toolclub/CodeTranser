from typing import Any


class DomainError(Exception):
    code: str = "INTERNAL_UNEXPECTED"
    http_status: int = 500

    def __init__(self, message: str = "", **extra: Any) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code
        self.extra = extra


class NotFound(DomainError):
    code = "NOT_FOUND"
    http_status = 404


class Forbidden(DomainError):
    code = "PERM_DENIED"
    http_status = 403


class Unauthorized(DomainError):
    code = "AUTH_UNAUTHORIZED"
    http_status = 401


class Conflict(DomainError):
    code = "CONFLICT_STALE_VERSION"
    http_status = 409


class TooManyRequests(DomainError):
    code = "RATE_LIMITED"
    http_status = 429


class BusinessError(DomainError):
    http_status = 422


class ValidationError(BusinessError):
    code = "VALIDATION_FAILED"


class TemplateSchemaInvalid(BusinessError):
    code = "VALIDATION_TEMPLATE_SCHEMA_INVALID"


class GraphHasCycle(BusinessError):
    code = "VALIDATION_GRAPH_HAS_CYCLE"


class InvalidDesign(BusinessError):
    code = "BUSINESS_PHASE1_INVALID_DESIGN"


class MissingSimulator(BusinessError):
    code = "BUSINESS_MISSING_SIMULATOR"


class DependencyError(DomainError):
    http_status = 503


class LLMUnavailable(DependencyError):
    code = "DEPENDENCY_LLM_UNAVAILABLE"


class LLMSchemaError(DependencyError):
    code = "DEPENDENCY_LLM_SCHEMA_MISMATCH"


class SandboxUnavailable(DependencyError):
    code = "DEPENDENCY_SANDBOX_UNAVAILABLE"


class SandboxTimeout(DependencyError):
    code = "DEPENDENCY_SANDBOX_TIMEOUT"
