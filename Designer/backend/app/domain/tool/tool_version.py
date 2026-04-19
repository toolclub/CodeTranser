from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class NodeTemplateVersion:
    """t_node_template_version 一行的值对象;03 章会用。"""

    id: str
    template_id: str
    version_number: int
    definition: Mapping[str, Any]
    definition_hash: str
    change_note: str
    created_by: int
    created_at: datetime
