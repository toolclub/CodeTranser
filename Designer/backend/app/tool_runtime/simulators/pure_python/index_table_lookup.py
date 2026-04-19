from time import perf_counter_ns
from typing import Any

from app.domain.run.sim import SimContext, SimResult
from app.domain.tool.tool import Engine
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.simulators.common import coerce_int, effective_mask, get_required


class IndexTableLookupSim(ToolSimulator):
    """查索引表。作为"怎么写一个节点模板模拟器"的范本。

    fields:
      EntrySize: int (1~64),字节数
      MaxEntryNum: int
      Mask: int | null
    input_json: { "key": int }
    output_json:
      命中:   {"hit": true,  "value": <Any>, "index": int}
      未命中: {"hit": false, "value": null,  "index": null}
    ctx.table_data["entries"]: [{"key": int, "value": Any}, ...]
    """

    tool_name = "IndexTableLookup"
    engine = Engine.PURE_PYTHON

    def run(
        self,
        fields: dict[str, Any],
        input_json: dict[str, Any],
        ctx: SimContext,
    ) -> SimResult:
        t0 = perf_counter_ns()

        entries = ctx.get_table("entries")
        max_n = coerce_int(fields["MaxEntryNum"], "MaxEntryNum")
        width_bits = coerce_int(fields["EntrySize"], "EntrySize") * 8
        mask = effective_mask(fields.get("Mask"), width_bits)

        (key_raw,) = get_required(input_json, "key")
        key = coerce_int(key_raw, "key")

        for i, entry in enumerate(entries[:max_n]):
            if (entry["key"] & mask) == (key & mask):
                return SimResult(
                    output={"hit": True, "value": entry["value"], "index": i},
                    engine_used=self.engine,
                    duration_ms=(perf_counter_ns() - t0) // 1_000_000,
                )
        return SimResult(
            output={"hit": False, "value": None, "index": None},
            engine_used=self.engine,
            duration_ms=(perf_counter_ns() - t0) // 1_000_000,
        )
