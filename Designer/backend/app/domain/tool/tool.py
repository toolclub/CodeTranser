from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


class Engine(str, Enum):
    PURE_PYTHON = "pure_python"
    LLM = "llm"
    HYBRID = "hybrid"


class Scope(str, Enum):
    GLOBAL = "global"
    PRIVATE = "private"


@dataclass(frozen=True, slots=True)
class EdgeSemantic:
    field: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class CodeGenerationHints:
    style_hints: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()
    example_fragment: str = ""


@dataclass(frozen=True, slots=True)
class JsonSimulatorSpec:
    engine: Engine
    python_impl: str | None = None
    llm_fallback: bool = False


@dataclass(frozen=True, slots=True)
class NodeTemplate:
    id: str
    name: str
    display_name: str
    category: str
    scope: Scope
    version: int
    description: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    simulator: JsonSimulatorSpec
    edge_semantics: Sequence[EdgeSemantic]
    code_hints: CodeGenerationHints
    extensions: Mapping[str, Any]
    definition_hash: str
    owner_id: int | None = None

    def __post_init__(self) -> None:
        if self.scope is Scope.PRIVATE and self.simulator.engine is not Engine.LLM:
            raise ValueError(f"private node template {self.name} must use engine=llm")
