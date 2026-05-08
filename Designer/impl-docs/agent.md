# D3A 代码仓库 AI 辅助参考 (顶层 agent.md)

> 此文档面向：**AI 辅助工具（Claude Code / Cursor / Copilot）与新协作者**。
>
> 用法：把本文件作为 system 提示，让 AI 写代码前先理解全仓的目录边界。
>
> 范围：本文件**只列代码目录与用途**。每个 owner 的分工边界另起文档（不在此处）。
>
> 单一事实源：`D3A顶层模块级设计文档.md` §2.1（81 模块清单）+ §10.2（聚合根映射）。本文件的目录与模块编号一一对齐，编号即模块编号。

---

## 1. 仓库总分层（先看这张图）

```
L0 Edge（接入层）             web/  +  src/d3a/application/api_gateway,websocket_pusher
    │
L2 Application（应用层）      src/d3a/application/   8 个具名模块（含 saga 编排、worker、幂等）
    │
L1 Domain（业务限界上下文）   src/d3a/{meta_template, command, edge, graph,
    │                                  execution, phase1, phase2, phase3, review}/
    │                          9 个 BC，共 54 个领域模块；每个 BC 内部统一为
    │                          domain/ → ports/ → application/ → infrastructure/ → api/
    │
    └── 模板通用承载体        src/d3a/_template_base/  5 个共享代码骨架（被 MetaTemplate / Command / Edge 实例化）
    │
L3 Integration（抗腐层）      src/d3a/integration/   7 个具名模块（LLM 5 + sandbox + d3a-codegen-target）
    │
L4 Cross-Cutting（横切）      src/d3a/crosscutting/  7 个具名模块（正交维度，任意层可引用）
    │
L5 Infrastructure（基础设施） src/d3a/infrastructure/ 5 个具名模块（实现 Domain 层定义的 Port ABC）
```

**模块总数**：81 = Domain 54（承载体 5 + MetaTemplate 1 + Command 5 + Edge 2 + Graph 13 + Execution 6 + Phase1 7 + Phase2 5 + Phase3 7 + Review 3）+ Application 8 + Integration 7 + Cross-Cutting 7 + Infrastructure 5。

**每个 BC 的内部目录是同构的**：`domain/` → `ports/` → `application/` → `infrastructure/` → `api/`。
后面的目录树里非首次出现时简写为 `（与 meta_template 同构）`。

---

### 1.1 关于 `_template_base/`（共享内核 Shared Kernel，**特例**）

`_template_base/` 不是 BC，是 DDD 里的 **Shared Kernel**——MetaTemplate / Command / Edge 三个 BC 之间有大量结构共性（都是带 IO schema 的模板、都要注册表+缓存、都要冻结快照、都要权限矩阵），把这些共性抽成一份，三个 BC 各自继承 / 实例化（详见顶层文档 §3.1 引言）：

```
_template_base/                    整体属于 Domain 层（共享内核）
   ├── definition/      ┐
   ├── registry/        │  抽象类 + 协议 + 默认实现
   ├── simulator_base/  │  
   ├── library_base/    │  
   └── schema_engine/   ┘  
                              ↓ 被以下三个 BC 各自继承 / 实例化
   meta_template/  command/  edge/   ← 这三个 BC 才有完整的
                                       domain/ports/application/infrastructure/api 五层
```

**为什么 `_template_base/` 没有 `domain/` 子目录**：因为整个包**就是** domain 层，不存在自己的 application / infrastructure / api 层——那些层归实例化它的具体 BC。再套一层空 `domain/` 是冗余。

**唯一例外**：`registry/` 与 `library_base/` 内置默认缓存与权限实现，会通过 Port 注入 `infrastructure/redis_pubsub/` 等基础设施。这是共享内核的合理折中——避免三个 BC 各写一份缓存逻辑——但 Redis 等具体技术仍由 Adapter 注入，没破规矩。

---

## 2. 完整目录树（**只列目录，不列文件**；末位编号 = §2.1 模块编号）

```
D3A/
├── src/
│   └── d3a/                                    # Python 主代码包
│       │
│       ├── _template_base/                     # 模板通用承载体（**Shared Kernel，详见 §1.1**；不是 BC，整体属于 Domain 层；故无 domain/ports/application/api 五层结构）
│       │   ├── definition/                     # 1.1 node-definition：NodeTemplate 聚合根抽象 + 哈希 + 冻结快照
│       │   ├── registry/                       # 1.2 node-registry：模板注册表 + 进程 LRU + Redis 二级缓存 + Scope 解析
│       │   ├── simulator_base/                 # 1.3 node-simulator：NodeSimulator ABC（Pure / LLM / Hybrid）
│       │   ├── library_base/                   # 1.4 node-library：模板库管理 + 权限矩阵 + 导入导出
│       │   └── schema_engine/                  # 1.5 schema-engine：JSON Schema (Draft 2020-12) 校验 + 兼容性 + 规范化
│       │
│       ├── meta_template/                      # MetaTemplate BC（1 个；详见 §10.6）
│       │   ├── domain/
│       │   │   └── meta_template/              # 2.1 meta-template：EnumType / ValueType / CompositeType / VariableSlot 聚合
│       │   ├── ports/                          # MetaTemplateRepositoryPort 等
│       │   ├── application/                    # 类型字典管理用例
│       │   ├── infrastructure/                 # 适配器：mysql-store / redis-pubsub
│       │   └── api/                            # /api/v1/meta-templates REST
│       │
│       ├── command/                            # Command BC（5 个；详见 §10.7 / §10.10 / §10.19）
│       │   ├── domain/
│       │   │   ├── template_engine/            # 3.1 command-template-engine：CommandTemplate 聚合根 + 版本 + 属性树
│       │   │   ├── template_registry/          # 3.2 command-template-registry：聚合查询路径（实例化 1.2 承载体）
│       │   │   ├── template_library/           # 3.3 command-template-library：库管理 + 官方包种子
│       │   │   ├── property_evaluator/         # 3.4 command-property-evaluator：表达式 DSL 解释器（option / type_option）
│       │   │   └── simulator/                  # 3.5 command-simulator：实现 1.3 NodeSimulator
│       │   └── ...                             # （ports / application / infrastructure / api 同构）
│       │
│       ├── edge/                               # Edge BC（2 个；详见 §10.8 / §10.19）
│       │   ├── domain/
│       │   │   ├── edge_template/              # 4.1 edge-template：EdgeTemplate 聚合根 + 语义约束
│       │   │   └── edge_resolver/              # 4.2 edge-resolver：边实例化 / 语义匹配 (shared lib)
│       │   └── ...                             # （与 meta_template 同构）
│       │
│       ├── graph/                              # Graph BC（13 个；详见 §10.9 / §10.11–§10.13 / §10.19）
│       │   ├── domain/
│       │   │   ├── forest/                     # Forest 子族（6 个）
│       │   │   │   ├── structure/              # 5.1 forest-structure：CascadeForest 不可变数据结构
│       │   │   │   ├── snapshot/               # 5.2 forest-snapshot：Graph / GraphVersion 聚合根 + 版本化
│       │   │   │   ├── snapshot_builder/       # 5.3 forest-snapshot-builder：原始 JSON → 解析模板 → 冻结 snapshot
│       │   │   │   ├── template_library/       # 5.4 forest-template-library：森林模板库（与命令模板库不同）
│       │   │   │   ├── diff/                   # 5.5 forest-diff：版本 Diff（按 Bundle / DAG）
│       │   │   │   └── visitor/                # 5.6 forest-visitor：Visitor 框架 + 内置校验器
│       │   │   ├── dag/                        # 5.7 dag-compute：拓扑 / 环检测 / DagView 派生（shared lib）
│       │   │   ├── cascade/                    # 5.8 cascade-validator：级联规则校验（shared lib）
│       │   │   ├── impact/                     # 5.9 template-impact-analyzer：模板变更影响面索引
│       │   │   └── simulator/                  # 模拟器子系统（4 个；§10.19）
│       │   │       ├── cascade_sim/            # 5.10 cascade-simulator
│       │   │       ├── dag_runner/             # 5.11 dag-runner
│       │   │       ├── bundle_sim/             # 5.12 bundle-simulator
│       │   │       └── forest_runner/          # 5.13 forest-runner
│       │   ├── ports/                          # ★GraphRepositoryPort / ★TemplateUsageIndexPort 等
│       │   ├── application/
│       │   ├── infrastructure/                 # mysql-store / redis-pubsub Adapter
│       │   └── api/                            # /api/v1/graphs REST + /ws/* WebSocket
│       │
│       ├── execution/                          # Execution BC（6 个）
│       │   ├── domain/
│       │   │   ├── validation_run/             # 6.1 validation-run：ValidationRun 聚合根（§7.1）
│       │   │   ├── codegen_run/                # 6.2 codegen-run：CodegenRun 聚合根（§7.1b）
│       │   │   ├── phase_state_machine/        # 6.3 phase-state-machine：Phase 调度状态机（shared lib）
│       │   │   ├── cascade_state/              # 6.4 cascade-state：跨 Phase 级联状态
│       │   │   ├── run_step/                   # 6.5 run-step：步级日志 + Trace（接 mongo-trace）
│       │   │   └── cancellation/               # 6.6 cancellation：取消信号广播
│       │   └── ...                             # （与 meta_template 同构）
│       │
│       ├── phase1/                             # Phase1 BC（7 个；JSON 验证 + 反思）
│       │   ├── domain/
│       │   │   ├── structure_check/            # 7.1 structure-check：图结构校验（用 forest-visitor）
│       │   │   ├── scenario_engine/            # 7.2 scenario-engine：场景生成与执行
│       │   │   ├── scenario_comparator/        # 7.3 scenario-comparator：场景结果对比（shared lib）
│       │   │   ├── failure_attribution/        # 7.4 failure-attribution：失败归因
│       │   │   ├── handler_chain/              # 7.5 handler-chain：可扩展 Handler 流水线（shared lib）
│       │   │   ├── reflector/                  # 7.6 phase1-reflector：反思循环（§7.13）
│       │   │   └── changeset/                  # 7.7 changeset：ChangeSet 聚合根 + content-hash 去重
│       │   └── ...
│       │
│       ├── phase2/                             # Phase2 BC（5 个；代码生成）
│       │   ├── domain/
│       │   │   ├── code_planner/               # 8.1 code-planner：生成计划（按 DAG 拓扑切批）
│       │   │   ├── code_generator/             # 8.2 code-generator：调 LLM 出代码片段
│       │   │   ├── code_assembler/             # 8.3 code-assembler：拼装片段为目标产物
│       │   │   ├── code_snapshot/              # 8.4 code-snapshot：CodeSnapshot 聚合根
│       │   │   └── codegen_target/             # 8.5 codegen-target：CodegenTarget 抽象基类（shared lib；具体实现见 12.7）
│       │   └── ...
│       │
│       ├── phase3/                             # Phase3 BC（7 个；沙箱验证）
│       │   ├── domain/
│       │   │   ├── static_reflector/           # 9.1 static-reflector：静态分析 + LLM 反思
│       │   │   ├── sandbox_provisioner/        # 9.2 sandbox-provisioner：沙箱容器配置
│       │   │   ├── sandbox_compiler/           # 9.3 sandbox-compiler：在沙箱里编译
│       │   │   ├── sandbox_executor/           # 9.4 sandbox-executor：在沙箱里执行
│       │   │   ├── case_synthesizer/           # 9.5 case-synthesizer：用例合成
│       │   │   ├── dynamic_reflector/          # 9.6 dynamic-reflector：动态结果反思
│       │   │   └── fix_loop_controller/        # 9.7 fix-loop-controller：外层修复循环（§7.5）
│       │   └── ...
│       │
│       ├── review/                             # Review BC（3 个）
│       │   ├── domain/
│       │   │   ├── submission/                 # 10.1 submission：Submission 聚合根（§7.9c）
│       │   │   ├── review_workflow/            # 10.2 review-workflow：Review 聚合根（§7.9）
│       │   │   └── review_comment/             # 10.3 review-comment：ReviewComment 聚合根
│       │   └── ...
│       │
│       ├── application/                        # L2 Application（8 个；含 saga 编排）
│       │   ├── api_gateway/                    # 11.1 api-gateway：REST 路由（72 条）+ DTO + 鉴权 + 限流
│       │   ├── websocket_pusher/               # 11.2 websocket-pusher：WS 实时推送（4 条 ws 路由）
│       │   ├── worker_runtime/                 # 11.3 worker-runtime：Celery 队列 / Worker 启动 / Phase 调度
│       │   ├── pipeline_builder/               # 11.4 pipeline-builder：**LangGraph DAG 构造**（Phase 流编排在此）
│       │   ├── pipeline_orchestrator/          # 11.5 pipeline-orchestrator：Saga 编排（VR↔CR、ChangeSet apply、Submission approval）
│       │   ├── idempotency/                    # 11.6 idempotency：幂等键存储与去重
│       │   ├── pipeline_variant/               # 11.7 pipeline-variant：流水线变体（特性开关切流）
│       │   └── forest_promotion_workflow/      # 11.8 forest-promotion-workflow：森林晋升工作流（Review BC 跨界）
│       │
│       ├── integration/                        # L3 Integration（7 个；抗腐层）
│       │   ├── llm/                            # LLM 集成 5 个子模块
│       │   │   ├── provider/                   # 12.1 llm-provider：Claude / OpenAI / 本地模型适配
│       │   │   ├── tool_use/                   # 12.2 llm-tool-use：函数调用封装
│       │   │   ├── output_schema/              # 12.3 llm-output-schema：强制 schema 输出（接 schema-engine）
│       │   │   ├── prompt_cache/               # 12.4 llm-prompt-cache：Prompt 缓存（Redis）
│       │   │   └── agent_loop/                 # 12.5 llm-agent-loop：Agent 循环（思考 + 工具 + 反思）
│       │   ├── sandbox_runtime/                # 12.6 sandbox-runtime：沙箱运行时抽象（接 docker-driver）
│       │   └── d3a_codegen_target/             # 12.7 d3a-codegen-target：D3A → C/C++ 实现（实现 8.5 抽象）
│       │
│       ├── crosscutting/                       # L4 Cross-Cutting（7 个；正交维度）
│       │   ├── trace_bus/                      # 13.1 trace-bus：trace 收集与广播（mongo-trace + redis-pubsub）
│       │   ├── metrics/                        # 13.2 metrics：Prometheus 指标
│       │   ├── audit_log/                      # 13.3 audit-log：操作流水
│       │   ├── auth_rbac/                      # 13.4 auth-rbac：鉴权 / RBAC / 多租户
│       │   ├── feature_flag/                   # 13.5 feature-flag：特性开关（灰度发布）
│       │   ├── secret_vault/                   # 13.6 secret-vault：敏感凭证（env / KMS）
│       │   └── llm_cost_governor/              # 13.7 llm-cost-governor：LLM 配额与成本
│       │
│       ├── infrastructure/                     # L5 Infrastructure（5 个；实现 Domain Port）
│       │   ├── mysql_store/                    # 14.1 mysql-store：SQLAlchemy 仓储实现 + 事务 + 多库路由
│       │   ├── mongo_trace/                    # 14.2 mongo-trace：motor 客户端 + Trace 写入
│       │   ├── redis_pubsub/                   # 14.3 redis-pubsub：redis-py 客户端 + Pub/Sub + 锁
│       │   ├── docker_driver/                  # 14.4 docker-driver：Docker SDK 封装（被 sandbox-runtime 用）
│       │   └── schema_migration/               # 14.5 schema-migration：alembic 迁移触发（CLI + Cron 单例）
│       │
│       └── cli/                                # 命令行：d3a-cli（运维 / 数据导入导出 / 调试）
│
├── prompts/                                    # **Prompt 资产库**：与 Python 解耦，独立版本化
│   ├── phase1/                                 # Phase1 prompt（按 skill 组织）
│   ├── phase2/                                 # Phase2 prompt
│   ├── phase3/                                 # Phase3 prompt
│   ├── shared/                                 # 跨 phase 共享片段
│   └── golden_sets/                            # 黄金评测集（输入 + 期望输出对，回归用）
│
├── templates/                                  # **代码生成模板**：被 phase2 / phase3 emitter 调用
│   ├── cpp_emitters/                           # C++ 目标模板
│   ├── c_emitters/                             # C 目标模板
│   └── tests/                                  # 生成代码配套测试样板
│
├── migrations/                                 # alembic 单一时间线（由 14.5 schema-migration 驱动）
│   └── versions/                               # 所有 BC 共用一条版本线，编号统一收口避免冲突
│
├── web/                                        # **前端**（独立 pnpm workspace）
│   ├── src/
│   │   ├── components/                         # 通用组件库
│   │   ├── features/                           # 按业务切：forest-canvas / template-library / review / simulator-timeline
│   │   ├── api/                                # 后端 API 客户端（由 contracts/openapi 自动生成）
│   │   ├── stores/                             # 状态管理
│   │   ├── pages/                              # 页面路由 + 顶层布局
│   │   └── styles/                             # 主题 / 全局样式
│   ├── public/
│   └── tests/                                  # 单元 + Playwright e2e
│
├── contracts/                                  # **跨服务契约**：BC 间硬接口，前后端共享
│   ├── openapi/                                # api-gateway 暴露的 yaml（前端代码生成器读这里）
│   ├── events/                                 # 领域事件 JSON Schema（参考 §11.5 事件总表）
│   └── ws/                                     # WebSocket 协议定义
│
├── tests/                                      # **后端测试根目录**：按层切，按 BC 分子目录
│   ├── unit/                                   # 单元测试：domain + application 纯逻辑（不接外部）
│   │   ├── _template_base/
│   │   ├── meta_template/
│   │   ├── command/
│   │   ├── edge/
│   │   ├── graph/
│   │   ├── execution/
│   │   ├── phase1/
│   │   ├── phase2/
│   │   ├── phase3/
│   │   └── review/
│   ├── integration/                            # 集成测试：testcontainers 起真实 MySQL/Redis/Mongo
│   │   └── ...                                 # （按 BC 与上同构）
│   └── e2e/                                    # 端到端：跨 BC 全链路（QA Lead 维护）
│
├── deploy/                                     # 部署
│   ├── docker/                                 # docker-compose（本地 + 测试）
│   ├── helm/                                   # K8s helm chart（生产）
│   └── terraform/                              # 云资源（如适用）
│
├── scripts/                                    # 工具脚本：起服 / 数据导入 / 一次性运维
│
├── docs/                                       # **对外文档**：用户 / 运维 / 接入方读
│   ├── user_guide/
│   ├── admin/
│   └── api/                                    # 由 contracts/openapi 生成的对外 API 文档
│
└── impl-docs/                                  # **内部设计与实施文档**：团队内部读
    ├── D3A顶层模块级设计文档.md                 # 81 模块业务总图（已存在）
    ├── D3A研发分工与实施计划.md                 # 6 人分工表（已存在）
    ├── agent.md                                # 本文件（顶层）
    ├── P1_template_domain/                     # 各 owner 的 spec / impl / agent / prototype 四件套
    ├── P2_graph/                               # （已存在，作为标杆样本）
    ├── P3_execution/
    ├── P4_langgraph_phases/
    ├── P5_platform/
    └── P6_frontend/
```

---

## 3. BC 内部分层约定（每个 `<bc>/` 都长这样）

```
<bc>/
├── domain/                # 领域层：聚合根 / 实体 / 值对象 / 领域服务 / 领域事件；纯 Python，无外部 IO
├── ports/                 # 端口（Protocol/ABC）：领域定义的对外接口，不含实现
├── application/           # 应用层：用例编排（命令/查询服务、DTO、Saga 起点）；只组合，不写业务规则
├── infrastructure/        # 基础设施适配器：实现 ports/，调 mysql-store / redis-pubsub / mongo-trace
└── api/                   # 驱动适配器：FastAPI 路由 + Pydantic schema + WebSocket
```

> 多模块的 BC（如 graph 13、phase1 7、execution 6）在 `domain/` 下用**子目录**承载每个模块（与 §2.1 编号对齐）。
> 单模块的 BC（如 meta_template 1）也保留 `domain/<module_name>/` 一层，便于将来扩展。

---

## 4. 关键分层规矩（AI 写代码前必读）

| 规矩 | 说明 |
|---|---|
| **BC 内部分层** | `domain/` 不允许 `import sqlalchemy / motor / redis / docker / fastapi / httpx`；`application/` 只能 import `domain/` 与 `ports/`；`infrastructure/` 实现 `ports/` |
| **跨 BC 协作** | 仅通过对方 `ports/readonly/` 或事件总线（trace-bus / outbox），不允许 `from d3a.<bc>.domain import ...` |
| **跨 BC 引用对象** | 只持 `(id, version)`，不持对象；保存森林时由 forest-snapshot-builder 把命令模板等冻结为 inline snapshot |
| **LangGraph 编排归属** | LangGraph DAG 构造在 `application/pipeline_builder/`，**不在** Phase BC 内；Phase BC 提供领域逻辑被编排 |
| **Saga 编排归属** | 跨聚合写场景一律走 `application/pipeline_orchestrator/` + Outbox，不在 Worker 内存里 if/else |
| **Cross-Cutting 是正交维度** | 任何层都可引用 `crosscutting/`；`crosscutting/` 不得反向依赖业务 BC |
| **Integration 是抗腐层（ACL）** | 领域代码**不允许**直接 `import anthropic / openai / docker`，必须通过 `integration/llm/*` 与 `integration/sandbox_runtime/` |
| **Domain 只定义 Port** | `mysql-store / mongo-trace / redis-pubsub / docker-driver` 是 Port 的实现，由 DI 注入；Domain 代码 import 的是 Port ABC |
| **DDL 单一时间线** | 所有 alembic 脚本进 `migrations/versions/` 共用一条线，由 14.5 `schema-migration` 单例触发 |
| **Prompt 资产** | 不放 Python 包内，放 `prompts/`，独立版本化；改动必过 `prompts/golden_sets/` 回归 |
| **代码生成模板** | 不放 Python 包内，放 `templates/`，被 `phase2 / phase3` emitter 调用 |
| **codegen-target 双层结构** | 抽象基类在 `phase2/domain/codegen_target/`（8.5）；D3A 具体实现在 `integration/d3a_codegen_target/`（12.7） |

---

## 5. AI 写代码时的常见反模式（**禁止**）

| 反模式 | 正确做法 |
|---|---|
| 在 `<bc>/domain/` 里 `import sqlalchemy / motor / redis / docker / fastapi` | 这些只能进 `<bc>/infrastructure/` 或 `infrastructure/` |
| 让聚合根直接持有另一个 BC 的实体对象 | 只持 `(id, version)`，必要时通过 `ports/readonly/` 拿快照 |
| 在 `application/` 写业务规则（if 校验、状态机分支） | 业务规则归 `domain/`，application 只编排 |
| 在 BC 里重复实现鉴权 / 审计 / 限流 / 特性开关 / 成本治理 | 一律走 `crosscutting/` 装饰器或中间件 |
| 把 prompt 字符串 hardcode 在 `phase*/domain/` 里 | 写到 `prompts/<phase>/`，由加载器读取 |
| 在 Phase BC 内自己拼 LangGraph DAG | LangGraph 拼装归 `application/pipeline_builder/`；Phase BC 暴露领域服务被调 |
| 在 Worker 里内存 if/else 协调跨聚合写 | 跨聚合写一律走 `application/pipeline_orchestrator/` Saga + Outbox |
| 直接 `import anthropic / openai / docker` SDK | 走 `integration/llm/*` 或 `integration/sandbox_runtime/` 抗腐层 |
| 直接修改另一个 BC 的表 / migration | 改自己 BC 对应的 migration；编号由 14.5 schema-migration 单例收口 |
| 在 `api/` 路由里序列化领域聚合根直接返回 | 用 `application/dtos/` 转换后由 `api/schemas/` Pydantic 输出 |
| 在 NodeSimulator 实例上保存状态 | NodeSimulator 必须无状态，所有上下文走 `SimContext` 注入 |

---

## 6. 新协作者 5 分钟上手路径

1. 读 `D3A顶层模块级设计文档.md` §1.2（架构分层）+ §1.3（BC 总览）+ §10.2（聚合根映射）
2. 看本文件第 1 节的总分层图 + 第 2 节目录树
3. 找到自己负责的目录，进对应 `impl-docs/<owner>/` 读 spec / impl / agent / prototype
4. 跑 `deploy/docker/docker-compose.dev.yml` 起本地环境（MySQL + MongoDB + Redis + Docker Daemon）
5. 在自己 BC 目录下从 `domain/` 写起，遇到 IO → 走 `ports/`，遇到外部技术 → 落 `infrastructure/` 或走 `integration/`
