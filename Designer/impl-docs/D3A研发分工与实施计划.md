# D3A 研发分工与实施计划

> 配套主文档：`D3A顶层模块级设计文档.md`
>
> **6 人 + AI 辅助**。每人在自己模块包内全栈包办：实施文档 + 代码 + 单元测试。

| 负责人 | 模块包 | §2.1 模块清单 | 实施文档 | 代码路径 | 单元测试 |
|---|---|---|---|---|---|
| **P1**：xx | 模板与命令域（通用承载体 + MetaTemplate + Command + Edge） | 1.1–1.5 + 2.1 + 3.1–3.5 + 4.1–4.2 | `P1_template_domain_impl.md` | `src/d3a/_template_base/`、`src/d3a/meta_template/`、`src/d3a/command/`、`src/d3a/edge/` | `tests/unit/template_domain/`，覆盖率 ≥80% |
| **P2**：xx | Graph 全栈（Forest / DAG / Visitor / 模拟器） | 5.1–5.13 | `P2_graph_impl.md` | `src/d3a/graph/`（含 forest / dag / simulator 子包） | `tests/unit/graph/`，覆盖率 ≥80% |
| **P3**：xx | 执行编排链（Execution + Review + Saga + 应用层网关） | 6.1–6.6 + 10.1–10.3 + 11.1–11.8 | `P3_execution_impl.md` | `src/d3a/execution/`、`src/d3a/review/`、`src/d3a/application/` | `tests/unit/execution/`，覆盖率 ≥80% |
| **P4**：xx | LangGraph + Phase1/2/3 + LLM 集成（Prompt 主导） | 7.1–7.7 + 8.1–8.5 + 9.1–9.7 + 12.1–12.5 | `P4_langgraph_phases_impl.md` | `src/d3a/phase1/`、`src/d3a/phase2/`、`src/d3a/phase3/`、`src/d3a/integration/llm/` + `prompts/` + `templates/cpp_emitters/` | `tests/unit/phases/` + Prompt 黄金集 |
| **P5**：xx | 平台底座（沙箱 + d3a-codegen-target + 横切 + 基础设施 + DDL/Migration） | 12.6–12.7 + 13.1–13.7 + 14.1–14.5 | `P5_platform_impl.md` | `src/d3a/integration/sandbox/`、`src/d3a/integration/codegen_target/`、`src/d3a/crosscutting/`、`src/d3a/infrastructure/`、`migrations/` | `tests/unit/platform/`，覆盖率 ≥80% |
| **P6**：xx | 前端（森林画布 / 模板库 / 评审 UI） | 全部前端 + §10.14 编辑器契约 | `P6_frontend_impl.md` | `web/` | 组件单测 + Playwright E2E |

---

## AI 辅助约定

- 每位 owner 预留 30% 工时给"调 AI + 评审 AI 输出"

- AI 起草实施文档 / 代码骨架 / 单测样板；**人评审与定稿不可省**

- 关键决策（DDL 字段、状态机、Port 签名、API 契约）**人先有结论再让 AI 编码**

- Prompt 类产物（仅 P4）**必过黄金集回归**才能上线

  
