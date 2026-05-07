# D3A 研发分工与实施计划

> 配套主文档：`D3A顶层模块级设计文档.md`（已完成，作为"总")。
>
> **分工模型**：每个负责人在自己负责的模块包里**全栈包办** —— 写本模块详细设计文档、实施文档、代码、单元测试与自验收。**人人是架构师，也是程序员**。本文按"总 → 分 → 总"组织。
>
> **团队规模**：5–6 人 + AI 辅助（Claude Code / Cursor / Copilot 全员配套）。本文以 **6 人方案**为基准；缺人时按下方"5 人压缩方案"合并 P5/P6。
>
> **AI 辅助约定**：每位负责人交付的设计文档 / 实施文档 / 代码 / 单测均由 AI 辅助起草，**人工评审与定稿不可省**。AI 不替代评审、不替代关键决策、不替代联调。

---

## 一、总：项目启动（已完成 + 待补）

| # | 任务 | 状态 | 实施人 | 产出物 |
|---|---|---|---|---|
| 0.1 | PRD 撰写（用户角色 / 用例 / KPI / 业务边界） | **待补** | xx（产品 / PM） | `D3A_PRD.md` |
| 0.2 | 顶层模块级设计文档 | 已完成 | xx（架构师） | `D3A顶层模块级设计文档.md` |
| 0.3 | PRD + 顶层文档联评（产品 / 架构 / 业务方 / 后端 Lead / Prompt Lead） | 待启动 | xx（PM 召集） | 评审纪要 |

> **进入"分"阶段的前提**：PRD 评审通过 + 顶层文档联评通过。

---

## 二、分：模块级单兵作战分工

### 每位负责人的固定交付清单

每行**一位负责人**，对自己负责的模块包**端到端负责**以下 5 件事：

1. **模块详细设计文档**（`<owner>_<bc>_design.md`）—— 在顶层文档之下展开：包结构、聚合根 / 实体 / 值对象类清单、Port 接口、DDL / migration、API 契约、状态机细节、测试策略
2. **实施文档**（`<owner>_<bc>_impl.md`）—— 开发顺序、依赖前置、接入方式、配置项、本地起服方式、对接点 mock
3. **代码**（`src/d3a/<bc>/` 全部 Python 文件）
4. **单元测试**（≥80% 覆盖率）+ **本模块集成测试**（接真实 DB / Redis）
5. **自验收**（提交评审清单 + Demo 录屏 / 演示）

### 主分工表（6 人方案）

| 负责人 | 模块包覆盖 | §2.1 模块清单 | 设计文档 | 实施文档 | 代码路径 | 测试范围 |
|---|---|---|---|---|---|---|
| **P1**：xx | 模板与命令域（通用承载体 + MetaTemplate + Command + Edge）| 1.1-1.5 + 2.1 + 3.1-3.5 + 4.1-4.2 | `P1_template_domain_design.md` | `P1_template_domain_impl.md` | `src/d3a/_template_base/`、`src/d3a/meta_template/`、`src/d3a/command/`、`src/d3a/edge/` | 单测 + 三个模板 BC 内集成 |
| **P2**：xx | Graph 全栈（Forest 子域 + DAG/Visitor + 模拟器子系统） | 5.1-5.13 | `P2_graph_design.md` | `P2_graph_impl.md` | `src/d3a/graph/`（含 forest / dag / simulator 子包） | 单测 + 模拟器端到端 + 跨 BC 集成（依赖 P1） |
| **P3**：xx | 执行编排链（Execution + Review + Saga 编排 + 应用层网关） | 6.1-6.6 + 10.1-10.3 + 11.1-11.8 | `P3_execution_design.md` | `P3_execution_impl.md` | `src/d3a/execution/`、`src/d3a/review/`、`src/d3a/application/` | 单测 + Saga 中断恢复 + Submission 全链路冒烟 |
| **P4**：xx | LangGraph + Phase1/2/3 + LLM 集成（Prompt 主导） | 7.1-7.7 + 8.1-8.5 + 9.1-9.7 + 12.1-12.5 | `P4_langgraph_phases_design.md` | `P4_langgraph_phases_impl.md` | `src/d3a/phase1/`、`src/d3a/phase2/`、`src/d3a/phase3/`、`src/d3a/integration/llm/` + `prompts/` + `templates/cpp_emitters/` | Prompt 评测集 + 沙箱编译通过率 |
| **P5**：xx | 平台底座（沙箱 + d3a-codegen-target + 横切 + 基础设施 + DDL/Migration） | 12.6-12.7 + 13.1-13.7 + 14.1-14.5 | `P5_platform_design.md` | `P5_platform_impl.md` | `src/d3a/integration/sandbox/`、`src/d3a/integration/codegen_target/`、`src/d3a/crosscutting/`、`src/d3a/infrastructure/`、`migrations/` | 适配器单测 + 沙箱启停 + DDL 落库回归 |
| **P6**：xx | 前端（森林画布 / 模板库 / 评审 UI） + 编辑器后端契约联调 | 全部前端 + §10.14 编辑器契约 | `P6_frontend_design.md` | `P6_frontend_impl.md` | `web/` | 组件单测 + Playwright E2E |

> **6 人方案** 角色定位：
> - **P1 模板域**：负责所有"模板"概念的代码骨架——这是后端最深的领域，AI 辅助下一个人能扛
> - **P2 Graph 全栈**：森林 / DAG / 模拟器是 D3A 数据模型的核心，需要熟悉 DDD 与算法
> - **P3 执行编排**：Execution + Review + Saga + 网关是"应用层粘合剂"，工作量大但偏工程化
> - **P4 LangGraph 与 Prompt**：**项目核心瓶颈**，最适合 AI 协作（让 AI 帮调 AI），需要业务专家配合
> - **P5 平台底座**：偏 DevOps + 后端基础组件；E5/E6 全部 + 沙箱 + DDL 收口
> - **P6 前端**：单独一人；如果工作量饱满可独立到底，否则后期帮忙 P3 / P5
>
> **5 人压缩方案**：去掉 P6，前端工作合并到 P5，前端组件由 AI 主力生成、P5 负责评审与对接。但这要求 P5 有前端基础。
>
> **架构师 / 业务专家 / 产品 / QA / DevOps Lead** 角色按需挂在多人头上（轮值），不单独占人头。
>
> **协作约定**：跨包协作（如 P2 依赖 P1）通过**接口契约 + 桩 mock** 解耦——P2 不等 P1 落地，先按 P1 暴露的 Port ABC 写 mock 跑单测。

### 每个负责人的内部交付节奏（标准模板）

| 内部里程碑 | 交付物 | 验收人 |
|---|---|---|
| M1 | 设计文档 v1（评审稿） | 架构师 + 邻接 BC 负责人 |
| M2 | 实施文档 v1 + 接口 mock + DDL migration（如有） | 架构师 + DBA（如有 DDL） |
| M3 | 核心聚合根 / 值对象 / 领域服务代码 + 单测 | 自验 + Code Review |
| M4 | Port 实现（Repo / Cache）+ 集成测试 | 邻接 BC 负责人联调 |
| M5 | API / 事件订阅接入 + 端到端冒烟（自己范围内） | 测试 + 架构师 |
| M6 | 自验收 Demo + 提测 | 测试 / QA |

---

## 三、总：集成与上线

> 各模块负责人 M5 完成后进入此阶段；不再按模块拆，按链路拆。

### G 集成阶段

| # | 任务 | 实施人 | 产出物 |
|---|---|---|---|
| G1 | 跨 BC 集成测试矩阵执行（A↔B↔C↔D↔E 主链路） | xx（QA Lead） + 各模块负责人值班 | 集成测试报告 |
| G2 | e2e：1 棵真实 forest → Phase1 → Phase2 → Phase3 → 出 C/C++ 代码 → 沙箱跑通 | xx（QA） + xx（业务专家） | e2e 报告 + 黄金用例 |
| G3 | Prompt 黄金集回归（D1 / D2 / D3 输出稳定性） | xx（Prompt Lead）+ D1-D3 负责人 | 评测报告 |
| G4 | 性能与并发（10 个并发 Run / Phase 各自 SLA） | xx（QA） | 性能报告 |
| G5 | 故障演练（DB 宕 / Redis 宕 / Worker 崩 / LLM 超时 / 沙箱挂） | xx（QA + DevOps） | 演练报告 |
| G6 | 安全扫描（沙箱逃逸 / 表达式 DSL 沙箱 / SQL 注入 / RBAC） | xx（安全） | 安全报告 |

### H 部署上线

| # | 任务 | 实施人 | 串/并 | 产出物 |
|---|---|---|---|---|
| H1 | 单机测试环境部署：docker-compose 一键起 | xx（DevOps） | 串 | `docker-compose.test.yml` + 起服文档 |
| H2 | 种子数据导入（官方 MetaTemplate / Command 包 / 演示 forest） | xx（业务专家 + A1/A2） | 串 | seed 包 |
| H3 | UAT（业务专家上手实操） | xx（产品 + 业务专家） | 串 | UAT 纪要 |
| H4 | 集群部署：K8s manifests / Helm chart / 主从 DB / Redis Cluster / Mongo 副本集 | xx（DevOps + DBA） | 串 | helm chart |
| H5 | 监控告警接入（Prometheus / Grafana / 告警规则 / 日志聚合） | xx（SRE） | 并（与 H4） | 监控看板 |
| H6 | 灰度发布（5% → 20% → 100%；feature-flag 控制） | xx（DevOps + 产品） | 串 | 灰度报告 |
| H7 | 全量上线 + 上线 Review + 7 天稳定性观察 | 全员 | 串 | 上线报告 |

---

## 四、附：协作与文档规范

### 文档命名

- 模块详细设计：`<owner>_<bc>_design.md`，放 `impl-docs/` 下
- 实施文档：`<owner>_<bc>_impl.md`，放 `impl-docs/` 下
- 全部模块设计文档统一在 `impl-docs/INDEX.md` 维护索引

### 文档"分"层级的内容要求（与顶层文档的关系）

| 层级 | 文档 | 谁写 | 内容粒度 |
|---|---|---|---|
| **总（开局）** | `D3A_PRD.md` | 产品 | 用户故事 / 用例 / 范围 / KPI |
| **总（开局）** | `D3A顶层模块级设计文档.md` | 架构师（已完成） | 81 个模块清单 / DDD 分包 / 状态机 / DDL / 跨 BC 关系 |
| **分** | `xx_<bc>_design.md` | 模块负责人 | 在自己包内：聚合根类设计、Port 接口签名、DDL 字段细节、状态机分支、错误码 |
| **分** | `xx_<bc>_impl.md` | 模块负责人 | 开发顺序、本地启动方式、配置项、依赖前置、Mock 提供方式 |
| **总（收口）** | 集成测试报告 / e2e 报告 / 部署文档 | QA / DevOps | 跨链路 |

### 跨负责人协作约定

- **接口先行**：上游负责人（如 A1 MetaTemplate）**M1 设计文档评审通过后**，先把 Port ABC 与 DTO 提到主仓 → 下游（如 A2 Command）拿着 ABC 写 mock 即可并行
- **DDL 评审统一**：所有 migration 脚本由 P5 平台底座负责人统一收口、统一 alembic 编号，避免冲突
- **跨包集成**：在 M4 阶段双方联调；联调通过算双方 M4 完成
- **不允许**：跨 BC 直接持对象引用、跨 BC 修改对方表、绕过 Port 直接 import infra 模块

### 评审节奏

- 每周一次"分"组例会：P1-P6 各 5 分钟同步进度 + 阻塞项
- 每位负责人 M1（设计）必经过**架构师评审 + 邻接包负责人会签**（如 P2 设计需 P1 / P3 评论）
- 每位负责人 M6（自验收）必经过 QA 评审

---

## 五、AI 辅助使用约定（人均配套）

每位负责人在自己模块包内的标准工作流：

| 阶段 | AI 干什么 | 人干什么 |
|---|---|---|
| 模块设计文档 | 起草大纲；按顶层文档与 §10 业务模型自动产出聚合根类清单 / DDL / API 草案 | **评审业务边界、字段语义、DDL 索引取舍**；最终拍板 |
| 实施文档 | 起草开发顺序 / 起服步骤 / 配置项清单 | 校对依赖前置是否真实可达，删除虚假依赖 |
| 代码（聚合根 / VO / 服务） | 按设计文档生成 Python 类骨架 + dataclass + Port 接口 + 单测样板 | **领域规则、状态机分支、并发约束** 必须人写，AI 只生成纯模板代码 |
| 代码（Repository / Adapter） | 起草 SQL / Redis 调用样板、ORM 映射、错误处理 | 校对事务边界、异常路径、回滚语义 |
| 单元测试 | 按方法签名生成测试样板与 fixture | 补 AI 想不到的边界 / 并发 / 异常场景 |
| Prompt（仅 P4）| 起草 prompt 草稿与评测集样本 | 黄金答案、业务正确性判定、回归基线 |
| Code Review | 给出修改建议 | **最终 approve 必须人** |

**铁律**：
- AI 生成的代码 **必须经人审，不得直接合 main**
- 关键决策（DDL 字段、状态机、Port 签名、对外 API 契约）**人必须先有结论再让 AI 编码**
- AI 生成的提示词 **必须过黄金集回归**才能上线

---

## 六、关键依赖与瓶颈

```
PRD (待补) ──┐
            ├─→ P1-P6 各启动 M1
顶层文档 ────┘

P1（模板域：承载体+Meta+Cmd+Edge）─┐
                                  ├──→ P2（Graph 全栈）──┐
                                  │                       │
P5（平台底座：DDL+infra）─────────┘                       │
                                                          │
P3（Execution+Review+Saga+网关）──┬───────────────────────┤
                                  │                       │
P4（LangGraph+Phase1/2/3+LLM）────┘                       │
                                                          │
                                                          ▼
                                                       G 集成 → H 部署
P6（前端）── 与 P3 联调（编辑器抽屉/悬浮 API）────→ G2 e2e
```

**主路径瓶颈**（任何一个延迟整体延迟）：
- **P5（DDL/Migration）** 最先必须落地，否则 P1-P4 都没表写
- **P1（承载体 + Command）** 阻塞 P2、P3、P4 全部下游
- **P2（Graph 全栈）** 是最重的一个包，建议给经验最足的人；可借 AI 生成大量样板
- **P4（Prompt-heavy）** 调优周期最长，**M1 设计 + 评测集必须最早启动**，与 P1/P2 并行而不是等
- **P6（前端）** 与 P3 联调（编辑器后端契约）容易卡住，需要 P3 早期就给出 OpenAPI Mock

---

## 七、实施人填写指引

> 把所有 `xx` 替换成具体姓名 / 工号即可。建议规则：
>
> - **6 人方案推荐分配**：
>   - P1 模板域 → 后端最深、对 DDD 概念熟悉的同学
>   - P2 Graph 全栈 → 对图算法 / 数据结构有经验的同学（最重的包）
>   - P3 执行编排 → 对分布式系统、saga、消息队列熟悉
>   - P4 LangGraph + Prompt → 提示词工程 / LLM 经验最足；项目核心
>   - P5 平台底座 → DevOps 倾向 + 写过适配器
>   - P6 前端 → 前端工程师；如果只 5 人则去掉，前端由 P5 兼
> - **架构师 / 业务专家 / 产品** 不占人头，按需挂在多个负责人头上轮值
> - **AI 辅助预算**：每位 owner 预留 30% 工时给"调 AI + 评审 AI 输出"，不是省下来去做别的
