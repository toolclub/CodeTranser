from app.domain.errors import BusinessError


class GraphParseError(BusinessError):
    code = "VALIDATION_GRAPH_PARSE"


class GraphHasCycle(BusinessError):
    code = "VALIDATION_GRAPH_HAS_CYCLE"


class NodeRefInvalid(BusinessError):
    code = "VALIDATION_NODE_REF_INVALID"


class BundleMembershipConflict(BusinessError):
    code = "VALIDATION_BUNDLE_MEMBERSHIP"


class EdgeSemanticInvalid(BusinessError):
    code = "VALIDATION_EDGE_SEMANTIC_INVALID"


class FieldValueInvalid(BusinessError):
    code = "VALIDATION_FIELD_VALUE_INVALID"


class SelfLoopEdge(BusinessError):
    code = "VALIDATION_EDGE_SELF_LOOP"


class DuplicateEdge(BusinessError):
    code = "VALIDATION_EDGE_DUPLICATE"


class StaleVersion(BusinessError):
    code = "CONFLICT_STALE_VERSION"
    http_status = 409
