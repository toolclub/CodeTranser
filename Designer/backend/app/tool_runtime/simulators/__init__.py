"""节点模板模拟器自动注册表。

导入本模块即扫描 `pure_python/` 下所有文件,把每个 `ToolSimulator` 子类(tool_name 非空)
放进 SIMULATOR_REGISTRY,key = tool_name = 节点模板名。
"""

from __future__ import annotations

import importlib
import pkgutil

from app.tool_runtime.base import ToolSimulator

SIMULATOR_REGISTRY: dict[str, type[ToolSimulator]] = {}


def _scan() -> None:
    from . import pure_python

    for _, name, _ in pkgutil.iter_modules(pure_python.__path__):
        mod = importlib.import_module(f"{pure_python.__name__}.{name}")
        for attr in vars(mod).values():
            if (
                isinstance(attr, type)
                and issubclass(attr, ToolSimulator)
                and attr is not ToolSimulator
                and attr.tool_name
            ):
                if attr.tool_name in SIMULATOR_REGISTRY:
                    raise RuntimeError(f"duplicate simulator for {attr.tool_name}")
                SIMULATOR_REGISTRY[attr.tool_name] = attr


def register(cls: type[ToolSimulator]) -> type[ToolSimulator]:
    """手动注册入口(测试 monkeypatch 用)。"""
    if not cls.tool_name:
        raise ValueError("tool_name required")
    SIMULATOR_REGISTRY[cls.tool_name] = cls
    return cls


def clear_registry() -> None:
    """仅测试使用。"""
    SIMULATOR_REGISTRY.clear()


_scan()
