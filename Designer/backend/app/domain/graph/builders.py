from typing import Any, Mapping, Protocol

from app.domain.graph.errors import BundleMembershipConflict, GraphParseError
from app.domain.graph.nodes import Bundle, CascadeForest, Edge, NodeInstance
from app.domain.tool.tool import (
    CodeGenerationHints,
    EdgeSemantic,
    Engine,
    JsonSimulatorSpec,
    NodeTemplate,
    Scope,
)


class TemplateResolver(Protocol):
    """从 `template_id + version` 解析出 `NodeTemplate` 值对象。

    v1 仅实现 FrozenResolver:从 snapshot 里已冻结的 template_snapshot 还原。
    保存前由 ForestParser.freeze_snapshot(async)先把 template_snapshot 填好,
    随后用 build_forest + FrozenResolver(sync)构造值对象。
    """

    def resolve(
        self,
        *,
        template_id: str,
        version: int | None,
        hint_snapshot: Mapping[str, Any] | None = None,
    ) -> NodeTemplate: ...


class FrozenResolver:
    """读取路径专用。严格要求 `hint_snapshot` 非空,否则抛。"""

    def resolve(
        self,
        *,
        template_id: str,
        version: int | None,
        hint_snapshot: Mapping[str, Any] | None = None,
    ) -> NodeTemplate:
        if not hint_snapshot:
            raise GraphParseError(f"template_snapshot missing for {template_id}")
        return snapshot_dict_to_template(hint_snapshot)


def snapshot_dict_to_template(snap: Mapping[str, Any]) -> NodeTemplate:
    raw_desc = snap.get("description", "")
    desc = "\n".join(raw_desc) if isinstance(raw_desc, list) else str(raw_desc)
    sim_raw = snap.get("simulator") or {}
    code_hints_raw = snap.get("code_hints") or {}
    return NodeTemplate(
        id=snap["id"],
        name=snap["name"],
        display_name=snap["display_name"],
        category=snap["category"],
        scope=Scope(snap["scope"]),
        version=int(snap["version"]),
        description=desc,
        input_schema=snap.get("input_schema", {}),
        output_schema=snap.get("output_schema", {}),
        simulator=JsonSimulatorSpec(
            engine=Engine(sim_raw.get("engine", "llm")),
            python_impl=sim_raw.get("python_impl"),
            llm_fallback=bool(sim_raw.get("llm_fallback", False)),
        ),
        edge_semantics=tuple(
            EdgeSemantic(e["field"], e.get("description", ""))
            for e in snap.get("edge_semantics", []) or []
        ),
        code_hints=CodeGenerationHints(
            style_hints=tuple(code_hints_raw.get("style_hints", [])),
            forbidden=tuple(code_hints_raw.get("forbidden", [])),
            example_fragment=code_hints_raw.get("example_fragment", ""),
        ),
        extensions=snap.get("extensions", {}),
        definition_hash=snap.get("definition_hash", ""),
        owner_id=snap.get("owner_id"),
    )


def template_to_snapshot_dict(t: NodeTemplate) -> dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "display_name": t.display_name,
        "category": t.category,
        "scope": t.scope.value,
        "version": t.version,
        "description": t.description.split("\n") if t.description else [],
        "input_schema": dict(t.input_schema),
        "output_schema": dict(t.output_schema),
        "simulator": {
            "engine": t.simulator.engine.value,
            "python_impl": t.simulator.python_impl,
            "llm_fallback": t.simulator.llm_fallback,
        },
        "edge_semantics": [
            {"field": e.field, "description": e.description} for e in t.edge_semantics
        ],
        "code_hints": {
            "style_hints": list(t.code_hints.style_hints),
            "forbidden": list(t.code_hints.forbidden),
            "example_fragment": t.code_hints.example_fragment,
        },
        "extensions": dict(t.extensions),
        "definition_hash": t.definition_hash,
        "owner_id": t.owner_id,
    }


def build_forest(
    *,
    graph_version_id: str,
    version_number: int,
    snapshot: dict[str, Any],
    resolver: TemplateResolver,
) -> CascadeForest:
    try:
        bundles_src = snapshot.get("bundles", [])
        nodes_src = snapshot["node_instances"]
        edges_src = snapshot["edges"]
    except KeyError as e:
        raise GraphParseError(f"missing key: {e}") from e

    iid_to_bid: dict[str, str] = {}
    for b in bundles_src:
        for iid in b.get("node_instance_ids", []):
            if iid in iid_to_bid:
                raise BundleMembershipConflict(
                    f"instance {iid} belongs to multiple bundles",
                    instance_id=iid,
                    bundles=[iid_to_bid[iid], b["bundle_id"]],
                )
            iid_to_bid[iid] = b["bundle_id"]

    nodes = tuple(_build_node(n, iid_to_bid, resolver) for n in nodes_src)
    edges = tuple(_build_edge(e) for e in edges_src)
    bundles = tuple(_build_bundle(b) for b in bundles_src)

    return CascadeForest(
        graph_version_id=graph_version_id,
        version_number=version_number,
        bundles=bundles,
        node_instances=nodes,
        edges=edges,
        metadata=snapshot.get("metadata", {}),
    )


def _build_node(
    n: dict[str, Any],
    iid_to_bid: dict[str, str],
    resolver: TemplateResolver,
) -> NodeInstance:
    tpl = resolver.resolve(
        template_id=n["template_id"],
        version=n.get("template_version"),
        hint_snapshot=n.get("template_snapshot"),
    )
    return NodeInstance(
        instance_id=n["instance_id"],
        template_snapshot=tpl,
        instance_name=n.get("instance_name", n["instance_id"]),
        field_values=dict(n.get("field_values", {})),
        bundle_id=iid_to_bid.get(n["instance_id"]),
    )


def _build_edge(e: dict[str, Any]) -> Edge:
    src = e.get("from") or e.get("src")
    dst = e.get("to") or e.get("dst")
    semantic = e.get("edge_semantic") or e.get("semantic")
    if not src or not dst or not semantic:
        raise GraphParseError(f"bad edge: {e}")
    return Edge(edge_id=e["edge_id"], src=src, dst=dst, semantic=semantic)


def _build_bundle(b: dict[str, Any]) -> Bundle:
    return Bundle(
        bundle_id=b["bundle_id"],
        name=b.get("name", b["bundle_id"]),
        description=b.get("description", ""),
        node_instance_ids=tuple(b.get("node_instance_ids", [])),
    )
