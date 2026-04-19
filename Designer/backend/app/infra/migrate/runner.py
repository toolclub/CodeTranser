import hashlib
from pathlib import Path

from sqlalchemy import text

from app.config import Settings
from app.infra.db.session import create_engine
from app.infra.logging import get_logger

log = get_logger(__name__)
SQL_DIR = Path(__file__).resolve().parents[3] / "config" / "sql"


class MigrationError(Exception):
    pass


async def run_migrations(settings: Settings, sql_dir: Path | None = None) -> list[str]:
    """按字典序跑 config/sql/*.ddl,返回本次实际执行的文件名列表。"""
    base = sql_dir or SQL_DIR
    files = sorted(base.glob("*.ddl"))
    if not files:
        raise MigrationError(f"no .ddl under {base}")

    engine = create_engine(settings)
    executed: list[str] = []

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS t_migration_applied (
                  file_name   VARCHAR(128) PRIMARY KEY,
                  checksum    VARCHAR(64)  NOT NULL,
                  applied_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
                """
            )
        )

    try:
        for f in files:
            body = f.read_text(encoding="utf-8")
            checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
            async with engine.begin() as conn:
                row = (
                    await conn.execute(
                        text("SELECT checksum FROM t_migration_applied WHERE file_name = :fn"),
                        {"fn": f.name},
                    )
                ).first()
                if row is not None:
                    if row[0] != checksum:
                        raise MigrationError(
                            f"ddl {f.name} checksum changed; history is immutable"
                        )
                    log.info("migration_skip", file=f.name)
                    continue
                log.info("migration_apply", file=f.name)
                for stmt in split_statements(body):
                    if stmt.strip():
                        await conn.execute(text(stmt))
                await conn.execute(
                    text(
                        "INSERT INTO t_migration_applied (file_name, checksum) VALUES (:fn, :cs)"
                    ),
                    {"fn": f.name, "cs": checksum},
                )
                executed.append(f.name)
    finally:
        await engine.dispose()

    return executed


def split_statements(sql: str) -> list[str]:
    """朴素分号拆分。忽略 `--` 行注释;不处理字符串里带 ; 的情况(v1 DDL 不涉及)。"""
    out: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            joined = "\n".join(buf)
            out.append(joined[: joined.rfind(";")])
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        out.append(tail)
    return out
