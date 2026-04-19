from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class WorkflowRunRow(Base):
    __tablename__ = "t_workflow_run"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    graph_version_id: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    triggered_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    phase1_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    phase2_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    phase3_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    final_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    archive_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # 分布式运维(03.ddl):记录最后 heartbeat + 当前 worker pod,便于 K8S 下排查卡死 Run
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
