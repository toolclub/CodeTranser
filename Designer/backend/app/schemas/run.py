from typing import Any, Literal

from pydantic import BaseModel, Field


class ScenarioInDTO(BaseModel):
    name: str = Field(..., max_length=256)
    input_json: dict[str, Any]
    expected_output: dict[str, Any]
    tables: dict[str, list[Any]] = {}
    description: str = ""
    target_root: str | None = None


class RunTriggerDTO(BaseModel):
    graph_version_id: str
    scenarios: list[ScenarioInDTO] = []
    options: dict[str, Any] = {}


class RunHandleDTO(BaseModel):
    run_id: str
    status: Literal["pending", "running", "success", "failed", "cancelled"]


class PhaseSummaryDTO(BaseModel):
    phase: int
    verdict: str | None
    started_at: str | None
    finished_at: str | None
    step_count: int


class RunDetailDTO(BaseModel):
    run_id: str
    graph_version_id: str
    status: str
    phases: list[PhaseSummaryDTO]
    final_verdict: str | None
    review_status: str
    created_at: str
