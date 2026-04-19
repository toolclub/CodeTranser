import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.llm.types import LLMRequest, LLMResponse, LLMUsage, ToolUseRequest


@dataclass
class MockStep:
    match: dict[str, Any]
    text: str = ""
    tool_uses: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: LLMUsage = field(default_factory=LLMUsage)
    raise_exception: Exception | None = None


class MockProvider:
    """按顺序脚本回放。匹配到的 step 被 pop。"""

    name = "mock"

    def __init__(self, steps: list[MockStep]) -> None:
        self._steps = list(steps)
        self.call_log: list[LLMRequest] = []

    async def call(self, req: LLMRequest) -> LLMResponse:
        self.call_log.append(req)
        for i, s in enumerate(self._steps):
            if self._match(req, s.match):
                self._steps.pop(i)
                if s.raise_exception is not None:
                    raise s.raise_exception
                return self._make_response(req, s)
        raise AssertionError(
            f"no mock step matched. user={(req.user or '')[:100]!r}"
        )

    def _match(self, req: LLMRequest, m: dict[str, Any]) -> bool:
        if "any" in m:
            return True
        if "user_contains" in m:
            if m["user_contains"] not in (req.user or ""):
                return False
        if "system_contains" in m:
            if m["system_contains"] not in req.system:
                return False
        if "user_regex" in m:
            if not re.search(m["user_regex"], req.user or ""):
                return False
        return True

    def _make_response(self, req: LLMRequest, s: MockStep) -> LLMResponse:
        return LLMResponse(
            call_id=f"mock_{uuid.uuid4().hex[:8]}",
            model=req.model or "mock",
            text=s.text,
            tool_uses=tuple(
                ToolUseRequest(
                    id=f"tu_{uuid.uuid4().hex[:6]}",
                    name=t["name"],
                    input=t.get("input", {}),
                )
                for t in s.tool_uses
            ),
            stop_reason=s.stop_reason,  # type: ignore[arg-type]
            usage=s.usage,
            raw={"mock": True},
            duration_ms=0,
        )
