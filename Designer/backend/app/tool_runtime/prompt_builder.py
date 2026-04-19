import json
from dataclasses import dataclass
from typing import Any

from jinja2 import BaseLoader, Environment, StrictUndefined

from app.domain.tool.tool import NodeTemplate


@dataclass(frozen=True, slots=True)
class PromptPair:
    system: str
    user: str


class PromptBuilder:
    """构造 LLM 输入。

    - NodeTemplate.description(已 join 的单串,含 Jinja)→ system
    - fields + input_json 合并 JSON → user
    """

    _env: Environment = Environment(
        loader=BaseLoader(),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )

    def __init__(self, tpl: NodeTemplate) -> None:
        self._tpl = tpl
        self._ctx: dict[str, Any] = {"fields": {}, "input": None, "examples": None}

    def with_fields(self, fv: dict[str, Any]) -> "PromptBuilder":
        self._ctx["fields"] = dict(fv)
        return self

    def with_input(self, inp: dict[str, Any]) -> "PromptBuilder":
        self._ctx["input"] = inp
        return self

    def with_examples(self, exs: list[Any]) -> "PromptBuilder":
        self._ctx["examples"] = exs
        return self

    def build(self) -> PromptPair:
        tmpl = self._env.from_string(self._tpl.description)
        system = tmpl.render(**self._ctx)
        user = json.dumps(
            {"fields": self._ctx["fields"], "input": self._ctx["input"]},
            ensure_ascii=False,
        )
        return PromptPair(system=system, user=user)
