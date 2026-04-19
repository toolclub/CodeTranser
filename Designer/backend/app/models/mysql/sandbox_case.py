from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class SandboxCaseRow(Base):
    __tablename__ = "t_sandbox_case"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(256), nullable=False)
    input_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    input_spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    expected: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actual: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timeout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
