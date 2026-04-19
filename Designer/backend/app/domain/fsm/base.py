"""极简 FSM 基类(不依赖第三方 statemachine 包)。

用法:
    class MySM(FSM[MyStatus]):
        TRANSITIONS = {
            (MyStatus.A, "go"): MyStatus.B,
            (MyStatus.B, "finish"): MyStatus.C,
        }

    sm = MySM.from_status("A")
    sm.fire("go")       # A → B
    sm.current          # MyStatus.B

任何非法 `(current, event)` 抛 `IllegalTransition`。
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Generic, TypeVar

from app.domain.errors import BusinessError

_S = TypeVar("_S", bound=Enum)


class IllegalTransition(BusinessError):
    code = "FSM_ILLEGAL_TRANSITION"


class FSM(Generic[_S]):
    """FSM 基类。

    子类必须:
      - 指定状态 Enum 类 `STATUS_ENUM`
      - 填 `TRANSITIONS` 字典(`(from_state, event) -> to_state`)
    """

    STATUS_ENUM: ClassVar[type[Enum]]
    TRANSITIONS: ClassVar[dict[tuple[Enum, str], Enum]]

    def __init__(self, status: _S, *, entity_id: str = "") -> None:
        self._current: _S = status
        self.entity_id = entity_id

    @property
    def current(self) -> _S:
        return self._current

    @property
    def current_value(self) -> str:
        v = self._current.value
        return str(v)

    @classmethod
    def from_status(cls, status: _S | str, *, entity_id: str = "") -> "FSM[_S]":
        if isinstance(status, str):
            status = cls.STATUS_ENUM(status)  # type: ignore[arg-type]
        return cls(status, entity_id=entity_id)  # type: ignore[arg-type]

    def can_fire(self, event: str) -> bool:
        return (self._current, event) in self.TRANSITIONS

    def fire(self, event: str) -> _S:
        key = (self._current, event)
        nxt = self.TRANSITIONS.get(key)
        if nxt is None:
            raise IllegalTransition(
                f"{type(self).__name__}: cannot fire {event!r} from {self._current.name}",
                entity_id=self.entity_id,
                from_state=self._current.name,
                event=event,
            )
        self._current = nxt  # type: ignore[assignment]
        return self._current

    def transition_to(self, target: _S | str) -> _S:
        """根据目标状态自动选择 event(便捷方法)。要求目标在可达集合内且只有 1 条路径。"""
        if isinstance(target, str):
            target = self.STATUS_ENUM(target)  # type: ignore[arg-type]
        candidates = [
            ev for (frm, ev), to in self.TRANSITIONS.items()
            if frm == self._current and to == target
        ]
        if len(candidates) != 1:
            raise IllegalTransition(
                f"ambiguous or no path from {self._current.name} to {target.name}: {candidates}",
                entity_id=self.entity_id,
            )
        return self.fire(candidates[0])
