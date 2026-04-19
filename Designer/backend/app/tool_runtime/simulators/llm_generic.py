from time import perf_counter_ns
from typing import Any

from app.domain.run.sim import SimContext, SimResult
from app.domain.tool.tool import Engine, NodeTemplate
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.errors import ToolLLMFailed
from app.tool_runtime.json_schema import validate_output
from app.tool_runtime.prompt_builder import PromptBuilder


class LLMSimulator(ToolSimulator):
    """engine=llm 时所有节点模板共用。
    - description 渲染为 system prompt
    - fields + input_json 合并为 user payload
    - 要求 LLM 返回满足 `output_schema` 的 JSON
    """

    engine = Engine.LLM

    def __init__(self, tpl: NodeTemplate) -> None:
        self._tpl = tpl
        # 注意:tool_name 是 ClassVar,但每个 LLMSimulator 实例绑定一个模板,
        # 这里用实例属性覆盖,仅影响 trace/metrics 的 label。
        self.tool_name = tpl.name  # type: ignore[misc]

    def run(
        self,
        fields: dict[str, Any],
        input_json: dict[str, Any],
        ctx: SimContext,
    ) -> SimResult:
        t0 = perf_counter_ns()
        if ctx.llm is None:
            raise ToolLLMFailed("no LLMClient in SimContext")

        pp = PromptBuilder(self._tpl).with_fields(fields).with_input(input_json).build()
        try:
            resp = ctx.llm.call_sync(
                system=pp.system,
                user=pp.user,
                model=None,
                output_schema=self._tpl.output_schema,
                node_name=f"tool_sim:{self._tpl.name}",
            )
        except Exception as e:
            raise ToolLLMFailed(str(e)) from e

        data = resp.parsed_json
        validate_output(self._tpl.output_schema, data)
        return SimResult(
            output=data,
            engine_used=Engine.LLM,
            llm_call_ref=getattr(resp, "call_id", None),
            duration_ms=(perf_counter_ns() - t0) // 1_000_000,
        )
