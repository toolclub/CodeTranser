"""LangGraph checkpointer 工厂。

分布式铁律:
  - `memory`:进程内,**仅 dev** 使用,pod 重启即丢 state
  - `redis`:推荐生产,所有 pod 共享,任一 pod 挂了其他 pod 能接手 resume
  - `none`:不做 checkpoint(等同 memory,但显式;ainvoke 不需要 thread_id 配置)

调用方:
    saver = build_checkpointer(settings)      # 返回 BaseCheckpointSaver | None
    graph = state_graph.compile(checkpointer=saver)
    await graph.ainvoke(state, config={"configurable": {"thread_id": run_id}})

分布式要点:
  - `thread_id = run_id` 是跨 pod 协调的关键,任何 pod 拿同一个 run_id 都能续上
  - Redis checkpoint 要求同一 Redis 集群(prod 必备)
  - 开发期可降级为 `memory` 便于调试,但 prod 必须切到 `redis`
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.infra.logging import get_logger

log = get_logger(__name__)


def build_checkpointer(settings: Settings) -> Any | None:
    kind = getattr(settings, "CHECKPOINTER_KIND", "memory")
    if kind == "none":
        return None
    if kind == "memory":
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except ImportError as e:
            log.warning("langgraph_memory_checkpoint_unavailable", error=str(e))
            return None
        if settings.APP_ENV == "prod":
            log.warning(
                "memory_checkpointer_in_prod",
                message=(
                    "MemorySaver 是进程内存储,pod 重启或被调度到其他节点后 state 丢失。"
                    "K8S 多副本部署请切 CHECKPOINTER_KIND=redis"
                ),
            )
        return MemorySaver()
    if kind == "redis":
        try:
            # langgraph-checkpoint-redis 为可选依赖
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver  # type: ignore[import-untyped]
        except ImportError:
            log.error(
                "redis_checkpointer_missing_dep",
                message="pip install langgraph-checkpoint-redis 才能启用",
            )
            return None
        return AsyncRedisSaver.from_conn_string(settings.REDIS_URL)
    if kind == "postgres":
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # type: ignore[import-untyped]
        except ImportError:
            log.error(
                "postgres_checkpointer_missing_dep",
                message="pip install langgraph-checkpoint-postgres 才能启用",
            )
            return None
        pg_url = getattr(settings, "CHECKPOINTER_PG_URL", "") or settings.DATABASE_URL
        return AsyncPostgresSaver.from_conn_string(pg_url)
    raise ValueError(f"unknown CHECKPOINTER_KIND: {kind!r}")
