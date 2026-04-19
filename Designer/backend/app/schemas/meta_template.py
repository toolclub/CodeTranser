from typing import Literal

from pydantic import BaseModel


class MetaTemplateFieldDTO(BaseModel):
    key: str
    label: str
    type: Literal[
        "string",
        "string_array",
        "json_schema",
        "code_block",
        "edge_list",
        "json",
        "bool",
        "number",
    ]
    required: bool = False
    hint: str | None = None
    pattern: str | None = None
    max_length: int | None = None


class MetaTemplateDTO(BaseModel):
    version: int
    fields: list[MetaTemplateFieldDTO]


class MetaTemplateUpdateDTO(BaseModel):
    content: MetaTemplateDTO
    note: str = ""
