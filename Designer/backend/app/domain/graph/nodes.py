from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

from app.domain.tool.tool import NodeTemplate


class GraphNode(ABC):
    @abstractmethod
    def accept(self, v: "ForestVisitor") -> Any: ...  # noqa: F821


@dataclass(frozen=True, slots=True)
class NodeInstance(GraphNode):
    instance_id: str
    template_snapshot: NodeTemplate
    instance_name: str
    field_values: Mapping[str, Any]
    bundle_id: str | None = None

    def accept(self, v: "ForestVisitor") -> Any:  # noqa: F821
        return v.visit_node(self)


@dataclass(frozen=True, slots=True)
class Edge:
    edge_id: str
    src: str
    dst: str
    semantic: str

    def accept(self, v: "ForestVisitor") -> Any:  # noqa: F821
        return v.visit_edge(self)


@dataclass(frozen=True, slots=True)
class Bundle(GraphNode):
    bundle_id: str
    name: str
    description: str
    node_instance_ids: tuple[str, ...]

    def accept(self, v: "ForestVisitor") -> Any:  # noqa: F821
        return v.visit_bundle(self)


@dataclass(frozen=True, slots=True)
class CascadeForest(GraphNode):
    graph_version_id: str
    version_number: int
    bundles: tuple[Bundle, ...]
    node_instances: tuple[NodeInstance, ...]
    edges: tuple[Edge, ...]
    metadata: Mapping[str, Any]

    def node_by_id(self, iid: str) -> NodeInstance:
        for n in self.node_instances:
            if n.instance_id == iid:
                return n
        raise KeyError(iid)

    def bundle_by_id(self, bid: str) -> Bundle:
        for b in self.bundles:
            if b.bundle_id == bid:
                return b
        raise KeyError(bid)

    def orphans(self) -> list[NodeInstance]:
        return [n for n in self.node_instances if n.bundle_id is None]

    def accept(self, v: "ForestVisitor") -> Any:  # noqa: F821
        return v.visit_forest(self)
