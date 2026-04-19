import click
from sqlalchemy import select

from app.bootstrap import AppContainer
from app.infra.db.session import session_scope
from app.models.mysql.node_template import NodeTemplateRow
from app.models.mysql.node_template_version import NodeTemplateVersionRow
from app.tool_runtime.simulators import SIMULATOR_REGISTRY


async def run_verify(container: AppContainer) -> list[str]:
    errors: list[str] = []
    async with session_scope(container.session_factory) as s:
        rows = (
            await s.execute(
                select(NodeTemplateRow).where(
                    NodeTemplateRow.scope == "global",
                    NodeTemplateRow.deleted_at.is_(None),
                )
            )
        ).scalars().all()
        for r in rows:
            v = (
                await s.execute(
                    select(NodeTemplateVersionRow).where(
                        NodeTemplateVersionRow.id == r.current_version_id
                    )
                )
            ).scalar_one_or_none()
            if v is None:
                errors.append(f"{r.name}: current_version_id points to nothing")
                continue
            sim = v.definition.get("simulator", {})
            eng = sim.get("engine")
            impl = sim.get("python_impl")
            if eng == "pure_python":
                if impl != r.name:
                    errors.append(f"{r.name}: python_impl must equal template name")
                if r.name not in SIMULATOR_REGISTRY:
                    errors.append(f"{r.name}: simulator class not registered")
            elif eng == "hybrid":
                if impl and impl not in SIMULATOR_REGISTRY:
                    errors.append(f"{r.name}: hybrid primary {impl} not registered")
    return errors


@click.command("verify_simulators")
def main() -> None:
    import asyncio

    from app.cli.__main__ import _run

    async def _do(c: AppContainer) -> None:
        errs = await run_verify(c)
        if errs:
            for e in errs:
                click.echo(f"ERR {e}", err=True)
            raise SystemExit(1)
        click.echo("[verify] all simulators registered OK")

    asyncio.run(_run(_do))


if __name__ == "__main__":
    main()
