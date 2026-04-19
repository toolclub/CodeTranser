"""Run 事件流 — 对齐 ChatFlow `fsm/sse_events.py` 的优先级注册表 + DB 持久化协议。

设计(ChatFlow 铁律转译):
  1. **所有事件类型在 EventType 枚举里注册**,禁止散落字符串
  2. **多 key 共存时按优先级匹配**(控制事件 > 工具调用 > 内容)
  3. **事件先入 DB(`t_run_event_log`),再广播 Redis pub/sub** — Redis 挂了前端
     仍可用 `GET /api/runs/{id}/events?after_id=N` 从 DB resume
  4. Redis 操作全部包 `asyncio.wait_for(timeout=...)`,慢 Redis 不阻塞心跳
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from app.infra.logging import get_logger
from app.utils.clock import utcnow

log = get_logger(__name__)

_REDIS_OP_TIMEOUT = 2.0  # 秒;ChatFlow 心跳 wait_for 同等


class EventType(str, Enum):
    """Run 事件类型。继承 `(str, Enum)` 使 JSON 序列化与 DB 存储无转换成本。"""

    # ── 生命周期控制(最高优先级) ──
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    PHASE_STARTED = "phase_started"
    PHASE_FINISHED = "phase_finished"

    # ── 步骤 ──
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"

    # ── Phase1 责任链 ──
    HANDLER_STARTED = "handler_started"
    HANDLER_COMPLETED = "handler_completed"

    # ── 工具与 LLM ──
    TOOL_CALLED = "tool_called"
    LLM_CALLED = "llm_called"

    # ── 结构化思考(ChatFlow thinking 协议派生,供流式 LLM 用) ──
    THINKING = "thinking"
    CONTENT = "content"

    # ── 异常/预算 ──
    ITERATION_HIT = "iteration_hit"

    # ── 心跳/未知 ──
    PING = "ping"
    UNKNOWN = "unknown"


# 控制 > 步骤 > handler > 工具/LLM > thinking/content > ping
_PRIORITY_ORDER: list[EventType] = [
    EventType.RUN_FINISHED,
    EventType.RUN_STARTED,
    EventType.PHASE_FINISHED,
    EventType.PHASE_STARTED,
    EventType.STEP_COMPLETED,
    EventType.STEP_STARTED,
    EventType.HANDLER_COMPLETED,
    EventType.HANDLER_STARTED,
    EventType.TOOL_CALLED,
    EventType.LLM_CALLED,
    EventType.ITERATION_HIT,
    EventType.THINKING,
    EventType.CONTENT,
    EventType.PING,
]


def detect_event_type(payload: dict[str, Any]) -> EventType:
    """从任意 payload 里按优先级侦测事件类型。多 key 共存时严格按序。"""
    if "type" in payload:
        try:
            return EventType(payload["type"])
        except ValueError:
            return EventType.UNKNOWN
    for t in _PRIORITY_ORDER:
        if t.value in payload:
            return t
    return EventType.UNKNOWN


@dataclass(frozen=True, slots=True)
class RunEvent:
    """一条运行事件。"""

    type: EventType
    run_id: str
    ts: str  # ISO-8601
    phase: int | None = None
    step_id: str | None = None
    node_name: str | None = None
    handler_name: str | None = None
    payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value if isinstance(self.type, EventType) else str(self.type)
        return d


def channel_of(run_id: str) -> str:
    return f"run:{run_id}:events"


class RunEventBus:
    """事件总线:DB-first(source of truth)+ Redis pub/sub(实时广播)。

    - 先 `await event_store.append(...)` → 获得自增 event_id
    - 再 Redis publish 带上 `event_id`,前端实时收到时可用来去重 + resume 基准
    - Redis 不可用(`redis=None`、超时、异常)时降级:只落 DB,事件不丢
    """

    def __init__(
        self,
        redis: Any | None = None,
        *,
        event_store: Any | None = None,
    ) -> None:
        self._r = redis
        self._store = event_store

    async def emit(self, event: RunEvent) -> int | None:
        event_id: int | None = None
        if self._store is not None:
            try:
                event_id = await self._store.append(
                    run_id=event.run_id,
                    event_type=event.type.value,
                    event_data=event.to_dict(),
                )
            except Exception as e:
                log.warning("event_log_append_failed", error=str(e), run=event.run_id)
        if self._r is not None:
            msg: dict[str, Any] = {"id": event_id, **event.to_dict()}
            try:
                await asyncio.wait_for(
                    self._r.publish(channel_of(event.run_id), json.dumps(msg, ensure_ascii=False)),
                    timeout=_REDIS_OP_TIMEOUT,
                )
            except asyncio.TimeoutError:
                log.warning("event_publish_timeout", run=event.run_id, type=event.type.value)
            except Exception as e:
                log.warning("event_publish_failed", run=event.run_id, error=str(e))
        else:
            # 既无 Redis 又无 event_store:记 debug 便于排查
            if self._store is None:
                log.debug(
                    "run_event",
                    **{k: v for k, v in event.to_dict().items() if v is not None},
                )
        return event_id

    async def emit_simple(self, etype: EventType, run_id: str, **kw: Any) -> int | None:
        return await self.emit(
            RunEvent(type=etype, run_id=run_id, ts=utcnow().isoformat(), **kw)
        )
