from dataclasses import dataclass, field
from typing import Any

from app.domain.tool.tool import Engine


@dataclass(slots=True)
class SimContext:
    run_id: str
    instance_id: str
    table_data: dict[str, list[Any]] = field(default_factory=dict)
    llm: Any = None
    trace: Any = None

    def get_table(self, name: str) -> list[Any]:
        return self.table_data.get(name, [])


@dataclass(slots=True)
class SimResult:
    output: dict[str, Any]
    engine_used: Engine
    llm_call_ref: str | None = None
    duration_ms: int = 0
    error: str | None = None
