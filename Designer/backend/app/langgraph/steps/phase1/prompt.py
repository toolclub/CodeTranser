import json
from dataclasses import dataclass
from typing import Any

from app.domain.graph.nodes import CascadeForest

_SYSTEM_HEADER = """\
你是"级跳设计平台"的森林执行引擎。给你一张森林:含若干 Bundle(大节点,代码层对应 class/function)\
+ 若干游离节点实例(孤儿小节点,代码层对应独立代码片段)+ 全局边(可跨 Bundle)。
你的任务:

1. 从森林里找一个入口(入度 0 的节点实例)开始,通过 tool_use 依次让每个节点实例执行。
2. 每次 tool_use 只调一个节点实例。工具参数 = (instance_id, input_json);节点实例的 field_values 会由执行器自动从森林里取出。
3. 每次调用返回该节点的 output_json + 当前节点的 outgoing_edges(可走哪些 semantic 到哪个下游 instance_id)。
4. 根据 output_json 决定走哪条 outgoing_edge,然后调下游节点。
5. 跨 Bundle 的调用和同 Bundle 内一样;Bundle 只是组织分组,不影响执行。
6. 整图走完后,用一条普通文本消息返回**一段合法 JSON** 描述对外的最终输出。

规则:
- 不要伪造节点输出:必须通过 tool_use 拿真实输出
- 工具调用 is_error=true → 停止执行,在最终 JSON 里用 "__error__" 字段说明失败节点
- 顶多 {MAX_ITERATIONS} 次 tool_use
- 最终消息**只发一段合法 JSON**,不要任何前后解释文字
"""


@dataclass(frozen=True, slots=True)
class PromptBundle:
    system: str
    initial_user: str


def build_prompt_bundle(
    forest: CascadeForest,
    *,
    scenario_input: Any,
    scenario_description: str = "",
    max_iterations: int = 20,
) -> PromptBundle:
    parts: list[str] = [
        _SYSTEM_HEADER.format(MAX_ITERATIONS=max_iterations),
        "",
        "# 森林结构",
        "",
        "## Bundles(大节点)",
    ]
    if not forest.bundles:
        parts.append("(无)")
    for b in forest.bundles:
        parts.append(
            f"- {b.bundle_id}  name={b.name}  members={list(b.node_instance_ids)}"
        )

    orphans = [n for n in forest.node_instances if n.bundle_id is None]
    parts += ["", "## 游离节点实例(孤儿,不属于任何 Bundle)"]
    if not orphans:
        parts.append("(无)")
    else:
        for n in orphans:
            parts.append(
                f"- {n.instance_id}  template={n.template_snapshot.name}  name={n.instance_name}"
            )

    parts += ["", "## 节点实例(全部)"]
    for n in forest.node_instances:
        bid = n.bundle_id or "(orphan)"
        parts.append(
            f"- {n.instance_id}  template={n.template_snapshot.name}  bundle={bid}  "
            f"name={n.instance_name}  fields={json.dumps(dict(n.field_values), ensure_ascii=False)}"
        )

    parts += ["", "## 边(全局,可跨 Bundle)"]
    for e in forest.edges:
        parts.append(f"- {e.src} --[{e.semantic}]--> {e.dst}")

    parts += ["", "## 节点模板说明"]
    parts += _render_template_descs(forest)

    system = "\n".join(parts)
    user = _render_initial_user(scenario_input, scenario_description)
    return PromptBundle(system=system, initial_user=user)


def _render_template_descs(forest: CascadeForest) -> list[str]:
    seen: dict[str, str] = {}
    for n in forest.node_instances:
        t = n.template_snapshot
        if t.name in seen:
            continue
        out_edges = ", ".join(es.field for es in t.edge_semantics) or "(无出边)"
        seen[t.name] = (
            f"### {t.name}  ({t.display_name})\n"
            f"类别: {t.category};出边语义: {out_edges}\n"
            f"描述:\n{t.description}\n"
            f"output_schema: {json.dumps(dict(t.output_schema), ensure_ascii=False)}\n"
        )
    return list(seen.values())


def _render_initial_user(scenario_input: Any, description: str) -> str:
    note = f"\n场景说明: {description}" if description else ""
    return (
        f"场景输入 JSON(整森林入口):\n"
        f"```json\n{json.dumps(scenario_input, ensure_ascii=False, indent=2)}\n```\n"
        f"请开始执行,直到产出最终输出。{note}"
    )
