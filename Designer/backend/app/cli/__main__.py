import asyncio
from typing import Awaitable, Callable

import click

from app.bootstrap import AppContainer, build_container, shutdown, startup
from app.config import get_settings


@click.group()
def cli() -> None:
    """Cascade backend CLI."""


async def _run(action: Callable[[AppContainer], Awaitable[None]]) -> None:
    settings = get_settings()
    container = build_container(settings)
    await startup(container)
    try:
        await action(container)
    finally:
        await shutdown(container)


@cli.command()
def version() -> None:
    click.echo("cascade-backend 0.1.0")


@cli.command()
def migrate() -> None:
    """按字典序跑 config/sql/*.ddl,已跑过的跳过;历史被改抛错。"""
    from app.infra.migrate.runner import run_migrations

    async def _do(c: AppContainer) -> None:
        applied = await run_migrations(c.settings)
        if applied:
            for f in applied:
                click.echo(f"[migrate] applied {f}")
        else:
            click.echo("[migrate] up-to-date")

    asyncio.run(_run(_do))


@cli.command("init_mongo_indexes")
def init_mongo_indexes() -> None:
    """初始化 Mongo 索引 + TTL。"""
    from app.cli.init_mongo_indexes import ensure_indexes

    async def _do(c: AppContainer) -> None:
        if c.mongo_db is None:
            click.echo("[init_mongo_indexes] mongo disabled; skip")
            return
        await ensure_indexes(c.mongo_db)
        click.echo("[init_mongo_indexes] ok")

    asyncio.run(_run(_do))


@cli.command("grant_admin")
@click.option("--external-id", required=True)
@click.option("--granted-by", default="cli")
def grant_admin(external_id: str, granted_by: str) -> None:
    """赋予 external_id 管理员权限。"""
    from app.infra.db.session import session_scope
    from app.repositories.user_repo import SqlAdminRepo

    async def _do(c: AppContainer) -> None:
        async with session_scope(c.session_factory) as s:
            await SqlAdminRepo(s).grant(external_id, granted_by)
        click.echo(f"[grant_admin] granted {external_id}")

    asyncio.run(_run(_do))


from app.cli.verify_simulators import main as _verify_simulators_cmd  # noqa: E402

cli.add_command(_verify_simulators_cmd)


if __name__ == "__main__":
    cli()
