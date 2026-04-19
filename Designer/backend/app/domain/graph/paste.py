"""粘贴工具:重发 ID + 更新内部引用。

前端 ctrl+v 使用;后端在"跨图粘贴"场景也会用。"""

import uuid
from typing import Any


def rebuild_ids(pasted: dict[str, Any]) -> dict[str, Any]:
    """对一个包含 {bundles, node_instances, edges} 的片段,全量换新 ID。

    - instance_id / bundle_id / edge_id 全部换新
    - 内部 bundle.node_instance_ids / edge.from / edge.to 跟着改
    - 保留 template_id / template_version / template_snapshot 原样
    """
    id_map: dict[str, str] = {}

    def _new(old: str) -> str:
        if old in id_map:
            return id_map[old]
        prefix = old.split("_", 1)[0] if "_" in old else "x"
        new = f"{prefix}_{uuid.uuid4().hex[:8]}"
        id_map[old] = new
        return new

    for n in pasted.get("node_instances", []):
        n["instance_id"] = _new(n["instance_id"])

    for b in pasted.get("bundles", []):
        b["bundle_id"] = _new(b["bundle_id"])
        b["node_instance_ids"] = [
            id_map.get(x, x) for x in b.get("node_instance_ids", [])
        ]

    for e in pasted.get("edges", []):
        e["edge_id"] = _new(e["edge_id"])
        src = e.get("from") or e.get("src")
        dst = e.get("to") or e.get("dst")
        if src is not None:
            new_src = id_map.get(src, src)
            if "from" in e:
                e["from"] = new_src
            if "src" in e:
                e["src"] = new_src
        if dst is not None:
            new_dst = id_map.get(dst, dst)
            if "to" in e:
                e["to"] = new_dst
            if "dst" in e:
                e["dst"] = new_dst

    return pasted
