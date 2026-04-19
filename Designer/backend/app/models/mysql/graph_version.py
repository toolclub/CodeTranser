from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class GraphVersionRow(Base):
    __tablename__ = "t_graph_version"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    graph_id: Mapped[str] = mapped_column(String(32), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    commit_message: Mapped[str] = mapped_column(String(1024), default="")
    parent_version_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)
