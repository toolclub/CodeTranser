from typing import Any, Literal

from pydantic import BaseModel, Field


class EdgeSemanticDTO(BaseModel):
    field: str
    description: str = ""


class CodeHintsDTO(BaseModel):
    style_hints: list[str] = []
    forbidden: list[str] = []
    example_fragment: str = ""


class JsonSimulatorDTO(BaseModel):
    engine: Literal["pure_python", "llm", "hybrid"]
    python_impl: str | None = None
    llm_fallback: bool = False


class NodeTemplateDefinitionDTO(BaseModel):
    """与 t_node_template_version.definition 一一对应。"""

    description: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    simulator: JsonSimulatorDTO
    edge_semantics: list[EdgeSemanticDTO] = []
    code_hints: CodeHintsDTO = CodeHintsDTO()
    extensions: dict[str, Any] = {}


class NodeTemplateCreateDTO(BaseModel):
    name: str = Field(..., pattern=r"^[A-Z][A-Za-z0-9_]{2,63}$")
    display_name: str = Field(..., max_length=256)
    category: str
    scope: Literal["global", "private"]
    definition: NodeTemplateDefinitionDTO
    change_note: str = ""


class NodeTemplateUpdateDTO(BaseModel):
    display_name: str | None = None
    category: str | None = None
    definition: NodeTemplateDefinitionDTO
    change_note: str = ""


class NodeTemplateOutDTO(BaseModel):
    """Admin / Tool 作者看到的完整节点模板。"""

    id: str
    name: str
    display_name: str
    category: str
    scope: Literal["global", "private"]
    status: Literal["draft", "active", "deprecated"]
    current_version: int
    definition: NodeTemplateDefinitionDTO
    created_at: str
    updated_at: str


class NodeTemplateCardDTO(BaseModel):
    """前端画布看到的投影(不含 description / python_impl / code_hints)。"""

    id: str
    name: str
    display_name: str
    category: str
    current_version: int
    input_schema: dict[str, Any]
    edge_semantics: list[EdgeSemanticDTO]
    extensions: dict[str, Any] = {}


class NodeTemplateSimulateReqDTO(BaseModel):
    field_values: dict[str, Any]
    input_json: dict[str, Any]
    tables: dict[str, list[Any]] = {}


class NodeTemplateSimulateRespDTO(BaseModel):
    output_json: dict[str, Any]
    engine_used: Literal["pure_python", "llm", "hybrid"]
    duration_ms: int
    llm_call_id: str | None = None
