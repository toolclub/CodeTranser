# 03 · 节点模板子系统(Tool)

> **后端内部代码**里继续叫 `Tool` / `NodeTemplate`(别名,二选一);**对外文档/前端/API** 统一叫 "节点模板 / node-template"。本章两个词混用,以表名 `t_node_template` 为准。
>
> 依赖:01(值对象、DTO、DDL)、02(DB 会话、Redis、Logging)
> 交付物:
> - ToolSimulator 抽象 + 自动注册表
> - SimulatorFactory / ToolRegistry(缓存 + pub/sub 热重载) / Loader
> - 节点模板 JSON Parser
> - ToolRepo + ToolService + 两套 API(前端 `/api/node-templates` + 管理 `/api/admin/node-templates`)
> - **元模板** Service + API(`/api/admin/meta-node-template`)
> - 一份完整示例模拟器(`IndexTableLookup`)+ 一份示例 JSON 定义
>
> 验收:
> 1. admin 可通过 `POST /api/admin/node-templates` 建一个全局 `IndexTableLookup`(JSON body)
> 2. 设计人员可通过 `POST /api/node-templates` 建私有节点模板(强制 engine=llm)
> 3. `POST /api/admin/node-templates/{id}/simulate` 对 pure_python 节点模板能跑出正确输出
> 4. `GET /api/admin/meta-node-template` 能读出预置元模板(01.ddl 已插入)
> 5. `python -m app.cli verify_simulators` 0 错
> 6. 新增节点模板(非 pure_python)完全不需要动代码;新增 pure_python 节点模板只需往 `simulators/pure_python/` 加一个类
> 7. 覆盖率:模拟器 ≥ 90%,框架 ≥ 85%

---

## 3.1 核心认知

1. **节点模板 = 一种节点类型**(种类);一张图里同一个节点模板可以被实例化任意多次
2. **节点模板是数据**:规格(description / schema / 边语义 / code_hints / extensions)**全部**以 **JSON + DB** 形式存在;代码里**无针对具体节点模板的硬编码**
3. **唯一和"代码"相关的是模拟器**:当节点模板 `engine=pure_python` 时,需要配一份"同名 Python 类"做 JSON 层的确定性计算。类的命名/路径按固定约定,由注册表自动发现
4. **框架对节点模板数量完全无感**:Registry / Factory / Service / API / LangGraph 节点都只依赖"节点模板"抽象
5. **节点模板是后端概念的对外名字**;前端只接触 `/api/node-templates` 投影(见 §3.16.2)
6. **设计人员也是节点模板的作者**:
   - 通过前端 UI 按元模板填表单 → `POST /api/node-templates` → 创建**私有节点模板**(强制 engine=llm)
   - admin 直接走 `POST /api/admin/node-templates` → 可创建**全局节点模板**(engine 任意;可配 pure_python 同名类)
7. **元模板**是"节点模板表单长什么样"的单例 JSON,预置在 `t_meta_node_template`(01.ddl 已插入),admin 可改

### 3.1.1 LLM 在节点模板子系统 vs Phase1 的双重角色

| 角色 | 在哪里落地 | 做什么 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| **单节点解释器**(被调) | 本章 `LLMSimulator`(§3.8) | engine=llm 时,按模板 description 推理 output_json | `fields, input_json` | `output_json` |
| **森林驱动者**(主导) | 07 章 `ScenarioRunHandler` | 读森林 + 所有节点模板 description,通过 tool-call 逐节点调解释器,串起整图,推理判定 | 森林 + scenario | `actual_output` + 归因 |

两者共用同一套 `LLMClient`(05 章),**调用层级**不同。本章只管前者。

---

## 3.2 模块总览

```
app/tool_runtime/
├── __init__.py
├── base.py                     ToolSimulator 抽象、SimResult 常量
├── errors.py                   本子系统专属异常
├── factory.py                  SimulatorFactory
├── registry.py                 ToolRegistry(单例)
├── loader.py                   DB -> NodeTemplate 值对象 + Anthropic tool-spec 转换
├── json_parser.py              JSON dict/str -> NodeTemplateDefinitionDTO(校验 + 规范化)
├── prompt_builder.py           PromptBuilder(LLM 引擎渲染 system prompt)
├── json_schema.py              JSON Schema 校验包装(jsonschema 库)
├── meta_template.py            元模板服务(读/写)
├── cross_validator.py          CI: example_fragment vs python 模拟器行为一致性(09 章真接沙箱后跑通)
└── simulators/
    ├── __init__.py             SIMULATOR_REGISTRY 自动收集
    ├── common.py               模拟器公共小工具
    ├── llm_generic.py          LLMSimulator(所有 engine=llm 共用)
    ├── hybrid.py               HybridSimulator(primary + llm fallback)
    └── pure_python/
        ├── __init__.py
        └── index_table_lookup.py   ← 唯一的示例实现,作为模板

app/repositories/tool_repo.py       t_node_template / t_node_template_version 仓储
app/services/tool_service.py        节点模板服务
app/services/meta_template_service.py  元模板服务
app/api/admin_tools.py              管理员 / Tool 作者路由
app/api/node_templates.py           前端路由(只读 + 设计人员创建私有)
app/api/admin_meta_template.py      元模板路由(仅 admin)
app/cli/verify_simulators.py        自检:pure_python 节点模板 ↔ SIMULATOR_REGISTRY 对齐
```

**注意**:**没有** `seed_tools` CLI 和 `backend/tools/seed/` 目录。节点模板通过 UI/API 创建,admin 手动复制 JSON 亦可。

---

## 3.3 异常

```python
# app/tool_runtime/errors.py
from app.domain.errors import BusinessError, DependencyError

class NodeTemplateNotFound(BusinessError):      code = "TOOL_NOT_FOUND";                    http_status = 404
class TemplateDefinitionInvalid(BusinessError): code = "VALIDATION_TEMPLATE_SCHEMA_INVALID"
class SimulatorNotRegistered(BusinessError):    code = "BUSINESS_MISSING_SIMULATOR"
class SimulatorInputInvalid(BusinessError):     code = "VALIDATION_SIM_INPUT_INVALID"
class SimulatorOutputInvalid(BusinessError):    code = "VALIDATION_SIM_OUTPUT_INVALID"
class ToolLLMFailed(DependencyError):           code = "DEPENDENCY_LLM_UNAVAILABLE"
class MetaTemplateError(BusinessError):         code = "META_TEMPLATE_INVALID"
```

---

## 3.4 ToolSimulator 抽象

```python
# app/tool_runtime/base.py
from abc import ABC, abstractmethod
from typing import ClassVar
from app.domain.run.sim import SimContext, SimResult
from app.domain.tool.tool import Engine

class ToolSimulator(ABC):
    """所有节点模板模拟器的抽象基类。

    约定:
      - **无状态**,同一实例可并发调用
      - 入参 fields / input_json 只读
      - 不做网络 / 磁盘 IO,外部数据通过 ctx 注入
      - 抛异常 = 节点执行失败;由调用方(07 章 executor)捕获

    新增一个 pure_python 节点模板的方式:
      1. admin 通过 UI/API 建一个 global 节点模板,engine=pure_python,python_impl=<NodeTemplateName>
      2. 在 app/tool_runtime/simulators/pure_python/ 下新建一个 <name_snake>.py
         实现一个 ToolSimulator 子类,tool_name = <NodeTemplateName>
      3. 写单测
      4. 重启或调 /api/admin/node-templates/registry/reload
    """
    tool_name: ClassVar[str] = ""                    # = 节点模板 name
    engine:    ClassVar[Engine] = Engine.PURE_PYTHON

    @abstractmethod
    def run(self, fields: dict, input_json: dict, ctx: SimContext) -> SimResult: ...

    def validate_input(self, fields: dict, input_json: dict, ctx: SimContext) -> None:
        """可选覆盖;默认 no-op"""
```

---

## 3.5 JSON Schema 校验器

```python
# app/tool_runtime/json_schema.py
from functools import lru_cache
from typing import Any
import json
from jsonschema.validators import Draft202012Validator
from app.tool_runtime.errors import (
    SimulatorInputInvalid, SimulatorOutputInvalid, TemplateDefinitionInvalid,
)

def _key(schema: dict) -> str:
    return json.dumps(schema, sort_keys=True, ensure_ascii=False)

@lru_cache(maxsize=512)
def _compile(schema_json: str) -> Draft202012Validator:
    schema = json.loads(schema_json)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)

def validate_schema_self(schema: dict) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as e:
        raise TemplateDefinitionInvalid(str(e))

def validate_input(input_schema: dict, data: Any) -> None:
    v = _compile(_key(input_schema))
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if errs: raise SimulatorInputInvalid("; ".join(e.message for e in errs))

def validate_output(output_schema: dict, data: Any) -> None:
    v = _compile(_key(output_schema))
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if errs: raise SimulatorOutputInvalid("; ".join(e.message for e in errs))
```

---

## 3.6 模拟器公共小工具

```python
# app/tool_runtime/simulators/common.py
"""面向节点模板作者的小工具集合。按需增补。"""
from typing import Any
from app.tool_runtime.errors import SimulatorInputInvalid

def get_required(d: dict, *keys: str) -> tuple:
    missing = [k for k in keys if k not in d]
    if missing:
        raise SimulatorInputInvalid(f"missing fields: {missing}")
    return tuple(d[k] for k in keys)

def coerce_int(v: Any, name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise SimulatorInputInvalid(f"{name} must be int")
    return v

def effective_mask(mask: int | None, width_bits: int) -> int:
    if mask is None:
        return (1 << width_bits) - 1
    return mask & ((1 << width_bits) - 1)
```

---

## 3.7 示例节点模板:IndexTableLookup

作为"如何写一个节点模板 + 对应模拟器"的范本。

### 3.7.1 示例 JSON(作为 API 请求体 / 文档范例)

> 本 JSON **不是种子文件**。admin 想初始化一份 IndexTableLookup,可以复制下面的 body 调 `POST /api/admin/node-templates` 即可。文档里的这份 JSON 就是管理员的参考。

```json
{
  "name": "IndexTableLookup",
  "display_name": "索引表查询",
  "category": "table_ops",
  "scope": "global",
  "change_note": "initial",
  "definition": {
    "description": [
      "这是一个查索引表节点。",
      "语义:根据输入 key,在一张预定义的索引表里查找匹配项,返回对应 value。",
      "",
      "业务约束:",
      "- 表大小上限: {{ fields.MaxEntryNum }}",
      "- 键宽度: {{ fields.EntrySize }} 字节",
      "- Mask 为 null 时等价全 1 掩码",
      "",
      "JSON 层应该返回:",
      "- 命中: { \"hit\": true, \"value\": <对应值>, \"index\": <命中位置> }",
      "- 未命中: { \"hit\": false, \"value\": null, \"index\": null }"
    ],
    "input_schema": {
      "type": "object",
      "required": ["EntrySize", "MaxEntryNum"],
      "properties": {
        "EntrySize":   { "type": "integer", "minimum": 1, "maximum": 64 },
        "MaxEntryNum": { "type": "integer", "minimum": 1 },
        "Mask":        { "type": ["integer", "null"] }
      }
    },
    "output_schema": {
      "type": "object",
      "required": ["hit"],
      "properties": {
        "hit":   { "type": "boolean" },
        "value": {},
        "index": { "type": ["integer", "null"] }
      }
    },
    "simulator": {
      "engine": "pure_python",
      "python_impl": "IndexTableLookup",
      "llm_fallback": false
    },
    "edge_semantics": [
      { "field": "next_on_hit",  "description": "命中分支" },
      { "field": "next_on_miss", "description": "未命中分支" }
    ],
    "code_hints": {
      "style_hints": ["使用 std::array 而不是 std::vector", "命中即 return"],
      "forbidden":   ["禁止动态分配", "禁止抛异常"],
      "example_fragment": "auto lookup = [&](uint32_t key) -> std::optional<Value> {\n  for (size_t i = 0; i < {{ fields.MaxEntryNum }} && i < entries.size(); ++i) {\n    if ((entries[i].key & effective_mask) == (key & effective_mask)) {\n      return entries[i].value;\n    }\n  }\n  return std::nullopt;\n};"
    },
    "extensions": {}
  }
}
```

**关键点**:
- `description` 是**字符串数组**,后端 `"\n".join` 后作为 LLM 的 system prompt 渲染模板
- **没有** `granularity` 字段(粒度由节点实例在 Bundle 里 / 游离决定)
- `extensions` 开放位,前后端透传,未来加字段不改表

### 3.7.2 配套 Python 模拟器

```python
# app/tool_runtime/simulators/pure_python/index_table_lookup.py
from time import perf_counter_ns
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.simulators.common import coerce_int, effective_mask, get_required
from app.domain.run.sim import SimContext, SimResult
from app.domain.tool.tool import Engine


class IndexTableLookupSim(ToolSimulator):
    """查索引表。作为"怎么写一个节点模板模拟器"的范本。

    fields:
      EntrySize: int (1~64)
      MaxEntryNum: int
      Mask: int | null
    input_json: { "key": int }
    output_json:
      命中: {"hit": true, "value": <Any>, "index": int}
      未命中: {"hit": false, "value": null, "index": null}
    ctx.table_data["entries"]: [{"key": int, "value": Any}, ...]
    """
    tool_name = "IndexTableLookup"
    engine = Engine.PURE_PYTHON

    def run(self, fields: dict, input_json: dict, ctx: SimContext) -> SimResult:
        t0 = perf_counter_ns()

        entries = ctx.get_table("entries")
        max_n = coerce_int(fields["MaxEntryNum"], "MaxEntryNum")
        width_bits = coerce_int(fields["EntrySize"], "EntrySize") * 8
        mask = effective_mask(fields.get("Mask"), width_bits)

        (key,) = get_required(input_json, "key")
        key = coerce_int(key, "key")

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
```

---

## 3.8 LLMSimulator(engine=llm 时共用)

```python
# app/tool_runtime/simulators/llm_generic.py
from time import perf_counter_ns
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.json_schema import validate_output
from app.tool_runtime.prompt_builder import PromptBuilder
from app.tool_runtime.errors import ToolLLMFailed
from app.domain.tool.tool import Engine, NodeTemplate
from app.domain.run.sim import SimResult, SimContext

class LLMSimulator(ToolSimulator):
    """engine=llm 的节点模板共用这一份。
       - description 渲染成 system prompt
       - fields + input_json 做 user 内容
       - 要求 LLM 返回满足 output_schema 的 JSON
    """
    engine = Engine.LLM

    def __init__(self, tpl: NodeTemplate) -> None:
        self._tpl = tpl
        self.tool_name = tpl.name              # type: ignore[misc]

    def run(self, fields, input_json, ctx: SimContext) -> SimResult:
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
            output=data, engine_used=Engine.LLM,
            llm_call_ref=resp.call_id,
            duration_ms=(perf_counter_ns() - t0) // 1_000_000,
        )
```

---

## 3.9 HybridSimulator(primary + fallback)

```python
# app/tool_runtime/simulators/hybrid.py
from time import perf_counter_ns
from app.tool_runtime.base import ToolSimulator
from app.domain.tool.tool import Engine
from app.domain.run.sim import SimResult, SimContext

class HybridSimulator(ToolSimulator):
    """primary 抛或返回 error 时,若配了 fallback 则转 LLM。"""
    engine = Engine.HYBRID

    def __init__(self, primary: ToolSimulator, fallback: ToolSimulator | None) -> None:
        self._primary = primary
        self._fallback = fallback
        self.tool_name = primary.tool_name           # type: ignore[misc]

    def run(self, fields, input_json, ctx: SimContext) -> SimResult:
        t0 = perf_counter_ns()
        try:
            r = self._primary.run(fields, input_json, ctx)
            if r.error is None:
                return r
        except Exception:
            if self._fallback is None:
                raise
        if self._fallback is None:
            raise
        r = self._fallback.run(fields, input_json, ctx)
        r.duration_ms = (perf_counter_ns() - t0) // 1_000_000
        return r
```

---

## 3.10 PromptBuilder

```python
# app/tool_runtime/prompt_builder.py
from dataclasses import dataclass
from jinja2 import Environment, StrictUndefined, BaseLoader
from app.domain.tool.tool import NodeTemplate

@dataclass(frozen=True, slots=True)
class PromptPair:
    system: str
    user: str

class PromptBuilder:
    """把 NodeTemplate.description(Jinja 模板)+ 字段 → system;
       input_json + fields JSON 化 → user。"""

    _env = Environment(
        loader=BaseLoader(),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )

    def __init__(self, tpl: NodeTemplate) -> None:
        self._tpl = tpl
        self._ctx: dict = {"fields": {}, "input": None, "examples": None}

    def with_fields(self, fv: dict) -> "PromptBuilder":
        self._ctx["fields"] = dict(fv); return self
    def with_input(self, inp: dict) -> "PromptBuilder":
        self._ctx["input"] = inp; return self
    def with_examples(self, exs: list) -> "PromptBuilder":
        self._ctx["examples"] = exs; return self

    def build(self) -> PromptPair:
        import json
        # NodeTemplate.description 此处已经是 "\n".join 后的单串(loader 做的)
        tmpl = self._env.from_string(self._tpl.description)
        system = tmpl.render(**self._ctx)
        user = json.dumps(
            {"fields": self._ctx["fields"], "input": self._ctx["input"]},
            ensure_ascii=False,
        )
        return PromptPair(system=system, user=user)
```

---

## 3.11 自动收集 + SimulatorFactory

```python
# app/tool_runtime/simulators/__init__.py
from __future__ import annotations
import importlib, pkgutil
from app.tool_runtime.base import ToolSimulator

SIMULATOR_REGISTRY: dict[str, type[ToolSimulator]] = {}

def _scan() -> None:
    from . import pure_python
    for _, name, _ in pkgutil.iter_modules(pure_python.__path__):
        mod = importlib.import_module(f"{pure_python.__name__}.{name}")
        for attr in vars(mod).values():
            if (isinstance(attr, type)
                and issubclass(attr, ToolSimulator)
                and attr is not ToolSimulator
                and attr.tool_name):
                if attr.tool_name in SIMULATOR_REGISTRY:
                    raise RuntimeError(f"duplicate simulator for {attr.tool_name}")
                SIMULATOR_REGISTRY[attr.tool_name] = attr

_scan()
```

```python
# app/tool_runtime/factory.py
from app.domain.tool.tool import NodeTemplate, Engine
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.simulators import SIMULATOR_REGISTRY
from app.tool_runtime.simulators.llm_generic import LLMSimulator
from app.tool_runtime.simulators.hybrid import HybridSimulator
from app.tool_runtime.errors import SimulatorNotRegistered

class SimulatorFactory:
    def create(self, tpl: NodeTemplate) -> ToolSimulator:
        if tpl.simulator.engine is Engine.PURE_PYTHON:
            return self._pure(tpl)
        if tpl.simulator.engine is Engine.LLM:
            return LLMSimulator(tpl)
        if tpl.simulator.engine is Engine.HYBRID:
            primary  = self._pure(tpl) if tpl.simulator.python_impl else None
            fallback = LLMSimulator(tpl) if tpl.simulator.llm_fallback else None
            if primary is None and fallback is None:
                raise SimulatorNotRegistered(
                    f"hybrid template {tpl.name} has neither primary nor fallback"
                )
            if primary is None:
                return fallback                  # type: ignore[return-value]
            return HybridSimulator(primary, fallback)
        raise ValueError(f"unknown engine {tpl.simulator.engine}")

    def _pure(self, tpl: NodeTemplate) -> ToolSimulator:
        # 私有 + pure_python 已被 NodeTemplate.__post_init__ 阻止
        cls = SIMULATOR_REGISTRY.get(tpl.name)
        if cls is None:
            raise SimulatorNotRegistered(f"no python simulator for template {tpl.name}")
        return cls()
```

---

## 3.12 ToolRegistry(单例 + 缓存 + pub/sub)

```python
# app/tool_runtime/registry.py
from __future__ import annotations
import asyncio
from redis.asyncio import Redis
from app.domain.tool.tool import NodeTemplate, Scope
from app.tool_runtime.factory import SimulatorFactory
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.loader import ToolLoader, to_anthropic_tool_spec

class ToolRegistry:
    CHANNEL = "tool_registry:invalidate"

    def __init__(self, loader: ToolLoader, factory: SimulatorFactory, redis: Redis) -> None:
        self._loader = loader
        self._factory = factory
        self._redis = redis
        self._cache_tpl: dict[str, NodeTemplate] = {}
        self._cache_sim: dict[str, ToolSimulator] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.CHANNEL)
        asyncio.create_task(self._listen(pubsub))

    async def _listen(self, pubsub):
        async for msg in pubsub.listen():
            if msg.get("type") == "message":
                self._cache_tpl.clear()
                self._cache_sim.clear()

    @staticmethod
    def _key(name: str, owner_id: int | None, version: int | None) -> str:
        return f"{name}|{owner_id or 0}|{version or 0}"

    async def get(self, *, name: str, owner_id: int | None = None,
                  scope: Scope = Scope.GLOBAL, version: int | None = None) -> NodeTemplate:
        k = self._key(name, owner_id, version)
        if (t := self._cache_tpl.get(k)) is not None: return t
        async with self._lock:
            if (t := self._cache_tpl.get(k)) is not None: return t
            t = await self._loader.load(name=name, owner_id=owner_id, scope=scope, version=version)
            self._cache_tpl[k] = t
            return t

    async def get_by_id(self, template_id: str, version: int | None = None) -> NodeTemplate:
        t = await self._loader.load_by_id(template_id, version)
        self._cache_tpl[self._key(t.name, t.owner_id, version)] = t
        return t

    def simulator_of(self, tpl: NodeTemplate) -> ToolSimulator:
        k = f"{tpl.name}|{tpl.version}|{tpl.owner_id or 0}"
        s = self._cache_sim.get(k)
        if s is None:
            s = self._factory.create(tpl)
            self._cache_sim[k] = s
        return s

    def for_llm(self, templates: list[NodeTemplate]) -> list[dict]:
        return [to_anthropic_tool_spec(t) for t in templates]

    async def invalidate(self, template_id: str | None = None) -> None:
        self._cache_tpl.clear(); self._cache_sim.clear()
        await self._redis.publish(self.CHANNEL, template_id or "*")
```

---

## 3.13 节点模板 JSON Parser

> 节点模板定义以 JSON 提交(API)或存 DB(`t_node_template_version.definition` 字段)。本模块做**入参校验 + 规范化**(description 数组 join、schema 自检)。

```python
# app/tool_runtime/json_parser.py
from app.schemas.tool import NodeTemplateDefinitionDTO
from app.tool_runtime.errors import TemplateDefinitionInvalid
from app.tool_runtime.json_schema import validate_schema_self

def parse_definition(raw: dict) -> NodeTemplateDefinitionDTO:
    try:
        dto = NodeTemplateDefinitionDTO.model_validate(raw)
    except Exception as e:
        raise TemplateDefinitionInvalid(str(e)) from e
    validate_schema_self(dto.input_schema)
    validate_schema_self(dto.output_schema)
    return dto

def join_description(description: list[str]) -> str:
    """前端传上来是字符串数组,落 DB 原样(数组),值对象里是 join 后的单串"""
    return "\n".join(description)
```

---

## 3.14 ToolLoader(DB → NodeTemplate 值对象)

```python
# app/tool_runtime/loader.py
from sqlalchemy import select
from app.models.mysql.node_template import NodeTemplateRow
from app.models.mysql.node_template_version import NodeTemplateVersionRow
from app.domain.tool.tool import (
    NodeTemplate, Scope, Engine, EdgeSemantic,
    JsonSimulatorSpec, CodeGenerationHints,
)
from app.tool_runtime.errors import NodeTemplateNotFound

class ToolLoader:
    def __init__(self, session_factory) -> None:
        self._sf = session_factory

    async def load_by_id(self, template_id: str, version: int | None = None) -> NodeTemplate:
        async with self._sf() as s:
            row = (await s.execute(
                select(NodeTemplateRow).where(NodeTemplateRow.id == template_id)
            )).scalar_one_or_none()
            if row is None: raise NodeTemplateNotFound(template_id)
            q = select(NodeTemplateVersionRow).where(NodeTemplateVersionRow.template_id == template_id)
            if version is not None:
                q = q.where(NodeTemplateVersionRow.version_number == version)
            else:
                q = q.where(NodeTemplateVersionRow.id == row.current_version_id)
            v = (await s.execute(q)).scalar_one_or_none()
            if v is None: raise NodeTemplateNotFound(f"{template_id} v{version}")
            return _row_to_tpl(row, v)

    async def load(self, *, name: str, owner_id: int | None, scope: Scope,
                   version: int | None = None) -> NodeTemplate:
        async with self._sf() as s:
            q = select(NodeTemplateRow).where(
                NodeTemplateRow.name == name,
                NodeTemplateRow.scope == scope.value,
            )
            if scope is Scope.PRIVATE and owner_id is not None:
                q = q.where(NodeTemplateRow.owner_id == owner_id)
            row = (await s.execute(q)).scalar_one_or_none()
            if row is None: raise NodeTemplateNotFound(name)
            return await self.load_by_id(row.id, version)

def _row_to_tpl(row: NodeTemplateRow, ver: NodeTemplateVersionRow) -> NodeTemplate:
    d = ver.definition
    # description 在 DB 里是 list[str],值对象里 join 成单串
    desc = "\n".join(d["description"]) if isinstance(d["description"], list) else d["description"]
    sim = JsonSimulatorSpec(
        engine=Engine(d["simulator"]["engine"]),
        python_impl=d["simulator"].get("python_impl"),
        llm_fallback=bool(d["simulator"].get("llm_fallback", False)),
    )
    ch_raw = d.get("code_hints", {}) or {}
    ch = CodeGenerationHints(
        style_hints=tuple(ch_raw.get("style_hints", [])),
        forbidden=tuple(ch_raw.get("forbidden", [])),
        example_fragment=ch_raw.get("example_fragment", ""),
    )
    es = tuple(EdgeSemantic(e["field"], e.get("description", ""))
               for e in d.get("edge_semantics", []))
    return NodeTemplate(
        id=row.id, name=row.name, display_name=row.display_name, category=row.category,
        scope=Scope(row.scope), version=ver.version_number,
        description=desc,
        input_schema=d["input_schema"], output_schema=d["output_schema"],
        simulator=sim, edge_semantics=es, code_hints=ch,
        extensions=d.get("extensions", {}),
        definition_hash=ver.definition_hash,
        owner_id=row.owner_id,
    )

def to_anthropic_tool_spec(tpl: NodeTemplate) -> dict:
    return {
        "name": tpl.name,
        "description": tpl.description,
        "input_schema": dict(tpl.input_schema),
    }
```

---

## 3.15 ToolRepo SQL 实现

```python
# app/repositories/tool_repo.py
from abc import ABC, abstractmethod
from sqlalchemy import select, update
from app.repositories.base import SqlRepoBase
from app.models.mysql.node_template import NodeTemplateRow
from app.models.mysql.node_template_version import NodeTemplateVersionRow
from app.schemas.tool import NodeTemplateCreateDTO, NodeTemplateDefinitionDTO
from app.domain.tool.tool import Scope
from app.utils.hash import sha256_json
from app.utils.ids import new_id
from app.tool_runtime.errors import NodeTemplateNotFound, TemplateDefinitionInvalid

class ToolRepo(ABC):
    @abstractmethod
    async def create(self, dto: NodeTemplateCreateDTO, user_id: int) -> tuple[str, int]: ...
    @abstractmethod
    async def update_create_version(self, template_id: str, definition: NodeTemplateDefinitionDTO,
                                    change_note: str, user_id: int) -> int: ...
    @abstractmethod
    async def activate_version(self, template_id: str, version_number: int) -> None: ...
    @abstractmethod
    async def list(self, *, scope: Scope | None, owner_id: int | None,
                   category: str | None, status: str | None = None) -> list[NodeTemplateRow]: ...
    @abstractmethod
    async def soft_delete(self, template_id: str) -> None: ...
    @abstractmethod
    async def fork_to_private(self, template_id: str, owner_id: int, user_id: int) -> str: ...
    @abstractmethod
    async def get(self, template_id: str) -> NodeTemplateRow: ...
    @abstractmethod
    async def get_version(self, template_id: str, version_number: int) -> NodeTemplateVersionRow: ...
    @abstractmethod
    async def list_versions(self, template_id: str) -> list[NodeTemplateVersionRow]: ...

class SqlToolRepo(SqlRepoBase, ToolRepo):
    async def create(self, dto, user_id):
        q = select(NodeTemplateRow).where(
            NodeTemplateRow.name == dto.name,
            NodeTemplateRow.scope == dto.scope,
        )
        if dto.scope == "private":
            q = q.where(NodeTemplateRow.owner_id == user_id)
        if (await self._s.execute(q)).scalar_one_or_none():
            raise TemplateDefinitionInvalid(f"duplicate template name: {dto.name}")

        tid = new_id("tpl")
        vid = new_id("tpv")
        defn = dto.definition.model_dump()
        self._s.add(NodeTemplateRow(
            id=tid, name=dto.name, display_name=dto.display_name, category=dto.category,
            scope=dto.scope, status="active",
            owner_id=(user_id if dto.scope == "private" else None),
            created_by=user_id,
            current_version_id=vid,
        ))
        self._s.add(NodeTemplateVersionRow(
            id=vid, template_id=tid, version_number=1,
            definition=defn, definition_hash=sha256_json(defn),
            change_note=dto.change_note, created_by=user_id,
        ))
        await self._s.flush()
        return tid, 1

    async def update_create_version(self, template_id, definition, change_note, user_id):
        latest = (await self._s.execute(
            select(NodeTemplateVersionRow)
              .where(NodeTemplateVersionRow.template_id == template_id)
              .order_by(NodeTemplateVersionRow.version_number.desc())
        )).scalars().first()
        new_num = (latest.version_number if latest else 0) + 1
        vid = new_id("tpv")
        defn = definition.model_dump()
        self._s.add(NodeTemplateVersionRow(
            id=vid, template_id=template_id, version_number=new_num,
            definition=defn, definition_hash=sha256_json(defn),
            change_note=change_note, created_by=user_id,
        ))
        await self._s.flush()
        await self._s.execute(
            update(NodeTemplateRow)
              .where(NodeTemplateRow.id == template_id)
              .values(current_version_id=vid)
        )
        return new_num

    async def activate_version(self, template_id, version_number):
        v = await self.get_version(template_id, version_number)
        await self._s.execute(
            update(NodeTemplateRow).where(NodeTemplateRow.id == template_id)
              .values(current_version_id=v.id)
        )

    async def list(self, *, scope, owner_id, category, status=None):
        q = select(NodeTemplateRow).where(NodeTemplateRow.deleted_at.is_(None))
        if scope is not None:    q = q.where(NodeTemplateRow.scope == scope.value)
        if owner_id is not None: q = q.where(NodeTemplateRow.owner_id == owner_id)
        if category is not None: q = q.where(NodeTemplateRow.category == category)
        if status is not None:   q = q.where(NodeTemplateRow.status == status)
        return list((await self._s.execute(q)).scalars().all())

    async def soft_delete(self, template_id):
        from app.utils.clock import utcnow
        await self._s.execute(
            update(NodeTemplateRow).where(NodeTemplateRow.id == template_id).values(deleted_at=utcnow())
        )

    async def fork_to_private(self, template_id, owner_id, user_id):
        src = await self.get(template_id)
        src_v = (await self._s.execute(
            select(NodeTemplateVersionRow).where(NodeTemplateVersionRow.id == src.current_version_id)
        )).scalar_one()
        # 私有强制 engine=llm
        definition = dict(src_v.definition)
        definition["simulator"] = {"engine": "llm", "python_impl": None, "llm_fallback": False}
        new_tid = new_id("tpl")
        new_vid = new_id("tpv")
        self._s.add(NodeTemplateRow(
            id=new_tid, name=src.name + "_fork", display_name=f"{src.display_name} (Fork)",
            category=src.category, scope="private", status="active",
            owner_id=owner_id, forked_from_id=src.id, created_by=user_id,
            current_version_id=new_vid,
        ))
        self._s.add(NodeTemplateVersionRow(
            id=new_vid, template_id=new_tid, version_number=1,
            definition=definition, definition_hash=sha256_json(definition),
            change_note="fork", created_by=user_id,
        ))
        await self._s.flush()
        return new_tid

    async def get(self, template_id):
        row = (await self._s.execute(
            select(NodeTemplateRow).where(NodeTemplateRow.id == template_id)
        )).scalar_one_or_none()
        if row is None: raise NodeTemplateNotFound(template_id)
        return row

    async def get_version(self, template_id, version_number):
        v = (await self._s.execute(
            select(NodeTemplateVersionRow).where(
                NodeTemplateVersionRow.template_id == template_id,
                NodeTemplateVersionRow.version_number == version_number,
            )
        )).scalar_one_or_none()
        if v is None: raise NodeTemplateNotFound(f"{template_id} v{version_number}")
        return v

    async def list_versions(self, template_id):
        return list((await self._s.execute(
            select(NodeTemplateVersionRow).where(NodeTemplateVersionRow.template_id == template_id)
              .order_by(NodeTemplateVersionRow.version_number.desc())
        )).scalars().all())
```

---

## 3.16 ToolService + MetaTemplateService

### 3.16.1 ToolService

```python
# app/services/tool_service.py
import re
from app.repositories.tool_repo import ToolRepo
from app.tool_runtime.registry import ToolRegistry
from app.tool_runtime.errors import TemplateDefinitionInvalid, SimulatorNotRegistered
from app.tool_runtime.simulators import SIMULATOR_REGISTRY
from app.tool_runtime.json_schema import validate_input, validate_output
from app.tool_runtime.json_parser import parse_definition
from app.domain.tool.tool import Scope
from app.schemas.tool import (
    NodeTemplateCreateDTO, NodeTemplateUpdateDTO, NodeTemplateDefinitionDTO,
    NodeTemplateSimulateReqDTO, NodeTemplateSimulateRespDTO,
    NodeTemplateOutDTO, NodeTemplateCardDTO, EdgeSemanticDTO,
)
from app.domain.run.sim import SimContext
from app.middlewares.auth import CurrentUser
from app.domain.errors import Forbidden

_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_]{2,63}$")
_FIELD_RE = re.compile(r"^[a-z_][a-zA-Z0-9_]{0,63}$")

class ToolService:
    def __init__(self, repo: ToolRepo, registry: ToolRegistry, llm_client, settings) -> None:
        self._repo = repo
        self._registry = registry
        self._llm = llm_client
        self._settings = settings

    async def create_global(self, dto: NodeTemplateCreateDTO, user: CurrentUser) -> str:
        if not user.is_admin: raise Forbidden("create global template requires admin")
        if not _NAME_RE.match(dto.name): raise TemplateDefinitionInvalid("bad name")
        self._validate_definition(dto.definition, scope=Scope.GLOBAL)
        tid, _ = await self._repo.create(dto, user.id)
        await self._registry.invalidate(tid)
        return tid

    async def create_private(self, dto: NodeTemplateCreateDTO, user: CurrentUser) -> str:
        if dto.definition.simulator.engine != "llm":
            raise TemplateDefinitionInvalid("private template must use engine=llm")
        self._validate_definition(dto.definition, scope=Scope.PRIVATE)
        dto2 = dto.model_copy(update={"scope": "private"})
        tid, _ = await self._repo.create(dto2, user.id)
        await self._registry.invalidate(tid)
        return tid

    async def update(self, template_id: str, dto: NodeTemplateUpdateDTO, user: CurrentUser) -> int:
        row = await self._repo.get(template_id)
        self._require_can_write(row, user)
        scope = Scope(row.scope)
        if scope is Scope.PRIVATE and dto.definition.simulator.engine != "llm":
            raise TemplateDefinitionInvalid("private template must use engine=llm")
        self._validate_definition(dto.definition, scope=scope)
        new_ver = await self._repo.update_create_version(template_id, dto.definition, dto.change_note, user.id)
        await self._registry.invalidate(template_id)
        return new_ver

    def _validate_definition(self, d: NodeTemplateDefinitionDTO, *, scope: Scope) -> None:
        joined_desc = "\n".join(d.description)
        if len(joined_desc) > self._settings.TOOL_DESCRIPTION_MAX_LENGTH:
            raise TemplateDefinitionInvalid("description too long")
        for kw in self._settings.TOOL_INJECTION_BLOCKLIST or []:
            if kw and kw in joined_desc:
                raise TemplateDefinitionInvalid(f"blocklist hit: {kw}")
        parse_definition(d.model_dump())    # 双 schema 自检
        if d.simulator.engine == "pure_python":
            if scope is Scope.PRIVATE:
                raise TemplateDefinitionInvalid("private template must be engine=llm")
            impl = d.simulator.python_impl
            if impl is None or impl not in SIMULATOR_REGISTRY:
                raise SimulatorNotRegistered(impl or "<none>")
        for e in d.edge_semantics:
            if not _FIELD_RE.match(e.field):
                raise TemplateDefinitionInvalid(f"invalid edge field: {e.field}")
        fields = [e.field for e in d.edge_semantics]
        if len(set(fields)) != len(fields):
            raise TemplateDefinitionInvalid("duplicate edge_semantics.field")

    def _require_can_write(self, row, user):
        if user.is_admin: return
        if row.scope == "global":
            raise Forbidden("global template is admin-only")
        if row.owner_id != user.id:
            raise Forbidden("not your private template")

    async def simulate(self, template_id: str, req: NodeTemplateSimulateReqDTO,
                       user: CurrentUser) -> NodeTemplateSimulateRespDTO:
        tpl = await self._registry.get_by_id(template_id)
        sim = self._registry.simulator_of(tpl)
        ctx = SimContext(
            run_id="preview", instance_id="preview",
            table_data=req.tables, llm=self._llm, trace=None,
        )
        validate_input(tpl.input_schema, req.field_values)
        r = sim.run(req.field_values, req.input_json, ctx)
        validate_output(tpl.output_schema, r.output)
        return NodeTemplateSimulateRespDTO(
            output_json=r.output,
            engine_used=r.engine_used.value,
            duration_ms=r.duration_ms,
            llm_call_id=r.llm_call_ref,
        )

    async def fork(self, template_id: str, user: CurrentUser) -> str:
        new_id = await self._repo.fork_to_private(template_id, user.id, user.id)
        await self._registry.invalidate(new_id)
        return new_id

    async def list_visible(self, *, scope, category, user) -> list[NodeTemplateRowLike]:
        return await self._repo.list(
            scope=Scope(scope) if scope in ("global","private") else None,
            owner_id=user.id if scope == "private" else None,
            category=category,
        )

    def to_card_dto(self, tpl) -> NodeTemplateCardDTO:
        """投影给前端"""
        return NodeTemplateCardDTO(
            id=tpl.id, name=tpl.name, display_name=tpl.display_name,
            category=tpl.category, current_version=tpl.version,
            input_schema=dict(tpl.input_schema),
            edge_semantics=[EdgeSemanticDTO(field=e.field, description=e.description)
                            for e in tpl.edge_semantics],
            extensions=dict(tpl.extensions),
        )

    def to_out_dto(self, tpl) -> NodeTemplateOutDTO:
        """完整定义给 admin"""
        ...   # 逆向从 NodeTemplate 构造 NodeTemplateOutDTO
```

### 3.16.2 MetaTemplateService(单例管理)

```python
# app/services/meta_template_service.py
from sqlalchemy import select, update
from app.repositories.base import SqlRepoBase
from app.models.mysql.meta_template import MetaTemplateRow
from app.schemas.meta_template import MetaTemplateDTO, MetaTemplateUpdateDTO
from app.domain.errors import NotFound
from app.tool_runtime.errors import MetaTemplateError

META_ID = 1

class MetaTemplateService:
    def __init__(self, session_factory) -> None:
        self._sf = session_factory

    async def get(self) -> MetaTemplateDTO:
        async with self._sf() as s:
            row = (await s.execute(
                select(MetaTemplateRow).where(MetaTemplateRow.id == META_ID)
            )).scalar_one_or_none()
            if row is None:
                raise NotFound("meta template not initialized (01.ddl 应已 INSERT)")
            return MetaTemplateDTO.model_validate(row.content)

    async def update(self, dto: MetaTemplateUpdateDTO, user_id: int) -> None:
        # 简单校验:每个 field.key 非空且唯一
        keys = [f.key for f in dto.content.fields]
        if len(set(keys)) != len(keys):
            raise MetaTemplateError("duplicate field key")
        if not all(k for k in keys):
            raise MetaTemplateError("empty field key")

        async with self._sf() as s:
            row = (await s.execute(
                select(MetaTemplateRow).where(MetaTemplateRow.id == META_ID)
            )).scalar_one_or_none()
            if row is None:
                s.add(MetaTemplateRow(
                    id=META_ID, content=dto.content.model_dump(),
                    note=dto.note, updated_by=user_id,
                ))
            else:
                await s.execute(
                    update(MetaTemplateRow).where(MetaTemplateRow.id == META_ID).values(
                        content=dto.content.model_dump(),
                        note=dto.note, updated_by=user_id,
                    )
                )
            await s.commit()
```

---

## 3.17 API 路由(三套)

### 3.17.1 管理员 / Tool 作者路由(完整定义)

```python
# app/api/admin_tools.py
from fastapi import APIRouter, Depends, Request
from typing import Literal
from app.schemas.common import ApiResponse
from app.schemas.tool import (
    NodeTemplateCreateDTO, NodeTemplateUpdateDTO, NodeTemplateOutDTO,
    NodeTemplateSimulateReqDTO, NodeTemplateSimulateRespDTO,
)
from app.middlewares.auth import require_user, require_admin
from app.services.tool_service import ToolService
from app.infra.db.deps import get_session

router = APIRouter(prefix="/api/admin/node-templates", tags=["admin-node-templates"])

async def _svc(request: Request, session=Depends(get_session)) -> ToolService:
    return request.app.state.container.tool_service_factory(session)

@router.post("", response_model=ApiResponse[dict], status_code=201)
async def create_global(body: NodeTemplateCreateDTO, user=Depends(require_admin),
                        svc: ToolService = Depends(_svc)):
    tid = await svc.create_global(body, user)
    return ApiResponse(data={"template_id": tid})

@router.put("/{template_id}", response_model=ApiResponse[dict])
async def update_tpl(template_id: str, body: NodeTemplateUpdateDTO, user=Depends(require_user),
                     svc: ToolService = Depends(_svc)):
    v = await svc.update(template_id, body, user)
    return ApiResponse(data={"version_number": v})

@router.get("/{template_id}", response_model=ApiResponse[NodeTemplateOutDTO])
async def get_tpl(template_id: str, version: int | None = None, user=Depends(require_user),
                  svc: ToolService = Depends(_svc)):
    tpl = await svc._registry.get_by_id(template_id, version)
    return ApiResponse(data=svc.to_out_dto(tpl))

@router.get("/{template_id}/versions", response_model=ApiResponse[list])
async def versions(template_id: str, user=Depends(require_user),
                   svc: ToolService = Depends(_svc)):
    rs = await svc._repo.list_versions(template_id)
    return ApiResponse(data=[{"version_number": r.version_number,
                              "change_note": r.change_note,
                              "created_at": r.created_at.isoformat()} for r in rs])

@router.post("/{template_id}/versions/{ver}/activate", response_model=ApiResponse[dict])
async def activate(template_id: str, ver: int, user=Depends(require_user),
                   svc: ToolService = Depends(_svc)):
    await svc._repo.activate_version(template_id, ver)
    await svc._registry.invalidate(template_id)
    return ApiResponse(data={"ok": True})

@router.post("/{template_id}/fork", response_model=ApiResponse[dict])
async def fork(template_id: str, user=Depends(require_user), svc: ToolService = Depends(_svc)):
    new_id = await svc.fork(template_id, user)
    return ApiResponse(data={"template_id": new_id})

@router.post("/{template_id}/simulate", response_model=ApiResponse[NodeTemplateSimulateRespDTO])
async def simulate(template_id: str, body: NodeTemplateSimulateReqDTO,
                   user=Depends(require_user), svc: ToolService = Depends(_svc)):
    return ApiResponse(data=await svc.simulate(template_id, body, user))

@router.post("/registry/reload", response_model=ApiResponse[dict])
async def reload_registry(request: Request, user=Depends(require_admin)):
    await request.app.state.container.tool_registry.invalidate()
    return ApiResponse(data={"ok": True})
```

### 3.17.2 前端路由(node-templates,投影 + 私有创建)

```python
# app/api/node_templates.py
from fastapi import APIRouter, Depends, Request
from typing import Literal
from app.schemas.common import ApiResponse
from app.schemas.tool import NodeTemplateCardDTO, NodeTemplateCreateDTO
from app.middlewares.auth import require_user
from app.services.tool_service import ToolService
from app.infra.db.deps import get_session

router = APIRouter(prefix="/api/node-templates", tags=["node-templates"])

async def _svc(request: Request, session=Depends(get_session)) -> ToolService:
    return request.app.state.container.tool_service_factory(session)

@router.get("", response_model=ApiResponse[list[NodeTemplateCardDTO]])
async def list_cards(
    request: Request,
    category: str | None = None,
    scope: Literal["global", "private", "all"] = "all",
    user=Depends(require_user),
    svc: ToolService = Depends(_svc),
):
    rows = await svc.list_visible(scope=scope, category=category, user=user)
    cards: list[NodeTemplateCardDTO] = []
    for row in rows:
        tpl = await svc._registry.get_by_id(row.id)
        cards.append(svc.to_card_dto(tpl))
    return ApiResponse(data=cards)

@router.get("/{template_id}", response_model=ApiResponse[NodeTemplateCardDTO])
async def get_card(template_id: str, user=Depends(require_user), svc: ToolService = Depends(_svc)):
    tpl = await svc._registry.get_by_id(template_id)
    return ApiResponse(data=svc.to_card_dto(tpl))

@router.post("", response_model=ApiResponse[dict], status_code=201)
async def create_private(body: NodeTemplateCreateDTO, user=Depends(require_user),
                         svc: ToolService = Depends(_svc)):
    """设计人员建私有节点模板。强制 engine=llm(Service 层校验)"""
    tid = await svc.create_private(body, user)
    return ApiResponse(data={"template_id": tid})
```

### 3.17.3 元模板路由(admin)

```python
# app/api/admin_meta_template.py
from fastapi import APIRouter, Depends, Request
from app.schemas.common import ApiResponse
from app.schemas.meta_template import MetaTemplateDTO, MetaTemplateUpdateDTO
from app.middlewares.auth import require_user, require_admin
from app.services.meta_template_service import MetaTemplateService

router = APIRouter(prefix="/api/admin/meta-node-template", tags=["admin-meta-template"])

def _svc(request: Request) -> MetaTemplateService:
    return request.app.state.container.meta_template_service

# 前端也可以读元模板(渲染节点模板编辑表单);但写只给 admin
@router.get("", response_model=ApiResponse[MetaTemplateDTO])
async def get_meta(request: Request, user=Depends(require_user)):
    return ApiResponse(data=await _svc(request).get())

@router.put("", response_model=ApiResponse[dict])
async def update_meta(request: Request, body: MetaTemplateUpdateDTO,
                      user=Depends(require_admin)):
    await _svc(request).update(body, user.id)
    return ApiResponse(data={"ok": True})
```

> **供前端读元模板的公开路径**:也可把 `GET` 方法再挂一个 `/api/meta-node-template`(不带 admin 前缀)给前端用。v1 直接用 `/api/admin/meta-node-template` 的 GET(登录用户就能读),省一个路由。

---

## 3.18 CLI:verify_simulators

> **不再有** `seed_tools`。admin 通过 UI/API 建节点模板。

```python
# app/cli/verify_simulators.py
import asyncio
import click
from sqlalchemy import select
from app.cli import _run
from app.infra.db.session import session_scope
from app.tool_runtime.simulators import SIMULATOR_REGISTRY
from app.models.mysql.node_template import NodeTemplateRow
from app.models.mysql.node_template_version import NodeTemplateVersionRow

@click.command("verify_simulators")
def main():
    """校验:每个 global + engine=pure_python 的节点模板,python_impl 必须在 SIMULATOR_REGISTRY"""
    async def _do(c):
        errors: list[str] = []
        async with session_scope(c.session_factory) as s:
            rows = (await s.execute(
                select(NodeTemplateRow).where(
                    NodeTemplateRow.scope == "global",
                    NodeTemplateRow.deleted_at.is_(None),
                )
            )).scalars().all()
            for r in rows:
                v = (await s.execute(
                    select(NodeTemplateVersionRow).where(NodeTemplateVersionRow.id == r.current_version_id)
                )).scalar_one()
                eng = v.definition["simulator"]["engine"]
                impl = v.definition["simulator"].get("python_impl")
                if eng == "pure_python":
                    if impl != r.name:
                        errors.append(f"{r.name}: python_impl must equal template name")
                    if r.name not in SIMULATOR_REGISTRY:
                        errors.append(f"{r.name}: simulator class not registered")
                elif eng == "hybrid":
                    if impl and impl not in SIMULATOR_REGISTRY:
                        errors.append(f"{r.name}: hybrid primary {impl} not registered")
        if errors:
            for e in errors: print("ERR", e)
            raise SystemExit(1)
        print("[verify] all simulators registered OK")
    asyncio.run(_run(_do))

if __name__ == "__main__":
    main()
```

---

## 3.19 Bootstrap 装配(本章新增)

```python
# app/bootstrap.py (追加)
from app.tool_runtime.loader import ToolLoader
from app.tool_runtime.factory import SimulatorFactory
from app.tool_runtime.registry import ToolRegistry
from app.services.tool_service import ToolService
from app.services.meta_template_service import MetaTemplateService
from app.repositories.tool_repo import SqlToolRepo

def build_container(settings):
    # ...
    loader = ToolLoader(sf)
    sim_factory = SimulatorFactory()
    tool_registry = ToolRegistry(loader, sim_factory, redis)
    meta_template_service = MetaTemplateService(sf)

    container.tool_registry = tool_registry
    container.meta_template_service = meta_template_service
    container.tool_service_factory = lambda sess: ToolService(
        SqlToolRepo(sess), tool_registry, container.llm_client, settings,
    )

async def startup(container):
    await container.settings_service.start()
    await container.tool_registry.start()
```

---

## 3.20 节点模板作者指南(SOP)

> 本章的活文档。复制下面 SOP 任何 AI / 工程师 / 设计人员可直接照做。

### 设计人员(私有,engine=llm)

1. 打开前端"节点模板编辑器"——页面由 `GET /api/admin/meta-node-template` 的返回值驱动渲染(元模板定义了要填哪些字段)
2. 填完 `name / display_name / category / description / input_schema / output_schema / edge_semantics / code_hints` 等
3. `POST /api/node-templates` —— scope 自动 private,engine 强制 llm
4. 拿到 `template_id` 后就能在画布节点库里看到(`GET /api/node-templates`)

### Admin / Tool 作者(engine 任意)

1. 同上填表单 → `POST /api/admin/node-templates` —— 可选 `scope=global` 和 `engine=pure_python`
2. 如果 `engine=pure_python`:
   - 在 `app/tool_runtime/simulators/pure_python/<name_snake>.py` 新建一个 `ToolSimulator` 子类,`tool_name = <NodeTemplateName>`
   - 重启服务 **或** 调 `POST /api/admin/node-templates/registry/reload`
   - 跑 `python -m app.cli verify_simulators` 自检
3. 写单测 `tests/unit/tool_simulators/test_<name_snake>.py`

### 节点模板 JSON 必填字段(v1)

见 §3.7.1 示例。元模板(`t_meta_node_template` 表)定义了全部字段及类型;前端读元模板渲染表单,不用在前端硬编码。

### 扩展字段

- `code_hints.example_fragment` + `code_hints.style_hints` + `code_hints.forbidden` 是**代码生成**阶段(08 章)用的,Phase1 不看
- `extensions` 是**完全自由位**,前后端透传,不被校验。未来若需要加"图标 / 颜色 / 节点模板标签"等字段,先放 `extensions`,跑顺后再提升为一等字段

---

## 3.21 v1 显式不做的事

- ❌ 不预写除 IndexTableLookup 外的具体节点模板
- ❌ 不做 seed 目录;所有节点模板通过 UI/API 建
- ❌ 不做节点模板审批流
- ❌ 不做节点模板"从私有提拔到全局"自动化(admin 手动新建一份 global 即可)
- ❌ 不做 cross-validator 的真运行(framework 先落地,09 章接沙箱后跑通)

---

## 3.22 测试要点

### 3.22.1 示例模拟器单测

```python
# tests/unit/tool_simulators/test_index_table_lookup.py
import pytest
from app.tool_runtime.simulators.pure_python.index_table_lookup import IndexTableLookupSim
from app.domain.run.sim import SimContext

def ctx(**tables):
    return SimContext(run_id="t", instance_id="n", table_data=tables, llm=None, trace=None)

def test_hit():
    r = IndexTableLookupSim().run(
        {"EntrySize": 4, "MaxEntryNum": 2, "Mask": None}, {"key": 2},
        ctx(entries=[{"key": 1, "value": "a"}, {"key": 2, "value": "b"}]),
    )
    assert r.output == {"hit": True, "value": "b", "index": 1}

def test_miss():
    r = IndexTableLookupSim().run(
        {"EntrySize": 4, "MaxEntryNum": 1, "Mask": None}, {"key": 99},
        ctx(entries=[{"key": 1, "value": "a"}]),
    )
    assert r.output == {"hit": False, "value": None, "index": None}

def test_mask():
    r = IndexTableLookupSim().run(
        {"EntrySize": 2, "MaxEntryNum": 1, "Mask": 0xFF00}, {"key": 0xAB99},
        ctx(entries=[{"key": 0xABCD, "value": "x"}]),
    )
    assert r.output["hit"] is True

def test_missing_required_field():
    with pytest.raises(Exception):
        IndexTableLookupSim().run({"EntrySize": 4, "MaxEntryNum": 1, "Mask": None}, {}, ctx(entries=[]))
```

### 3.22.2 框架单测(不依赖具体模板)

- `test_registry_autoscan`:monkeypatch 一个假模拟器,SIMULATOR_REGISTRY 能拾到;重名抛
- `test_factory`:各 engine 路由正确;private + pure_python 被 `NodeTemplate.__post_init__` 拒绝
- `test_hybrid`:primary 成功 / primary 抛 + fallback 成功 / 都失败 三条路径
- `test_json_parser`:合法 JSON 通过;description 非数组报错;schema 非法报错
- `test_loader`:DB → NodeTemplate 字段准确;老版本可查
- `test_prompt_builder`:Jinja 缺字段报错;数组 description 不在此处拼接(是 loader 阶段拼)

### 3.22.3 Service / API 集成测

- 非 admin 创建 global 返 403
- 普通用户创建 private + engine=pure_python 被拒
- `update` 产生新 version_number
- `fork` 产生私有副本,engine 强制 llm
- `simulate` 对 IndexTableLookup 正确输出
- `list` 分 scope / category 能分别返回

### 3.22.4 元模板

- `GET /api/admin/meta-node-template` 返回 01.ddl 预置值
- admin `PUT` 修改后再次 GET 拿到新值
- 非 admin PUT 返 403

---

## 3.23 本章交付物清单

- [ ] `app/tool_runtime/base.py`
- [ ] `app/tool_runtime/errors.py`
- [ ] `app/tool_runtime/json_schema.py`
- [ ] `app/tool_runtime/json_parser.py`
- [ ] `app/tool_runtime/prompt_builder.py`
- [ ] `app/tool_runtime/factory.py`
- [ ] `app/tool_runtime/registry.py`
- [ ] `app/tool_runtime/loader.py`
- [ ] `app/tool_runtime/meta_template.py` (可与 service 合并)
- [ ] `app/tool_runtime/cross_validator.py` skeleton
- [ ] `app/tool_runtime/simulators/__init__.py` 自动扫描
- [ ] `app/tool_runtime/simulators/common.py`
- [ ] `app/tool_runtime/simulators/llm_generic.py`
- [ ] `app/tool_runtime/simulators/hybrid.py`
- [ ] `app/tool_runtime/simulators/pure_python/index_table_lookup.py` **(唯一的示例)**
- [ ] `app/repositories/tool_repo.py`
- [ ] `app/services/tool_service.py`
- [ ] `app/services/meta_template_service.py`
- [ ] `app/api/admin_tools.py`
- [ ] `app/api/node_templates.py`
- [ ] `app/api/admin_meta_template.py`
- [ ] `app/cli/verify_simulators.py`
- [ ] `tests/unit/tool_simulators/test_index_table_lookup.py`
- [ ] `tests/unit/tool_runtime/test_*.py`
- [ ] `tests/integration/test_tool_api.py`
- [ ] `tests/integration/test_meta_template_api.py`

---

下一份:[04_图森林子系统.md](./04_图森林子系统.md)
