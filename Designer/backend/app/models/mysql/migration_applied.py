from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class MigrationAppliedRow(Base):
    __tablename__ = "t_migration_applied"

    file_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime)
