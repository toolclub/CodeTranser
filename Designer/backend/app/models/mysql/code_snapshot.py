from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class CodeSnapshotRow(Base):
    __tablename__ = "t_code_snapshot"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    files: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    overall_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issues_fixed: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    node_to_code: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)
