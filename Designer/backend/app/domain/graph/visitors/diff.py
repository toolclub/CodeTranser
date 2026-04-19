from dataclasses import dataclass, field
from typing import Any

from app.domain.graph.nodes import CascadeForest


@dataclass
class ForestDiff:
    added_bundles: list[str] = field(default_factory=list)
    removed_bundles: list[str] = field(default_factory=list)
    added_nodes: list[str] = field(default_factory=list)
    removed_nodes: list[str] = field(default_factory=list)
    changed_nodes: list[dict[str, Any]] = field(default_factory=list)
    added_edges: list[str] = field(default_factory=list)
    removed_edges: list[str] = field(default_factory=list)
    bundle_membership_changes: list[dict[str, Any]] = field(default_factory=list)


def diff(a: CascadeForest, b: CascadeForest) -> ForestDiff:
    out = ForestDiff()
    ab = {x.bundle_id for x in a.bundles}
    bb = {x.bundle_id for x in b.bundles}
    out.added_bundles = sorted(bb - ab)
    out.removed_bundles = sorted(ab - bb)

    an = {n.instance_id: n for n in a.node_instances}
    bn = {n.instance_id: n for n in b.node_instances}
    out.added_nodes = sorted(bn.keys() - an.keys())
    out.removed_nodes = sorted(an.keys() - bn.keys())

    for iid in an.keys() & bn.keys():
        delta: dict[str, Any] = {}
        a_node, b_node = an[iid], bn[iid]
        if a_node.template_snapshot.name != b_node.template_snapshot.name:
            delta["template_name"] = (
                a_node.template_snapshot.name,
                b_node.template_snapshot.name,
            )
        if a_node.template_snapshot.version != b_node.template_snapshot.version:
            delta["template_version"] = (
                a_node.template_snapshot.version,
                b_node.template_snapshot.version,
            )
        if dict(a_node.field_values) != dict(b_node.field_values):
            delta["field_values"] = (
                dict(a_node.field_values),
                dict(b_node.field_values),
            )
        if a_node.bundle_id != b_node.bundle_id:
            out.bundle_membership_changes.append(
                {"iid": iid, "from": a_node.bundle_id, "to": b_node.bundle_id}
            )
        if delta:
            out.changed_nodes.append({"iid": iid, "delta": delta})

    ae = {e.edge_id for e in a.edges}
    be = {e.edge_id for e in b.edges}
    out.added_edges = sorted(be - ae)
    out.removed_edges = sorted(ae - be)
    return out
