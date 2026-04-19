from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP total",
    ["method", "path", "status"],
    registry=REGISTRY,
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP dur",
    ["method", "path"],
    registry=REGISTRY,
)

TOOL_CALLS = Counter(
    "tool_calls_total",
    "Tool calls",
    ["tool_name", "engine", "verdict"],
    registry=REGISTRY,
)
TOOL_CALL_DUR = Histogram(
    "tool_call_duration_seconds",
    "Tool dur",
    ["tool_name", "engine"],
    registry=REGISTRY,
)

LLM_CALLS = Counter(
    "llm_calls_total",
    "LLM calls",
    ["model", "node_name"],
    registry=REGISTRY,
)
LLM_TOKENS = Counter(
    "llm_tokens_total",
    "LLM tokens",
    ["model", "kind"],
    registry=REGISTRY,
)

RUN_TOTAL = Counter(
    "workflow_run_total",
    "Run total",
    ["phase1_verdict", "phase3_verdict", "final_verdict"],
    registry=REGISTRY,
)
RUN_PHASE_DUR = Histogram(
    "workflow_run_duration_seconds",
    "Run dur",
    ["phase"],
    registry=REGISTRY,
)

SANDBOX_COMPILE = Counter(
    "sandbox_compile_total",
    "sandbox compile",
    ["verdict"],
    registry=REGISTRY,
)
SANDBOX_RUN = Counter(
    "sandbox_run_total",
    "sandbox run",
    ["verdict"],
    registry=REGISTRY,
)
SANDBOX_POOL = Gauge(
    "sandbox_pool_available",
    "sandbox pool",
    registry=REGISTRY,
)

PHASE1_EARLY_TERM = Counter(
    "phase1_early_termination_total",
    "design_bug 提前终止次数",
    registry=REGISTRY,
)

INNER_SDD_ITER = Histogram("inner_sdd_iterations", "inner sdd iters", registry=REGISTRY)
INNER_TDD_ITER = Histogram("inner_tdd_iterations", "inner tdd iters", registry=REGISTRY)
OUTER_FIX_ITER = Histogram("outer_fix_iterations", "outer fix iters", registry=REGISTRY)
