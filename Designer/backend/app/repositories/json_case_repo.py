from abc import ABC, abstractmethod
from typing import Any, Sequence

from sqlalchemy import select, update

from app.models.mysql.json_case import JsonCaseRow
from app.repositories.base import SqlRepoBase
from app.utils.ids import new_id


class JsonCaseRepo(ABC):
    @abstractmethod
    async def create_many(self, run_id: str, scenarios: list[dict[str, Any]]) -> list[str]: ...

    @abstractmethod
    async def update_result(
        self,
        case_id: str,
        *,
        actual_output_json: dict[str, Any] | None,
        verdict: str,
        reason: str | None,
    ) -> None: ...

    @abstractmethod
    async def list_by_run(self, run_id: str) -> Sequence[JsonCaseRow]: ...


class SqlJsonCaseRepo(SqlRepoBase, JsonCaseRepo):
    async def create_many(self, run_id: str, scenarios: list[dict[str, Any]]) -> list[str]:
        ids: list[str] = []
        for s in scenarios:
            cid = s.get("scenario_id") or new_id("jc", 12)
            self._s.add(
                JsonCaseRow(
                    id=cid,
                    run_id=run_id,
                    scenario_name=s["name"],
                    input_json=s["input_json"],
                    expected_output_json=s["expected_output"],
                    actual_output_json=None,
                    verdict=None,
                    reason=None,
                    created_by_step_id=s.get("step_id", ""),
                )
            )
            ids.append(cid)
        await self._s.flush()
        return ids

    async def update_result(
        self,
        case_id: str,
        *,
        actual_output_json: dict[str, Any] | None,
        verdict: str,
        reason: str | None,
    ) -> None:
        await self._s.execute(
            update(JsonCaseRow)
            .where(JsonCaseRow.id == case_id)
            .values(
                actual_output_json=actual_output_json,
                verdict=verdict,
                reason=reason,
            )
        )

    async def list_by_run(self, run_id: str) -> Sequence[JsonCaseRow]:
        return list(
            (
                await self._s.execute(
                    select(JsonCaseRow).where(JsonCaseRow.run_id == run_id)
                )
            ).scalars().all()
        )
