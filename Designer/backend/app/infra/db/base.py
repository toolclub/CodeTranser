from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase

from app.utils.clock import utcnow


class Base(DeclarativeBase):
    """Declarative base for all MySQL ORM rows.

    ORM 类仅做 CRUD,不负责建表;建表走 config/sql/*.ddl。
    """


_TIMESTAMP_FIELDS_ON_INSERT = ("created_at", "updated_at", "applied_at")


@event.listens_for(Base, "before_insert", propagate=True)
def _fill_timestamps_on_insert(_mapper: Any, _conn: Any, target: Any) -> None:
    """在 SQLite 等没有 CURRENT_TIMESTAMP 默认值的情况下,由应用层兜底填写。
    MySQL 生产环境 DDL 自带 DEFAULT CURRENT_TIMESTAMP(6),这里的赋值会被 INSERT 显式覆盖——
    两端行为一致。"""
    now = utcnow()
    for fld in _TIMESTAMP_FIELDS_ON_INSERT:
        if hasattr(target, fld) and getattr(target, fld, None) is None:
            setattr(target, fld, now)


@event.listens_for(Base, "before_update", propagate=True)
def _fill_updated_at_on_update(_mapper: Any, _conn: Any, target: Any) -> None:
    if hasattr(target, "updated_at"):
        setattr(target, "updated_at", utcnow())
