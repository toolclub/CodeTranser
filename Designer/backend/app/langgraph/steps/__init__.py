from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from app.langgraph.steps.base import BasePipelineStep

STEP_REGISTRY: dict[str, type[BasePipelineStep]] = {}


def _scan() -> None:
    from app.langgraph import steps as _pkg

    # 顶层模块(phase_end 等公用 step)
    for _, modname, ispkg in pkgutil.iter_modules(_pkg.__path__):
        if ispkg:
            continue
        if modname in {"base", "factory"}:
            continue
        mod = importlib.import_module(f"{_pkg.__name__}.{modname}")
        _harvest(mod)
    # 子包(phase1 / phase2 / phase3)
    for _, pkgname, ispkg in pkgutil.iter_modules(_pkg.__path__):
        if not ispkg:
            continue
        sub = importlib.import_module(f"{_pkg.__name__}.{pkgname}")
        for _, modname, _ in pkgutil.iter_modules(sub.__path__):
            mod = importlib.import_module(f"{sub.__name__}.{modname}")
            _harvest(mod)


def _harvest(mod: Any) -> None:  # type: ignore[name-defined]
    for attr in vars(mod).values():
        if (
            isinstance(attr, type)
            and issubclass(attr, BasePipelineStep)
            and attr is not BasePipelineStep
            and attr.name
        ):
            if attr.name in STEP_REGISTRY:
                raise RuntimeError(f"duplicate step {attr.name}")
            STEP_REGISTRY[attr.name] = attr


_scan()
