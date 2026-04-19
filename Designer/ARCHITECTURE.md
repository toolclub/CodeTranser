# 级跳(Cascade)设计平台 · 架构与代码解读

> 更新时间:2026-04-18
> 状态:骨架 + Ch01–07 + ChatFlow 协议改造 + K8S 分布式就绪 · 147 backend 测试全绿 · frontend `vite build` 通过

---

## 0. 一图看懂

```
┌────────────────────────────── 前端(K8S Ingress) ──────────────────────────────┐
│ Vue 3 + Pinia + Vue Router + @antv/x6                                          │
│ Pages: GraphList / CanvasEditor / TemplateLibrary / TemplateEditor /           │
│        Scenarios / RunList / RunDetail / CodeDiff / Review / NoPermission      │
│   Canvas OO:NodeShape / BundleShape / PortRegistry / FieldValueEditor         │
│   Store:graph / templates / runs / app(Pinia 分模块)                         │
│   API:分模块 axios + ApiResponse<T> 解包;401/403 跳 /no-permission           │
└───────────────────────────────┬────────────────────────────────────────────────┘
                                │  REST /api/*   WS /ws/*(Ch11 实装)
┌───────────────────────────────┴────────────────────────────────────────────────┐
│                         后端(K8S Deployment,多副本)                          │
│ ┌─────────── API 层(FastAPI,每 pod 独立) ─────────────────────────────┐     │
│ │ graphs / node-templates / admin-tools / admin-meta-template /            │     │
│ │ runs-events / runs-stop / runs-owner(分布式协调)                       │     │
│ └───────────────────┬─────────────────────────┬────────────────────────────┘     │
│                     │                         │                                  │
│ ┌─── Service 层 ────┘   ┌── LangGraph Runtime ┘ ─────────────────────────┐     │
│ │  GraphService           │ PipelineBuilder(variant:P1/P2/FULL)         │     │
│ │  ToolService(policy)    │ PhaseRouter(责任链)                         │     │
│ │  MetaTemplateService    │ BasePipelineStep(模板方法 + trace)           │     │
│ │  DesignValidator(9 Vs)  │ HandlerStep(Phase1 责任链)                  │     │
│ │  ForestParser(冻结)     │ Phase1:structure_check + scenario_run       │     │
│ └───────────┬─────────────┴──┬───────────────────┬────────────────────────┘     │
│             │                │                   │                              │
│  ┌──────────┴───┐  ┌─────────┴──────┐  ┌─────────┴──────┐                       │
│  │ tool_runtime │  │ llm(适配层)   │  │ graph(森林)   │                       │
│  │ - ToolRegistry│ │ - LLMClient    │  │ - Visitor*9    │                       │
│  │   (LRU+TTL)  │  │ - agent_loop   │  │ - TopologicalI │                       │
│  │ - SimFactory │  │ - Claude/OpenAI│  │ - DagCompute   │                       │
│  │ - Simulators │  │   /Mock Adapter│  │ - paste.ids    │                       │
│  └──────┬───────┘  └────┬───────────┘  └────────────────┘                       │
│         │               │                                                        │
│ ┌───────┴───┐  ┌────────┴──┐                                                    │
│ │ Repository│  │ FSM (base)│ WorkflowRunSM / RunStepSM / Phase1HandlerSM        │
│ │(DB I/O)  │  │ Event bus │ EventType enum + 优先级 + DB-first                  │
│ └───┬───────┘  └───────────┘                                                    │
│     │                                                                            │
└─────┼────────────────────────────────────────────────────────────────────────────┘
      │
┌─────┴─────┬──────────────┬────────────────┬────────────────────────────────────┐
│ MySQL     │ MongoDB       │ Redis          │ Checkpointer(Redis/Postgres)     │
│ t_* 19 表  │ run_step_details│cascade:run:*   │ LangGraph state 持久化            │
│ DDL/Migr  │ sandbox_traces│ cache+pubsub   │ pod 挂 → 任意 pod 续 thread_id=run │
└───────────┴──────────────┴────────────────┴────────────────────────────────────┘
```

---

## 1. 代码量统计

| 部分 | 行数 | 文件数 | 备注 |
|---|---|---|---|
| 后端 Python(`backend/app/`) | **9,509** | 192 | 业务代码 |
| 后端测试(`backend/tests/`) | **2,531** | 29 | 147 个测试全绿 |
| 后端 DDL(`backend/config/sql/`) | **324** | 3 | 01/02/03.ddl |
| 前端 TS + Vue + CSS + .d.ts(`frontend/src/`) | **3,037** | 45 | 页面 / 组件 / store / api / utils |
| 设计 + 实施文档(`impl-docs*/ + memory.md + ARCHITECTURE.md + 本文`) | — | ~15 | impl-docs 已 00-07,共 8963 行 |
| **合计(代码部分)** | **≈ 15,400** | **266** | 不含文档 |

**规模判断**:相当于一个**中型**后端 + 前端。后续加节点模板基本 0 代码增量(见 §7)。

---

## 2. 后端架构(Python 3.11 / FastAPI)

### 2.1 分层

```
app/
├── main.py                FastAPI 入口(lifespan:build_container + startup/shutdown)
├── bootstrap.py           组合根(AppContainer)+ build_workflow_runtime() 辅助
├── config.py              Settings(pydantic-settings)
├── settings_service.py    运行时动态配置(10s TTL + Redis pub/sub)
│
├── domain/                ★ 纯值对象(禁 import fastapi/sqlalchemy/redis)
│   ├── errors.py          DomainError 体系(14 类)
│   ├── fsm/               ★ WorkflowRunSM / RunStepSM / Phase1HandlerSM / PlanStepSM
│   ├── tool/              NodeTemplate / JsonSimulatorSpec / EdgeSemantic / ...
│   ├── graph/
│   │   ├── nodes.py       Bundle / NodeInstance / Edge / CascadeForest
│   │   ├── visitor.py     ForestVisitor 抽象
│   │   ├── visitors/      9 个具体 Visitor(cycle / node_ref / edge_semantic /
│   │   │                     schema_validation / duplicate_edge / orphan /
│   │   │                     metrics / diff / edge_map)
│   │   ├── iteration.py   TopologicalIterator(Kahn)
│   │   ├── dag_compute.py DagComputeVisitor(从 root 展开)
│   │   ├── builders.py    TemplateResolver(Protocol)+ FrozenResolver + build_forest
│   │   └── paste.py       rebuild_ids(跨图复制 ID 重发)
│   └── run/               CascadeState(TypedDict)+ Scenario + SimContext/SimResult
│
├── infra/
│   ├── db/{base,session,deps}.py    SQLAlchemy 2.0 async + session_scope
│   ├── mongo/client.py              AsyncIOMotorClient
│   ├── redis.py                     redis.asyncio
│   ├── metrics.py                   Prometheus 12 metrics
│   ├── logging.py                   structlog + trace_id + sanitize
│   ├── tracing.py                   trace_id_ctx(contextvar)
│   ├── migrate/runner.py            checksum-guarded DDL runner
│   ├── checkpointer.py              ★ LangGraph checkpointer 工厂(memory/redis/postgres)
│   └── run_control.py               ★ StopRegistry / SessionRegistry(跨 pod)
│
├── middlewares/
│   ├── trace_id.py                  自动生成 / 透传 X-Trace-Id
│   ├── error_handler.py             DomainError + PydanticValidationError 统一封装
│   ├── auth.py                      SSO(dev.bypass token)+ require_user/admin
│   ├── sso_adapter.py
│   └── rate_limit.py                Redis 滑窗限流
│
├── models/
│   ├── mysql/                       16 张 ORM(见 §2.2 表清单)
│   └── mongo/                       RunStepDetail / SandboxTrace TypedDicts
│
├── schemas/                         Pydantic v2 DTO(tool / meta_template / graph / run / common)
│
├── repositories/
│   ├── base.py                      SqlRepoBase
│   ├── user_repo.py                 UserRepo + SqlUserRepo / AdminRepo + SqlAdminRepo
│   ├── app_setting_repo.py
│   ├── audit_repo.py
│   ├── tool_repo.py                 SqlToolRepo(create/update/fork/activate)
│   ├── graph_repo.py                SqlGraphRepo
│   ├── graph_version_repo.py
│   ├── graph_draft_repo.py
│   ├── event_log_repo.py            ★ SqlEventLogStore(DB-first event stream)
│   ├── json_case_repo.py            SqlJsonCaseRepo
│   ├── run_repo.py                  ★ SqlWorkflowRunRepo(create/update_status/heartbeat)
│   └── review_repo.py(ABC,待 Ch10 实装)
│
├── services/
│   ├── tool_service.py              policy 层:权限 / scope=private 强制 llm / simulator 注册校验
│   ├── meta_template_service.py     元模板单例读写
│   ├── forest_parser.py             freeze_snapshot(async)+ parse_readonly(sync)
│   ├── design_validator.py          聚合 9 个 Visitor,产出 ValidationReport
│   └── graph_service.py             Create/SaveVersion/Diff/Draft
│
├── tool_runtime/                    ★ 节点模板解释器子系统
│   ├── base.py                      ToolSimulator 抽象 + tool_name ClassVar
│   ├── errors.py
│   ├── factory.py                   SimulatorFactory(engine 路由)
│   ├── loader.py                    DB → NodeTemplate 值对象
│   ├── registry.py                  ToolRegistry(LRU 512 + TTL 300s + Redis pub/sub)
│   ├── json_parser.py               definition dict → DTO
│   ├── json_schema.py               jsonschema 包装(validate_input/output)
│   ├── prompt_builder.py            Jinja + fields → system/user prompt
│   ├── cross_validator.py           Ch09 沙箱后完善
│   └── simulators/
│       ├── __init__.py              ★ SIMULATOR_REGISTRY 自动扫描 pure_python/
│       ├── common.py                get_required / coerce_int / effective_mask
│       ├── llm_generic.py           LLMSimulator(engine=llm 共用)
│       ├── hybrid.py                HybridSimulator(primary + fallback)
│       └── pure_python/
│           └── index_table_lookup.py ★ 唯一示例模板(作 SOP 范本)
│
├── llm/                             ★ LLM 适配层(Strategy + Decorator + Factory)
│   ├── errors.py                    TransientLLMError / LLMUnavailable / ...
│   ├── types.py                     LLMRequest / LLMResponse / ToolSpec / Message / ...
│   ├── provider.py                  LLMProvider Protocol
│   ├── adapters/{claude,openai,mock}.py
│   ├── decorators/{retry,trace,metrics,rate_limit,timeout}.py
│   ├── schema_coerce.py             output_schema 强制 + 自修复
│   ├── agent_loop.py                ★ tool-call 多轮原语(给 Phase1 Handler 2 用)
│   └── client.py                    LLMClient 门面(装饰器链 + call_sync 桥接)
│
├── langgraph/                       ★ Pipeline 骨架
│   ├── state.py                     re-export CascadeState
│   ├── events.py                    ★ EventType Enum + priority_order + RunEventBus(DB-first)
│   ├── trace_sink.py                TraceSink(Mongo)+ ToolCallTraceContext
│   ├── run_step_store.py            ★ RunStepStore Protocol + SqlRunStepStore + Noop(仅测试)
│   ├── router.py                    PhaseRouter(纯 routing,state 变更在 finalize 节点)
│   ├── pipeline.py                  PipelineBuilder(接 checkpointer)+ PipelineVariant
│   ├── runtime.py                   ★ WorkflowRuntime(DB 状态转换 + heartbeat + stop 监控)
│   ├── errors.py                    StepFailed / WorkflowTimeout / ...
│   └── steps/
│       ├── __init__.py              ★ STEP_REGISTRY 自动扫描 phase1/2/3 + phase_end
│       ├── base.py                  BasePipelineStep(模板方法)+ HandlerStep(Phase1 责任链)
│       ├── factory.py               PipelineStepFactory + StepDeps(depends_on 注入)
│       ├── phase_end.py             Finalize 节点(_phase1_end_valid/invalid 等)
│       ├── phase1/
│       │   ├── base.py              Phase1HandlerBase
│       │   ├── structure_check.py   ★ Handler 1(纯 Python,调 DesignValidator)
│       │   ├── prompt.py            森林 → 系统 prompt
│       │   ├── executor.py          ToolUseRequest → ToolSimulator 路由
│       │   ├── comparator.py        deep_equal + diff_report(字段级精确对比)
│       │   ├── attribution.py       失败归因(LLM 辅助)
│       │   └── scenario_run.py     ★ Handler 2(LLM 驱动森林执行)
│       ├── phase2/                  code_planner / code_generator / code_assembler(骨架)
│       └── phase3/                  6 个 step 骨架
│
├── api/                             FastAPI 路由
│   ├── health.py                    /healthz + /readyz(DB/Mongo/Redis 检查)
│   ├── metrics.py                   /metrics(Prometheus)
│   ├── node_templates.py            /api/node-templates(前端投影)
│   ├── admin_tools.py               /api/admin/node-templates(完整 CRUD + simulate)
│   ├── admin_meta_template.py       /api/admin/meta-node-template
│   ├── graphs.py                    /api/graphs + /versions + /draft + /_validate + /_diff
│   └── run_events.py                ★ /api/runs/{id}/events + /stop + /owner(分布式)
│
├── utils/                           ids / clock / hash / sanitize
└── cli/                             migrate / init_mongo_indexes / grant_admin / verify_simulators
```

### 2.2 DB Schema(MySQL,19 表)

| 表 | 用途 | 关键列 |
|---|---|---|
| `t_migration_applied` | DDL 迁移追踪 | `file_name PK / checksum` |
| `t_user` / `t_admin_user` | 用户 + admin 白名单 | `external_id` unique |
| `t_meta_node_template` | 元模板(单例 id=1) | `content JSON`(字段定义) |
| `t_node_template` / `_version` | 节点模板 + 版本快照 | `scope / status / current_version_id` |
| `t_cascade_graph` | 图元信息 | `owner_id / latest_version_id / status` |
| `t_graph_version` | 图版本(大 JSON snapshot) | `snapshot JSON / parent_version_id` |
| `t_graph_draft` | 草稿(每图一条) | `snapshot / saved_by` |
| `t_workflow_run` | Run 主表 | `status / phase1..3_verdict / final_verdict / worker_id / heartbeat_at` ★ |
| `t_run_step` | Step 摘要(每步一行) | `phase / node_name / status / mongo_ref` |
| `t_json_case` | Phase1 场景(input / expected / actual / verdict) | ★ 必填 |
| `t_sandbox_case` | Phase3 沙箱用例 |  |
| `t_code_snapshot` | Phase2 代码快照 |  |
| `t_graph_review` / `t_review_comment` | Review |  |
| `t_audit_log` | 审计(action / target / result) |  |
| `t_app_setting` | 动态配置 k-v |  |
| `t_run_event_log` | ★ Run 事件流(DB-first,resume 基础) | `id BIGINT AUTO_INCREMENT` |

### 2.3 关键设计模式

| 模式 | 落地点 |
|---|---|
| **Strategy** | `LLMProvider`(Claude/OpenAI/Mock),`SimulatorFactory` 按 engine 路由 |
| **Decorator** | `LLMClient` 装饰器链:Retry→Timeout→Metrics→Trace→RateLimit |
| **Factory** | `PipelineStepFactory`(StepDeps 注入)、`SimulatorFactory`、`build_checkpointer` |
| **Template Method** | `BasePipelineStep.execute`(trace/events/异常包装固化,子类只写 `_do`) |
| **Chain of Responsibility** | Phase1 handlers(按 `handler_order` 排序,pass/fail 路由) |
| **Visitor** | 9 个 `ForestVisitor` 子类独立合作 |
| **Observer** | `RunEventBus`(发事件 → DB 落 + Redis pub/sub + WS 订阅) |
| **Repository** | ABC + Sql* 分离;所有 DB I/O 通过它 |
| **Finite State Machine** | `WorkflowRunSM / RunStepSM / Phase1HandlerSM / PlanStepSM` |
| **Auto Registry** | `STEP_REGISTRY`、`SIMULATOR_REGISTRY`(`pkgutil.iter_modules` 自动扫描) |

---

## 3. 前端架构(Vue 3 + TypeScript + Vite)

### 3.1 目录

```
frontend/src/
├── main.ts / App.vue
├── router/index.ts         11 路由
├── types/                  api / forest / run / template(TypeScript 镜像后端 DTO)
├── api/                    分模块 axios:templates / graphs / runs / reviews + client.ts(unwrap)
├── stores/                 Pinia 分资源域:app / graph / templates / runs
├── components/
│   ├── shell/AppShell.vue            TopBar + Sidebar + <RouterView/>
│   ├── ui/                           Button / Tag / Card / FormField / JsonEditor(基础 5 件套)
│   └── canvas/
│       ├── shape_registry.ts         ★ X6 自定义节点注册(NODE_SHAPE + BUNDLE_SHAPE)
│       ├── NodeContent.vue           节点 HTML 渲染(header+body+footer 端口)
│       ├── FieldValueEditor.vue      ★ input_schema 驱动的表单引擎
│       └── useCanvas.ts              ★ CanvasController:graph ⇄ store 双向同步
├── pages/                  11 页:Home / GraphList / CanvasEditor / TemplateLibrary /
│                              TemplateEditor / Scenarios / RunList / RunDetail /
│                              CodeDiff / Review / NoPermission
├── utils/
│   ├── ids.ts              newInstanceId / newEdgeId / newBundleId(uuid4 前 8 位 hex)
│   ├── paste.ts            ★ rebuildIds(对齐后端 paste.rebuild_ids)
│   └── debounce.ts
└── styles/main.css         基于 impl-docs-frontend/assets/common.css
```

### 3.2 关键设计

| 点 | 实现 |
|---|---|
| **画布 OO** | `useCanvas.ts::CanvasController` + `shape_registry.ts`(X6 原生 `Graph.registerNode` 注入自定义 Shape,不污染 X6 内部) |
| **端口动态化** | 每种节点模板 → `edge_semantics[*].field` → 动态 `out:<field>` 端口 group |
| **Bundle 嵌入** | X6 embedding API;drag node → bundle 自动 setParent,释放 forest.node_instances[*].bundle_id |
| **字段表单驱动** | `FieldValueEditor.vue` 读 `NodeTemplateCard.input_schema`,按 type(integer/string/enum/...)渲染,复杂类型 fallback JsonEditor |
| **撤销/重做** | `useGraphStore` 自带 history(上限 50)+ forward;`shallowRef` 防 X6 大对象深度响应开销 |
| **复制粘贴** | `utils/paste.ts::rebuildIds` 对齐后端 `paste.py::rebuild_ids` — 同一份 id 换新规则 |
| **API 层解包** | `unwrap<T>(promise)`:业务直接拿 `T`;`ApiResponse.code != 0` 自动抛错误 |
| **鉴权** | 前端零判断:401/403 响应 → 跳 `/no-permission`;dev 模式自动注入 `Authorization: Bearer dev.<base64>` |
| **实时事件** | `RunDetail.vue` 订阅 `ws://.../ws/runs/:id/events`(Ch11 实装后可用);断线重连从 `/api/runs/:id/events?after_id=N` 补齐 |

---

## 4. K8S 分布式要点(已写入 memory 的铁律)

### 4.1 永远不信任进程内数据

| 状态类型 | 存在哪 | Cascade 落地 |
|---|---|---|
| Run 停止信号 | Redis `cascade:run:stop:{id}` + 本地 1s 缓存 | `app/infra/run_control.py::StopRegistry` |
| 哪个 pod 在跑 Run | Redis `cascade:run:session:{id}` + heartbeat(20s)| `SessionRegistry`(+ DB `t_workflow_run.worker_id/heartbeat_at`)|
| Run 事件流 | `t_run_event_log` DB(source of truth)+ Redis pub/sub(实时)| `SqlEventLogStore + RunEventBus` |
| 限流桶 | Redis 滑动窗口 | `RateLimitMiddleware` |
| LangGraph 中间 state | `CHECKPOINTER_KIND=redis` 时写 Redis;dev 用 MemorySaver | `build_checkpointer(settings)` |
| 模板 / 元模板 | MySQL 主存;**进程内 LRU(cap=512)+ TTL(300s)+ pub/sub invalidate** | `ToolRegistry._LruTtlCache` |
| 动态配置 | MySQL + 10s TTL + pub/sub | `SettingsService` |

### 4.2 分布式 API

- `POST /api/runs/:id/stop` — 任意 pod 触发;实际执行的 pod 最多 20s 内收到并 cancel
- `GET /api/runs/:id/owner` — 运维查 pod 归属
- `GET /api/runs/:id/events?after_id=N` — SSE/WS 断线重连,从 DB resume

### 4.3 所有 Redis 操作强制 `asyncio.wait_for(timeout=2)`

Redis 慢/挂不阻塞心跳。具体见 `ToolRegistry` / `SettingsService` / `StopRegistry` / `SessionRegistry` / `RunEventBus`。

### 4.4 配置

```env
# 生产 K8S 部署必改
APP_ENV=prod
CHECKPOINTER_KIND=redis        # MemorySaver 仅 dev 用,pod 重启丢 state
WORKER_ID=                     # 空则从 HOSTNAME 自动读(K8S Downward API)
REDIS_URL=redis://cascade-redis:6379/0
DATABASE_URL=mysql+asyncmy://...
MONGODB_URL=mongodb://...
```

---

## 5. 数据流:从前端保存图到 Phase1 验证

```
用户在 CanvasEditor 拖节点 / 连边 / 建 bundle
  ├─ useGraphStore mutation → forest JSON 变更(history 栈)
  ├─ 800ms debounce → PUT /api/graphs/:id/draft(持久化草稿)
  ├─ 发布 → POST /api/graphs/:id/versions {snapshot}
  │    ├─ ForestParser.freeze_snapshot → 给每个 node 填 template_snapshot
  │    ├─ DesignValidator(9 visitor)→ ValidationReport
  │    │    ├─ 致命错(cycle / ref invalid 等)→ 422 Reject
  │    │    └─ 轻量错(field_values schema fail)→ 存入 metadata.validation_warnings
  │    └─ INSERT t_graph_version
  └─ 场景页 POST /api/runs {graph_version_id, scenarios, variant}
       ├─ (Ch10 实装)WorkflowFacade 入 t_workflow_run + 预写 t_json_case
       ├─ (Ch11 实装)Celery 任务异步分发到 worker pod
       ├─ worker 实例化 WorkflowRuntime.run():
       │    ├─ create/update t_workflow_run(status=pending→running + worker_id + heartbeat_at)
       │    ├─ SessionRegistry.register → Redis 登记
       │    ├─ emit RUN_STARTED 事件(写 t_run_event_log + Redis publish)
       │    ├─ 启动后台 monitor task:20s 心跳 + stop 检查
       │    ├─ pipeline.ainvoke(state, thread_id=run_id)
       │    │    ├─ Phase1 structure_check(DesignValidator)
       │    │    ├─ Phase1 scenario_run(build_prompt + agent_loop + executor)
       │    │    │    ├─ LLM 驱动,tool_use 调 Simulator(IndexTableLookup 等)
       │    │    │    └─ deep_equal(expected, actual) → pass/fail + 失败归因
       │    │    ├─ 任一 handler fail → _phase1_end_invalid → final=invalid
       │    │    └─ 全 pass → _phase1_bridge → Phase2(Ch08)...
       │    ├─ 终态 FSM 转换 + update t_workflow_run(final_verdict + status)
       │    └─ emit RUN_FINISHED 事件
       └─ 前端订阅 WS(或轮询 /events?after_id=N)实时渲染 trace
```

---

## 6. 节点模板添加 SOP(面向**后续 30+ 节点**)

### 6.1 核心设计:**加节点 0 代码**(LLM 节点)/ **+1 文件**(Python 节点)

| 类型 | 谁能建 | 改代码? |
|---|---|---|
| 私有节点模板(engine=llm) | 设计人员 | ❌ 不用 |
| 全局节点模板(engine=llm) | admin | ❌ 不用 |
| 全局节点模板(engine=pure_python) | admin | ✅ 加 1 个 `ToolSimulator` 子类 |
| 全局节点模板(engine=hybrid) | admin | ✅ 同上(primary + llm fallback) |

### 6.2 LLM 节点(纯数据,零代码)

1. 打开 `/template-editor` → 元模板自动渲染表单(读 `/api/admin/meta-node-template`)
2. 填:`name`(`^[A-Z][A-Za-z0-9_]{2,63}$`)/ `display_name` / `category` / `description[]` / `input_schema` / `output_schema` / `edge_semantics[]` / `code_hints`
3. admin 选 `scope=global`(engine 可选 llm/hybrid);非 admin 强制 `private + engine=llm`
4. `POST /api/admin/node-templates` 或 `POST /api/node-templates`
5. **立即生效**:`ToolRegistry.invalidate(tid)` → Redis pub/sub → 所有 pod 清缓存

### 6.3 pure_python 节点(+1 Python 文件)

```python
# app/tool_runtime/simulators/pure_python/my_tool.py
from time import perf_counter_ns
from app.tool_runtime.base import ToolSimulator
from app.tool_runtime.simulators.common import get_required
from app.domain.run.sim import SimContext, SimResult
from app.domain.tool.tool import Engine


class MyToolSim(ToolSimulator):
    """与节点模板 name 同名;自动注册到 SIMULATOR_REGISTRY。"""

    tool_name = "MyTool"          # == 节点模板 name == python_impl
    engine = Engine.PURE_PYTHON

    def run(self, fields, input_json, ctx: SimContext) -> SimResult:
        t0 = perf_counter_ns()
        (x,) = get_required(input_json, "x")
        # ... 业务逻辑(无状态,无 IO,一切通过 ctx.table_data 注入)
        return SimResult(
            output={"y": x * 2},
            engine_used=self.engine,
            duration_ms=(perf_counter_ns() - t0) // 1_000_000,
        )
```

**然后**:
1. `python -m app.cli verify_simulators` 自检
2. 写单测 `tests/unit/tool_simulators/test_my_tool.py`
3. admin 建对应节点模板(name=`MyTool`,`simulator.engine=pure_python`,`python_impl=MyTool`)
4. 重启 pod **或** `POST /api/admin/node-templates/registry/reload` 热加载

### 6.4 预测:30+ 节点的规模成本

- **数据(定义)**:30 × 平均 150 行 JSON = ~4.5k 行 JSON(不算代码,纯 DB 行)
- **代码(pure_python 模拟器)**:假设 20 个需要 Python 解释器、每个 ~80 行 → **+1600 行**
- **单测**:每 simulator 5-8 个测试 → 20 × 60 行 = **+1200 行**
- **总增量**:~2800 行代码 + JSON 数据,**框架零改动**
- **单 simulator 上线流程**:写类 + 写测试 + `verify_simulators` + admin 建模板 = **约 2 小时 / 个**

### 6.5 加节点时要注意的分布式坑(已预埋)

1. 新建 template 要 `invalidate(tid)` 让其他 pod 清缓存(`ToolService` 已做)
2. `SIMULATOR_REGISTRY` 是进程级只读,所有 pod 都需部署新代码 — 这是 K8S rolling update 的语义,正常
3. 节点模板定义 JSON 不要嵌业务副作用(文件路径 / 外部 URL),所有数据走 `ctx.table_data` 由 Scenario 注入

---

## 7. 测试矩阵

| 层 | 文件 | 测试数 |
|---|---|---|
| domain | `tests/unit/domain/*` | 8 |
| schemas | `tests/unit/schemas/*` | 6 |
| graph(visitor/iterator/dag/paste/forest_parser)| `tests/unit/graph/*` | 19 |
| infra(tracing/middleware/error/auth/metrics/run_control/repo)| `tests/unit/infra/*` | 16 |
| fsm | `tests/unit/fsm/*` | 7 |
| tool_runtime(registry/factory/hybrid/prompt/repo/service/loader)| `tests/unit/tool_runtime/*` | 18 |
| tool_simulators | `tests/unit/tool_simulators/*` | 5 |
| llm(mock/decorators/schema_coerce/agent_loop/client)| `tests/unit/llm/*` | 22 |
| langgraph(pipeline / event_store / runtime_persist)| `tests/unit/langgraph/*` | 11 |
| phase1(comparator / structure_check / executor)| `tests/unit/phase1/*` | 14 |
| utils / orm / healthz / migrate_runner | `tests/unit/test_*.py` | 21 |
| **合计** | | **147 个** |

**缺口**:
- Ch08-11 无文档,未实装 → 暂无对应测试
- Redis 真实连接集成测试(需 docker-compose) → 标记 `@pytest.mark.integration`,CI 跑
- LLM contract test(真 Claude API) → 需 `LLM_API_KEY`,nightly 跑

---

## 8. 已知待办 & 不做清单

### 马上做(Ch08-11 文档补齐后)

| 章 | 交付 |
|---|---|
| 08 Phase2 代码生成 | `code_planner` / `code_generator` / `code_assembler` 真实 LLM 生成 C++ |
| 09 Phase3 沙箱 | `SandboxRuntime` Docker 适配 + 编译 + 执行 + 归因 |
| 10 Service/API 汇总 | `WorkflowFacade`(`POST /api/runs` 端到端)+ RunService + ReviewService + AuditService + authz 责任链 |
| 11 Workers + 实时 | Celery task(`run_workflow` + `archive` + `cleanup`)+ WebSocket gateway(订阅 Redis `run:*:events`)|

### 显式不做(v1)

- 节点模板审批流
- 私有→全局自动提拔
- 节点模板嵌套 Bundle
- 语义缓存(ChatFlow 踩坑已禁用;未来要做只缓存纯知识问答)
- 多模态(图片 / 音频 / 文件产物)— **本项目只管 LLM 文本 + JSON**

---

## 9. K8S 部署建议(未落地,仅文档)

### 9.1 Deployment 拆分

- `cascade-web`(FastAPI):无状态,`replicas: 3+`,rolling update
- `cascade-worker`(Celery 消费 LangGraph Runtime):`replicas: 2+`,preStop 处理优雅停机
- `cascade-redis`:StatefulSet + pvc
- `cascade-mysql`:StatefulSet(或托管 RDS)
- `cascade-mongo`:StatefulSet(或托管)

### 9.2 必须配置

```yaml
env:
  - name: APP_ENV
    value: "prod"
  - name: CHECKPOINTER_KIND
    value: "redis"             # ★ 不设置就是定时炸弹
  - name: AUTH_ENABLED
    value: "true"
  - name: RATE_LIMIT_ENABLED
    value: "true"
  - name: HOSTNAME             # K8S Downward API 自动填
    valueFrom:
      fieldRef:
        fieldPath: metadata.name
readinessProbe:
  httpGet: { path: /readyz, port: 8000 }
livenessProbe:
  httpGet: { path: /healthz, port: 8000 }
```

### 9.3 运维

- Prometheus `scrape` 每个 pod 的 `/metrics`
- 卡死 Run 排查:`SELECT id, worker_id, heartbeat_at FROM t_workflow_run WHERE status='running' AND TIMESTAMPDIFF(SECOND, heartbeat_at, NOW()) > 120;`
- 前端停止 Run:`POST /api/runs/:id/stop`(任意 pod 发)
- 查 Run 在哪 pod:`GET /api/runs/:id/owner`
- 断线重连:`GET /api/runs/:id/events?after_id=<last_seen>`

---

## 10. 变更入口 cheatsheet

| 要做什么 | 改哪里 |
|---|---|
| 加节点模板(LLM,0 代码) | 前端 `/template-editor` 填表单 → `POST /api/node-templates` |
| 加节点模板(pure_python) | `app/tool_runtime/simulators/pure_python/<snake>.py` 一个类 + 测试 |
| 加事件类型 | `app/langgraph/events.py::EventType` + `_PRIORITY_ORDER` |
| 加 DB 字段 | `config/sql/NN.ddl`(递增,不改历史)+ `app/models/mysql/*.py` ORM |
| 加状态机 | `app/domain/fsm/*.py`(新增 SM 子类)+ 业务代码走 FSM.fire |
| 加 Phase1 Handler | `app/langgraph/steps/phase1/<name>.py` 继承 `Phase1HandlerBase`,`handler_order` 决定顺序 |
| 加 Visitor | `app/domain/graph/visitors/<name>.py`,加入 `DesignValidator.run` 编排 |
| 加 API 路由 | `app/api/<topic>.py` + `app/main.py::create_app` 注册 |
| 加前端页 | `frontend/src/pages/*.vue` + `frontend/src/router/index.ts` |
| 加 Pinia store | `frontend/src/stores/*.ts` |
| 加共享组件 | `frontend/src/components/ui/*.vue`(纯 UI)或 `components/canvas/*`(画布相关)|

---

> **文档终。**如果本文与代码不一致,以代码为准。
> memory 系统里的 `feedback_chatflow_rules.md` 和 `feedback_k8s_distributed.md` 是持续性的铁律,每轮必检。
