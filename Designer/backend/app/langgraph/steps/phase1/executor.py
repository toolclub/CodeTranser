import json
from dataclasses import dataclass, field
from time import perf_counter_ns
from typing import Any, Awaitable, Callable

from app.domain.graph.nodes import CascadeForest, NodeInstance
from app.domain.run.sim import SimContext
from app.domain.tool.tool import Engine
from app.infra.metrics import TOOL_CALL_DUR, TOOL_CALLS
from app.langgraph.trace_sink import ToolCallTraceContext
from app.llm.types import ToolSpec, ToolUseRequest, ToolUseResult
from app.tool_runtime.errors import SimulatorInputInvalid, SimulatorOutputInvalid
from app.tool_runtime.registry import ToolRegistry


@dataclass(slots=True)
class NodeExecContext:
    forest: CascadeForest
    tables: dict[str, list[Any]]
    run_id: str
    tool_registry: ToolRegistry
    llm_client: Any
    tool_trace: ToolCallTraceContext
    node_outputs: dict[str, Any] = field(default_factory=dict)
    per_node_limit: int = 20
    per_node_counter: dict[str, int] = field(default_factory=dict)


def build_tool_specs(forest: CascadeForest) -> list[ToolSpec]:
    seen: dict[str, ToolSpec] = {}
    for n in forest.node_instances:
        t = n.template_snapshot
        if t.name in seen:
            continue
        input_schema: dict[str, Any] = {
            "type": "object",
            "required": ["instance_id", "input_json"],
            "properties": {
                "instance_id": {
                    "type": "string",
                    "description": f"森林里类型为 {t.name} 的某个节点实例 id",
                },
                "input_json": {"description": "传给该节点的输入 JSON"},
            },
            "additionalProperties": False,
        }
        seen[t.name] = ToolSpec(
            name=t.name,
            description=(
                f"调用一次类型为 {t.name} 的节点实例执行。{t.display_name}。"
                "详见 system 节点模板说明。"
            ),
            input_schema=input_schema,
        )
    return list(seen.values())


def find_node(forest: CascadeForest, instance_id: str) -> NodeInstance:
    for n in forest.node_instances:
        if n.instance_id == instance_id:
            return n
    raise KeyError(instance_id)


def make_executor(
    ctx: NodeExecContext,
) -> Callable[[ToolUseRequest], Awaitable[ToolUseResult]]:
    async def _exec(req: ToolUseRequest) -> ToolUseResult:
        t0 = perf_counter_ns()
        try:
            instance_id = req.input["instance_id"]
            input_json = req.input["input_json"]
        except Exception as e:
            return _err(req.id, f"bad tool input: {e}")

        try:
            node = find_node(ctx.forest, instance_id)
        except KeyError as e:
            return _err(req.id, f"instance not found: {e}")

        if node.template_snapshot.name != req.name:
            return _err(
                req.id,
                (
                    f"template mismatch: you called {req.name} but instance "
                    f"{instance_id} is {node.template_snapshot.name}"
                ),
            )

        n = ctx.per_node_counter.get(instance_id, 0) + 1
        ctx.per_node_counter[instance_id] = n
        if n > ctx.per_node_limit:
            return _err(
                req.id,
                f"instance {instance_id} called too many times (>{ctx.per_node_limit})",
            )

        sim = ctx.tool_registry.simulator_of(node.template_snapshot)
        sim_ctx = SimContext(
            run_id=ctx.run_id,
            instance_id=instance_id,
            table_data=dict(ctx.tables),
            llm=ctx.llm_client,
            trace=ctx.tool_trace,
        )
        try:
            r = sim.run(dict(node.field_values), dict(input_json), sim_ctx)
        except SimulatorInputInvalid as e:
            return _err(
                req.id,
                f"input invalid: {e}",
                engine=sim.engine.value,
                template=req.name,
            )
        except SimulatorOutputInvalid as e:
            return _err(
                req.id,
                f"output invalid: {e}",
                engine=sim.engine.value,
                template=req.name,
            )
        except Exception as e:
            return _err(
                req.id,
                f"simulator error: {e}",
                engine=sim.engine.value,
                template=req.name,
            )

        duration_ms = (perf_counter_ns() - t0) // 1_000_000

        ctx.tool_trace.record(
            {
                "template_name": req.name,
                "template_version": node.template_snapshot.version,
                "definition_hash": node.template_snapshot.definition_hash,
                "engine": r.engine_used.value,
                "instance_id": instance_id,
                "bundle_id": node.bundle_id,
                "field_values": dict(node.field_values),
                "input_json": input_json,
                "output_json": r.output,
                "duration_ms": int(duration_ms),
                "error": r.error,
                "llm_fallback_used": (
                    r.engine_used is Engine.LLM
                    and node.template_snapshot.simulator.engine is Engine.HYBRID
                ),
                "llm_call_ref": r.llm_call_ref,
            }
        )
        TOOL_CALLS.labels(
            tool_name=req.name,
            engine=r.engine_used.value,
            verdict="ok" if r.error is None else "error",
        ).inc()
        TOOL_CALL_DUR.labels(tool_name=req.name, engine=r.engine_used.value).observe(
            duration_ms / 1000
        )

        ctx.node_outputs[instance_id] = r.output

        payload = {
            "output_json": r.output,
            "outgoing_edges": _outgoing_edges(ctx.forest, instance_id),
        }
        return ToolUseResult(
            tool_use_id=req.id,
            content=json.dumps(payload, ensure_ascii=False),
            is_error=False,
        )

    return _exec


def _err(tool_use_id: str, msg: str, **meta: Any) -> ToolUseResult:
    return ToolUseResult(
        tool_use_id=tool_use_id,
        content=json.dumps({"error": msg, **meta}, ensure_ascii=False),
        is_error=True,
    )


def _outgoing_edges(forest: CascadeForest, instance_id: str) -> list[dict[str, Any]]:
    ids = {n.instance_id: n for n in forest.node_instances}
    return [
        {
            "semantic": e.semantic,
            "dst": e.dst,
            "dst_template": ids[e.dst].template_snapshot.name if e.dst in ids else None,
            "dst_bundle": ids[e.dst].bundle_id if e.dst in ids else None,
        }
        for e in forest.edges
        if e.src == instance_id
    ]
