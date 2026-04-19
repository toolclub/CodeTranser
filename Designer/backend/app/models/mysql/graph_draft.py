from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class GraphDraftRow(Base):
    __tablename__ = "t_graph_draft"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    graph_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    saved_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
