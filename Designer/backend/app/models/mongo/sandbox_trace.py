from datetime import datetime
from typing import Any, Literal, Optional, TypedDict


class SandboxTrace(TypedDict, total=False):
    _id: Any
    run_id: str
    kind: Literal["compile", "test_run"]
    snapshot_id: str
    case_id: Optional[str]
    cmd: list[str]
    stdin: Optional[bytes]
    stdout: str
    stderr: str
    exit_code: int
    signal: Optional[str]
    duration_ms: int
    cpu_peak_pct: Optional[float]
    mem_peak_mb: Optional[int]
    meta: dict[str, Any]
    schema_version: int
    created_at: datetime
