from app.domain.errors import BusinessError, DependencyError


class NodeTemplateNotFound(BusinessError):
    code = "TOOL_NOT_FOUND"
    http_status = 404


class TemplateDefinitionInvalid(BusinessError):
    code = "VALIDATION_TEMPLATE_SCHEMA_INVALID"


class SimulatorNotRegistered(BusinessError):
    code = "BUSINESS_MISSING_SIMULATOR"


class SimulatorInputInvalid(BusinessError):
    code = "VALIDATION_SIM_INPUT_INVALID"


class SimulatorOutputInvalid(BusinessError):
    code = "VALIDATION_SIM_OUTPUT_INVALID"


class ToolLLMFailed(DependencyError):
    code = "DEPENDENCY_LLM_UNAVAILABLE"


class MetaTemplateError(BusinessError):
    code = "META_TEMPLATE_INVALID"
