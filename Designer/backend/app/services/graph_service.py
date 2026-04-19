from dataclasses import asdict
from typing import Any

from app.domain.errors import BusinessError, Forbidden
from app.domain.graph.visitors.diff import ForestDiff, diff as forest_diff
from app.middlewares.auth import CurrentUser
from app.repositories.graph_draft_repo import GraphDraftRepo
from app.repositories.graph_repo import GraphRepo
from app.repositories.graph_version_repo import GraphVersionRepo
from app.schemas.graph import (
    ForestSnapshotDTO,
    GraphCreateDTO,
    GraphVersionSaveDTO,
)
from app.services.design_validator import DesignValidator, ValidationReport
from app.services.forest_parser import ForestParser

_FATAL_CODES: set[str] = {
    "VALIDATION_GRAPH_HAS_CYCLE",
    "VALIDATION_NODE_REF_INVALID",
    "VALIDATION_EDGE_SELF_LOOP",
    "VALIDATION_BUNDLE_MEMBERSHIP",
    "VALIDATION_EDGE_SEMANTIC_INVALID",
    "VALIDATION_EDGE_DUPLICATE",
}


class GraphService:
    def __init__(
        self,
        graph_repo: GraphRepo,
        gv_repo: GraphVersionRepo,
        draft_repo: GraphDraftRepo,
        parser: ForestParser,
        design_validator: DesignValidator | None = None,
    ) -> None:
        self._gr = graph_repo
        self._gv = gv_repo
        self._gd = draft_repo
        self._parser = parser
        self._dv = design_validator or DesignValidator()

    @property
    def graph_repo(self) -> GraphRepo:
        return self._gr

    @property
    def version_repo(self) -> GraphVersionRepo:
        return self._gv

    async def create(self, dto: GraphCreateDTO, user: CurrentUser) -> str:
        return await self._gr.create(dto.name, dto.description, user.id)

    async def save_version(
        self,
        graph_id: str,
        dto: GraphVersionSaveDTO,
        user: CurrentUser,
    ) -> str:
        g = await self._gr.get(graph_id)
        if g.owner_id != user.id and not user.is_admin:
            raise Forbidden("not your graph")

        snap_dict = dto.snapshot.model_dump(by_alias=True)
        snap_dict = await self._parser.freeze_snapshot(snap_dict)

        forest = self._parser.parse_readonly(
            graph_version_id="(pending)", version_number=0, snapshot=snap_dict
        )
        report = self._dv.run(forest)
        if not report.ok:
            for err in report.errors:
                if err["code"] in _FATAL_CODES:
                    raise BusinessError(err["message"], **err.get("extra", {}))
            # 非致命(如 FieldValueInvalid):允许保存,warnings 带进 metadata
            snap_dict.setdefault("metadata", {})["validation_warnings"] = (
                report.errors + report.warnings
            )

        row = await self._gv.save_new(
            graph_id,
            snap_dict,
            dto.commit_message,
            dto.parent_version_id,
            user.id,
        )
        await self._gr.set_latest_version(graph_id, row.id)
        await self._gd.clear(graph_id)
        return row.id

    async def get_version(self, graph_id: str, version_number: int) -> dict[str, Any]:
        v = await self._gv.get_by_number(graph_id, version_number)
        return dict(v.snapshot)

    async def list_versions(self, graph_id: str) -> list[dict[str, Any]]:
        rs = await self._gv.list(graph_id)
        return [
            {
                "id": r.id,
                "version_number": r.version_number,
                "commit_message": r.commit_message,
                "parent_version_id": r.parent_version_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rs
        ]

    async def diff_versions(
        self, graph_id: str, v1: int, v2: int
    ) -> ForestDiff:
        a = await self._gv.get_by_number(graph_id, v1)
        b = await self._gv.get_by_number(graph_id, v2)
        fa = self._parser.parse_readonly(
            graph_version_id=a.id,
            version_number=a.version_number,
            snapshot=dict(a.snapshot),
        )
        fb = self._parser.parse_readonly(
            graph_version_id=b.id,
            version_number=b.version_number,
            snapshot=dict(b.snapshot),
        )
        return forest_diff(fa, fb)

    async def save_draft(
        self, graph_id: str, snapshot: ForestSnapshotDTO, user: CurrentUser
    ) -> None:
        await self._gd.upsert(
            graph_id, snapshot.model_dump(by_alias=True), user.id
        )

    async def get_draft(self, graph_id: str) -> dict[str, Any] | None:
        d = await self._gd.get(graph_id)
        return dict(d.snapshot) if d else None

    async def validate_snapshot(self, snap: ForestSnapshotDTO) -> ValidationReport:
        snap_dict = snap.model_dump(by_alias=True)
        snap_dict = await self._parser.freeze_snapshot(snap_dict)
        forest = self._parser.parse_readonly(
            graph_version_id="(validate)", version_number=0, snapshot=snap_dict
        )
        return self._dv.run(forest)

    def diff_to_dict(self, d: ForestDiff) -> dict[str, Any]:
        return asdict(d)
