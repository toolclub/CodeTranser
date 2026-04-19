"""测试用森林 fixture 构造工具。"""

from __future__ import annotations

from typing import Iterable

from app.domain.graph.nodes import Bundle, CascadeForest, Edge, NodeInstance
from app.domain.tool.tool import (
    CodeGenerationHints,
    EdgeSemantic,
    Engine,
    JsonSimulatorSpec,
    NodeTemplate,
    Scope,
)


def make_tpl(
    name: str = "T",
    *,
    edges: Iterable[str] = ("next",),
    input_schema: dict | None = None,
) -> NodeTemplate:
    return NodeTemplate(
        id=f"tpl_{name}",
        name=name,
        display_name=name,
        category="c",
        scope=Scope.GLOBAL,
        version=1,
        description="",
        input_schema=input_schema or {},
        output_schema={},
        simulator=JsonSimulatorSpec(engine=Engine.PURE_PYTHON, python_impl=name),
        edge_semantics=tuple(EdgeSemantic(f) for f in edges),
        code_hints=CodeGenerationHints(),
        extensions={},
        definition_hash="h",
    )


def make_inst(
    iid: str,
    bundle: str | None = None,
    tpl: NodeTemplate | None = None,
    field_values: dict | None = None,
) -> NodeInstance:
    return NodeInstance(
        instance_id=iid,
        template_snapshot=tpl or make_tpl(),
        instance_name=iid,
        field_values=field_values or {},
        bundle_id=bundle,
    )


def make_edge(eid: str, src: str, dst: str, semantic: str = "next") -> Edge:
    return Edge(edge_id=eid, src=src, dst=dst, semantic=semantic)


def make_bundle(bid: str, iids: list[str], name: str = "B") -> Bundle:
    return Bundle(bundle_id=bid, name=name, description="", node_instance_ids=tuple(iids))


def make_forest(
    *,
    bundles: list[Bundle] | None = None,
    instances: list[NodeInstance],
    edges: list[Edge] | None = None,
) -> CascadeForest:
    return CascadeForest(
        graph_version_id="gv_test",
        version_number=1,
        bundles=tuple(bundles or []),
        node_instances=tuple(instances),
        edges=tuple(edges or []),
        metadata={},
    )
