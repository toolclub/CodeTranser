● 级跳设计平台 v1 — 实施文档项目 · 上下文摘要

  ▎ 作用:整个会话历史的压缩记忆。下次对话只需加载这份摘要 + /workspace/Designer/impl-docs/ 下所有 .md 即可无缝续上。

  ---
  1. 背景与定位

  - 产品:级跳(Cascade)设计平台 v1,后端为主。
  - 原始设计文档:/workspace/Designer/级跳设计平台_设计文档_v5.md(2977 行,作者给定)。
  - 交付目标:把 v5 设计落地到"AI 读文档就能直接写代码"的粒度。约 3 万行代码量。
  - 工作产物:/workspace/Designer/impl-docs/ 目录下 00–07 八份实施文档(约 8963 行)。08–12 暂缓。
  - 12 测试 / 部署 推迟到最后再讨论,先不做。

  ---
  2. 已产出文件清单

  /workspace/Designer/
  ├── 级跳设计平台_设计文档_v5.md                     (原始需求)
  ├── 级跳设计平台_代码实施文档_v1.md                 (第一版 OO + 设计模式骨架,已弃用,被 impl-docs/ 替代)
  └── impl-docs/
      ├── 00_总览与索引.md            446 行
      ├── 01_数据建模.md             1409 行
      ├── 02_基础设施与配置.md        1040 行
      ├── 03_Tool子系统.md           1429 行
      ├── 04_图森林子系统.md         1165 行
      ├── 05_LLM适配层.md            1149 行
      ├── 06_LangGraph骨架.md        1180 行(含 PipelineVariant)
      └── 07_Phase1_JSON层.md        1145 行

  未写:08 Phase2 代码生成 / 09 Phase3 沙箱 / 10 Service 与 API / 11 Workers 与实时 / 12 测试与部署(12 最后再谈)。

  ---
  3. 核心认知共识(会话中经过多轮澄清)

  3.1 前后端分工(关键)

  - 后端 = JSON 仓库 + 节点模板(解释器)目录 + 三阶段验证器
  - 前端 = JSON 画布编辑器(antv,自布局,后端不传 position)
  - "大 JSON" ≈ 写好的代码。用户给输入 + 期望输出,平台用解释器跑一遍判定对不对
  - 前端根本不需要理解 "Tool" 这个概念,只看到节点模板 / 节点实例 / bundle / 森林

  3.2 术语层级(全文统一)

  元模板 Meta Template       单例;t_meta_node_template;admin 可改;不版本化
     ↓ 决定结构
  节点模板 NodeTemplate       = Tool;设计人员按元模板填;版本化快照
     ↓ 实例化
  节点实例 NodeInstance       小节点,对应代码片段;可归属 Bundle 或游离(孤儿允许)
     ↓ 可组合成
  Bundle(节点集/大节点)      对应代码层 class/function;v1 不嵌套;可复用(ctrl-c/v)
     ↑ 但边不连 Bundle
  边 Edge                     全局;src/dst = 任意节点实例(可跨 Bundle)
     ↓ 沿边走 =
  DAG                         视图,不存储;从 root(入度 0 实例)出发沿边走到底
     ↓ 总和 =
  森林 CascadeForest          一张图的完整 JSON;存 t_graph_version.snapshot

  3.3 Phase1 架构(责任链 + LLM 驱动)

  - Phase1 = LangGraph 子图,责任链式多 Handler
  - 每个 Handler 独立、可插拔、按 handler_order 排序,新增不改其他代码
  - v1 两个 Handler:
    a. structure_check(纯 Python,调 DesignValidator)
    b. scenario_run(LLM 驱动,agent_loop + tool-call → 各 ToolSimulator)
  - LLM 双重角色:
    - 单节点解释器(engine=llm 时的 LLMSimulator)
    - 森林驱动者(ScenarioRunHandler 里,主导执行 + 判定)
  - 判定 = 字段级精确对比:{status:ok} ≠ {status:success}
  - 失败时 LLM 归因(design_bug / scenario_bug / simulator_bug / unknown),只写 trace 不改路由
  - 未来 Handler(覆盖率/不变量/覆盖场景合成/规约反思)= 加个类即可

  3.4 三阶段本质

  ┌─────────────────┬──────────────────────────────┬────────────────┐
  │      阶段       │           用什么跑           │    验证对象    │
  ├─────────────────┼──────────────────────────────┼────────────────┤
  │ Phase1 JSON 层  │ 解释器(ToolSimulator),软件级 │ 设计对不对     │
  ├─────────────────┼──────────────────────────────┼────────────────┤
  │ Phase2 代码生成 │ LLM + 代码工件组装           │ (产出)         │
  ├─────────────────┼──────────────────────────────┼────────────────┤
  │ Phase3 沙箱     │ 编译器 + 真实机器,硬件级     │ 代码实现对不对 │
  └─────────────────┴──────────────────────────────┴────────────────┘

  3.5 Pipeline 多图(06 章末)

  关键决策:不是所有 Run 都跑三阶段。

  - PipelineVariant.PHASE1_ONLY — 只做设计验证
  - PipelineVariant.UP_TO_PHASE2 — 设计验证 + 代码生成(不编译)
  - PipelineVariant.FULL — 完整三阶段

  PipelineBuilder.get(variant) 按需构造、缓存;WorkflowRuntime.run(..., variant=);RunTriggerDTO.variant 暴露给前端。

  3.6 代码生成层级绑定(08 章按此开写)

  ┌───────────────────┬─────────────────────────────────────────────┐
  │     森林元素      │                   代码层                    │
  ├───────────────────┼─────────────────────────────────────────────┤
  │ Bundle            │ class/function(unit)                        │
  ├───────────────────┼─────────────────────────────────────────────┤
  │ Bundle 里节点实例 │ 被内联的代码片段                            │
  ├───────────────────┼─────────────────────────────────────────────┤
  │ 游离节点实例      │ 独立片段(v1 由 08 章定:内联 main / 独立 fn) │
  ├───────────────────┼─────────────────────────────────────────────┤
  │ Edge              │ 类 / 方法间调用                             │
  └───────────────────┴─────────────────────────────────────────────┘

  Tool 定义里没有 granularity 字段——粒度由结构决定。

  ---
  4. 会话中的关键决策(回答用 "DECISIONS" 开关)

  ┌─────┬─────────────────────────────┬──────────────────────────────────────────────────────────────────────┐
  │  #  │             问              │                                  答                                  │
  ├─────┼─────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 1   │ DB 迁移方式                 │ 去掉 alembic;config/sql/NN.ddl 纯 SQL 文件 + runner(已写,见 01 §1.3) │
  ├─────┼─────────────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 2   │ 种子 YAML                   │ 去掉 seed 概念;admin 通过 UI/API 直接建节点模板                                      │
  ├─────┼─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ 3   │ 节点模板定义格式            │ JSON(不要 YAML);description 用字符串数组,后端 "\n".join                              │
  ├─────┼─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ 4   │ Tool code_hints.granularity │ 去掉;粒度由"节点实例在 Bundle 里 / 游离"决定                                         │
  ├─────┼─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ 5   │ 游离小节点                  │ 允许(代码层 = 独立代码片段)                                                          │
  ├─────┼─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ 6   │ Bundle 嵌套                 │ v1 不嵌套                                                                            │
  ├─────┼─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
  │ 7   │ Bundle 跨图复用             │ v1 支持 ctrl-c/v(前端负责重发 id,后端有 app/domain/graph/paste.py::rebuild_ids 工具)       │
  ├─────┼─────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 8   │ 节点模板创建权限            │ 设计人员建私有(强制 engine=llm);admin 建全局(engine 任意);不审批                           │
  ├─────┼─────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 9   │ 元模板                      │ 独立表 t_meta_node_template,预置在 01.ddl,admin 可改,不版本化,单例                         │
  ├─────┼─────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 10  │ 所有表前缀                  │ t_                                                                                         │
  ├─────┼─────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
  ├─────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 11  │ 英文                      │ 节点集 = bundle                                                                                                │
  ├─────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 12  │ ID 前缀                   │ u_ / tpl_ / tpv_ / g_ / gv_ / bnd_ / n_ / e_ / r_ / s_ / jc_ / sc_ / cs_ / rv_ / cm_ / al_                     │
  ├─────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 13  │ 森林 JSON 结构            │ { bundles:[], node_instances:[], edges:[], metadata:{} };不含 position                                         │
  ├─────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 14  │ DAG 是否存储              │ 不存储,计算视图(DagComputeVisitor)                                                                             │
  ├─────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 15  │ Pipeline 多图             │ 三种 variant(PHASE1_ONLY / UP_TO_PHASE2 / FULL)                                                                │
  ├─────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 16  │ Tool/节点模板前端暴露     │ 前端只看 NodeTemplateCardDTO(/api/node-templates);完整 NodeTemplateOutDTO 只给                                 │
  │     │                           │ admin(/api/admin/node-templates);完整 t_node_template 概念前端 0 感知                                          │
  ├─────┼───────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ 17  │ 12 测试/部署              │ 最后再讨论                                                                                                     │
  └─────┴───────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ---
  5. 架构总览(简版)

  ┌─ 前端(antv,大 JSON 编辑器)──────────────────────────────┐
  │  拉 /api/node-templates + 元模板渲染节点库               │
  │  画布 = 节点实例 + bundle + 边  →  ForestSnapshotDTO      │
  │  PUT draft / POST versions / POST runs(带 scenarios)     │
  └───────────────────────────┬──────────────────────────────┘
                              ↓
  ┌─ 后端(FastAPI)───────────────────────────────────────────┐
  │  API:graphs / node-templates / admin-tools / meta /     │
  │       runs / reviews / traces                           │
  │  Service:GraphService / ToolService / WorkflowFacade    │
  │  LangGraph:PipelineBuilder → 三种 variant 图             │
  │    Phase1:structure_check → scenario_run(LLM driver)    │
  │    Phase2:code_planner → code_generator → code_assembler│
  │    Phase3:static → compile → scenario → exec → dynamic  │
  │  Runtime:ToolRegistry + LLMClient + SandboxPool        │
  │  Storage:MySQL(t_*) + MongoDB(run_step_details /      │
  │                                sandbox_traces) + Redis  │
  │  迁移:config/sql/NN.ddl + app/infra/migrate/runner.py   │
  └───────────────────────────────────────────────────────────┘

  ---
  6. 目录结构速查(后端)

  backend/
  ├── app/
  │   ├── bootstrap.py           DI 组合根(唯一 new XxxImpl 的地方)
  │   ├── config.py              Settings(pydantic-settings)
  │   ├── main.py                FastAPI 入口
  │   ├── domain/                纯模型(禁 import fastapi/sqlalchemy/redis)
  │   │   ├── tool/tool.py       NodeTemplate 值对象
  │   │   ├── graph/             nodes(Bundle/NodeInstance/Edge/CascadeForest) / visitor / iteration / dag_compute / builders / paste
  │   │   └── run/               state(CascadeState)/ sim / scenario
  │   ├── schemas/               pydantic DTO
  │   ├── models/mysql/          SQLAlchemy ORM(只做 CRUD,不建表)
  │   ├── models/mongo/          TypedDict
  │   ├── infra/                 db / mongo / redis / logging / tracing / metrics / migrate
  │   ├── middlewares/           auth / trace_id / error_handler / rate_limit
  │   ├── repositories/          各 Repo(抽象 + SQL 实现)
  │   ├── tool_runtime/          ToolSimulator / Factory / Registry / Loader / json_parser / prompt_builder / json_schema / simulators/
  │   ├── llm/                   provider / adapters(claude/openai/mock) / decorators / client / agent_loop / schema_coerce
  │   ├── langgraph/             steps/(base/phase1/phase2/phase3) + pipeline / router / events / trace_sink / runtime
  │   ├── services/              tool_service / meta_template_service / graph_service / forest_parser / design_validator / (+10 章) workflow_facade /
  run_service / review_service 等
  │   ├── api/                   各路由
  │   ├── realtime/              WS gateway(11 章)
  │   ├── workers/               Celery(11 章)
  │   ├── cli/                   migrate / init_mongo_indexes / verify_simulators / grant_admin
  │   └── utils/                 ids / clock / hash / sanitize
  ├── config/sql/                01.ddl(已给完整 SQL)、后续 02.ddl...
  ├── tests/
  ├── pyproject.toml
  └── Dockerfile

  ---
  7. 已完成章节速览(给 AI 下次读什么)

  - 00_总览:整体索引 + ID 体系 + 阶段验收 + §0.12 共识(术语层级 / 代码生成层级 / Pipeline variant)
  - 01_数据建模:config/sql/01.ddl 全 SQL(16+2 表 + 元模板预置) + runner + 值对象 + DTO + 异常 + CascadeState
  - 02_基础设施:Settings / 日志 / trace_id / 中间件 / session / redis / Mongo / Metrics / AppContainer / cli migrate
  - 03_节点模板子系统:ToolSimulator 抽象 + Registry + Factory + Loader + json_parser + 示例 IndexTableLookup + 元模板 Service + 三套路由 + 作者 SOP
  - 04_图森林子系统:Bundle/NodeInstance/Edge/CascadeForest + 9 个 Visitor + TopologicalIterator + DagComputeVisitor + ForestParser + DesignValidator +
  GraphService + API + paste.rebuild_ids
  - 05_LLM 适配层:LLMProvider + Claude/OpenAI/Mock + 5 个装饰器 + schema_coerce + agent_loop(Phase1 Handler 2 用) + LLMClient.call_sync 桥接
  - 06_LangGraph 骨架:BasePipelineStep(模板方法) + HandlerStep(Phase1 责任链基类) + STEP_REGISTRY 自动扫描 + PipelineStepFactory(depends_on 注入) +
  PhaseRouter + §6.10 PipelineBuilder / PipelineVariant(多图)+ WorkflowRuntime + RunEventBus + TraceSink
  - 07_Phase1 JSON 层:structure_check + scenario_run + prompt(按 bundle + 游离 + 全局边 + 模板说明)+ executor(全局查 instance + 返回 outgoing_edges 含
  dst_bundle)+ comparator(deep_equal + diff_report)+ attribution(LLM 归因)+ Scenario / ScenarioResult / JsonCaseRepo

  ---
  8. 待办(下次继续)

  马上做

  - 08_Phase2 代码生成:code_planner / code_generator / code_assembler;CodeArtifact
  组合(CodeFragment/CodeUnit/CompositeCode);EdgeMapper;CompositeCodeBuilder;Bundle → class/function 的 prompt 模板;游离节点处理策略待本章定
  - 09_Phase3 沙箱:SandboxRuntime 适配器(Docker/gVisor/Kata)+ SandboxPool(对象池)+ SandboxCommand(CompileCommand/TestRunCommand)+ SandboxFacade(门面)+
  outer_static/dynamic_reflector + outer_scenario_synthesizer
  - 10_Service 与 API:WorkflowFacade(唯一对外触发入口)+ RunService + ReviewService + TraceService + AuditService + 鉴权责任链 + 所有 REST 路由汇总
  - 11_Workers 与实时:Celery 配置(run_workflow / archive / cleanup)+ WebSocket gateway + Redis pub/sub 订阅转发

  最后做

  - 12_测试与部署:测试策略、Dockerfile、compose / K8s、CI、Runbook

  残留回扫提示

  - 01 章 §1.4 森林 JSON 的 position 字段已删;如果后续 08 章发现代码生成需要 name / label 之类的 UI hint,放 bundle.description 或
  node_instance.instance_name,不要再加 position 字段
  - 06 章 PhaseRouter.after_phase1_handler 和 after_code_assembler 签名已改成接 variant= 参数——后续 Router 新方法照同样约定
  - 03 章 API 拆成三套(/api/admin/node-templates / /api/node-templates / /api/admin/meta-node-template),10 章做鉴权责任链时要按这个拆分写 require_admin /
   require_user

  ---
  9. 下次加载提示词(可直接粘给新对话)

  ▎ 接着上次会话继续。上下文在 /workspace/Designer/impl-docs/ 所有 md 文件里。本轮已完成 00-07 + 06 的 PipelineVariant 改造(约 8963 行文档)。下一步是写
  ▎ 08 Phase2 代码生成,按 07 章相同的详细度(prompt / executor / 值对象 / step / 测试 / 交付清单)。代码生成的层级绑定约定:Bundle → class/function、Bundle
  ▎ 里节点实例 → 内联代码片段、游离节点 → v1 由 08 章裁定、Edge → 调用/跳转。所有表 t_ 前缀,所有 DDL 走 config/sql/NN.ddl,节点模板定义用 JSON(description
  ▎  字符串数组),无 position 字段。其他共识见 00 章 §0.12。

  ---
  10. 前端原型(2026-04-18 追加)

  - 产出目录:/workspace/CodeTranser/Designer/impl-docs-frontend/
  - 栈定型:Vue 3 + Pinia + Vite + antv X6(非 VueFlow,否决了 §25.11 的选型)
  - 前端不做鉴权,所有权限判断走后端 @require_admin / @require_user 装饰器;前端收 401 跳登录、403 跳 no-permission.html。
  - 高保真原型(直接浏览器打开),11 个页面 + 共享 CSS:
      * index.html              导航(入口)
      * pages/graph-list.html   CascadeGraph 列表
      * pages/canvas-editor.html 画布编辑器 · 真实 antv X6 CDN 交互
      * pages/template-library.html 节点模板库
      * pages/template-editor.html  元模板驱动表单 + JSON 实时预览
      * pages/scenarios.html    input / expected JSON 两列编辑器
      * pages/run-list.html     Run 列表
      * pages/run-detail.html   三阶段时间线 + LLM 驱动对话 + trace
      * pages/code-diff.html    多文件 unified diff
      * pages/review.html       画布上钉评论 · 线程 · 批准
      * pages/no-permission.html 401/403/404/500 兜底
  - 后续如果要落到真实 Vue 代码:按页面切分 components/ + pages/ 即可,原型是视觉契约。

  ---
  摘要终。保留这份 + impl-docs 所有 md + impl-docs-frontend/ 所有 html = 上下文完整恢复。