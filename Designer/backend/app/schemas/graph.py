from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NodeInstanceDTO(BaseModel):
    instance_id: str
    template_id: str
    template_version: int
    template_snapshot: dict[str, Any] | None = None
    instance_name: str
    field_values: dict[str, Any]
    bundle_id: str | None = None


class EdgeDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    edge_id: str
    src: str = Field(..., alias="from")
    dst: str = Field(..., alias="to")
    semantic: str = Field(..., alias="edge_semantic")


class BundleDTO(BaseModel):
    bundle_id: str
    name: str
    description: str = ""
    node_instance_ids: list[str]


class ForestSnapshotDTO(BaseModel):
    bundles: list[BundleDTO] = []
    node_instances: list[NodeInstanceDTO]
    edges: list[EdgeDTO]
    metadata: dict[str, Any] = {}


class GraphCreateDTO(BaseModel):
    name: str
    description: str = ""


class GraphVersionSaveDTO(BaseModel):
    snapshot: ForestSnapshotDTO
    commit_message: str = ""
    parent_version_id: str | None = None
