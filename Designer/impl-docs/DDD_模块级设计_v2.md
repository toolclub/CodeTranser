# DDD 模块级设计文档 v3

> **版本**: v3.0 **状态**: 设计稿，等待评审 **作者**: Architecture Team **创建日期**: 2026-04-27 **替代**: v2.0（保留作为对比参考）
>
> ------
>
> **v3 相对于 v2 的关键变化：**
>
> 1. **修正模块计数**：从标称"35"修正为实际 **52 个模块**（6 层），消除标题与清单不一致
> 2. **API 网关路由补全**：从 14 条扩展为 **54 条完整路由**，覆盖所有域的 CRUD + 管理 + WebSocket
> 3. **修正架构分层违例**：Cross-Cutting 改为正交维度（非层级）；Domain 层依赖倒置（Repository ABC + DI）
> 4. **CascadeState 语义修正**：明确为"可变执行上下文"（非值对象），引入 Copy-on-Phase 策略和体积控制
> 5. **新增状态机联动总图**（§8.0）：13 个状态机之间的驱动关系一目了然
> 6. **新增 LLM 成本控制模块**（llm-cost-ctrl）：Token 预算、模型选择策略、Provider Fallback
> 7. **Review 域重新定位**：明确触发时机、与 GraphVersion 的关系、自动/手动模式
> 8. **领域事件总表补全**：从 33 个扩展为 **52 个**，与各模块设计完全对齐
> 9. **错误码补全**：从 14 个扩展为 **48 个**，覆盖所有域
> 10. **新增 Phase1 reflection-loop 模块**：SDD/TDD 反思循环有明确归属
> 11. **修复 GraphVersion VALIDATED 语义**：拆分为 `PHASE1_PASSED` 与 `FULLY_VALIDATED`
> 12. **idempotency 模块归属修正**：从 Domain 层移至 Application 层
> 13. **状态机从 12 个增至 13 个**：新增 Phase1 Reflection Loop 状态机

------

## 目录

- [第 1 章 顶层架构与分布式视图](#第-1-章-顶层架构与分布式视图)
- [第 2 章 模块清单（52 个模块）](#第-2-章-模块清单52-个模块)
- [第 3 章 Node/Graph 域模块详细设计](#第-3-章-nodegraph-域模块详细设计)
- [第 4 章 Execution/Phase1 域模块详细设计](#第-4-章-executionphase1-域模块详细设计)
- [第 5 章 Phase2/Phase3/Review 域模块详细设计](#第-5-章-phase2phase3review-域模块详细设计)
- [第 6 章 应用层详细设计（含完整 API 路由）](#第-6-章-应用层详细设计含完整-api-路由)
- [第 7 章 集成层 / 横切关注点 / 基础设施](#第-7-章-集成层--横切关注点--基础设施)
- [第 8 章 13 个状态机完整规约](#第-8-章-13-个状态机完整规约)
- [第 9 章 分布式与可靠性设计](#第-9-章-分布式与可靠性设计)
- [第 10 章 扩展性机制](#第-10-章-扩展性机制)
- [第 11 章 TBD（D3A 留白）与迁移路径](#第-11-章-tbdd3a-留白与迁移路径)
- [附录 A 术语表](#附录-a-术语表)
- [附录 B 错误码总表（48 个）](#附录-b-错误码总表48-个)
- [附录 C 领域事件总表（52 个）](#附录-c-领域事件总表52-个)
- [附录 D v2→v3 变更记录](#附录-d-v2v3-变更记录)

------

## 第 1 章 顶层架构与分布式视图

### 1.1 设计目标与非功能需求

| 维度         | 目标                                                         | 量化指标（参考）                          |
| ------------ | ------------------------------------------------------------ | ----------------------------------------- |
| **可用性**   | 多副本部署，单节点故障不影响服务                             | 99.9%                                     |
| **可扩展性** | 水平扩展 API/Worker；新增 Phase/Handler/Provider 不动核心代码 | 加节点不停机；新插件 ≤200 行代码          |
| **健壮性**   | 任意阶段崩溃可恢复；非法状态转移强制拒绝                     | 每个 Run 可断点续跑                       |
| **一致性**   | Run 状态强一致；图快照不可变                                 | 状态变更通过状态机，乐观锁兜底            |
| **可观测性** | 全链路追踪、指标、审计                                       | trace_id 贯穿、P99 < 2s                   |
| **安全性**   | 多租户隔离；沙箱强隔离；密钥不落盘                           | RBAC、Docker 网络隔离                     |
| **演进能力** | Schema 平滑升级；模板/代码生成目标插件化                     | 同时支持 N-1, N 两版                      |
| **成本可控** | LLM Token 预算管理；按 Phase/Step 选模型                     | 单 Run Token 上限可配；Fallback 切换 < 5s |

### 1.2 架构分层（v3 修正）

> **v3 变更**：Cross-Cutting 不再作为中间"层"，改为正交维度；Domain 层通过 Repository 接口隔离 Infrastructure，遵循依赖倒置。

```
┌─────────────────────────────────────────────────────────┐
│  Edge Layer (边缘层)                                     │
│   外部入口：REST API / WebSocket / Webhook              │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│  Application Layer (应用层)                              │
│   编排领域服务，事务边界，DTO 转换，DI 容器              │
│   api-gateway / websocket-pusher / worker-runtime       │
│   pipeline-builder / pipeline-variant / idempotency     │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│  Domain Layer (领域层)                                   │
│   核心业务逻辑、聚合根、值对象、领域服务、状态机           │
│   tool / graph / execution / phase1 / phase2 /         │
│   phase3 / review                                        │
│                                                          │
│   ★ Domain 只定义 Repository 接口（ABC），不 import       │
│     任何基础设施包（SQLAlchemy/motor/redis/docker）       │
└──────────────────┬──────────────────────────────────────┘
                   │ (通过 DI 注入实现)
┌──────────────────▼──────────────────────────────────────┐
│  Integration Layer (集成层 / 抗腐层 ACL)                 │
│   外部系统适配（LLM / 沙箱），抗腐层                      │
│   llm-provider / llm-tool-use / llm-output-schema /    │
│   llm-prompt-cache / llm-agent-loop / llm-cost-ctrl /  │
│   sandbox-runtime                                        │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│  Infrastructure Layer (基础设施)                         │
│   实现 Domain 定义的 Repository 接口                     │
│   mysql-store / mongo-trace / redis-pubsub /            │
│   docker-driver / schema-migration                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ⊥ Cross-Cutting (正交维度，非层级，任何层可引用)          │
│    trace-bus / metrics / audit-log /                    │
│    auth-rbac / feature-flag / secret-vault              │
└─────────────────────────────────────────────────────────┘
```

### 1.3 限界上下文（Bounded Context）总览

```mermaid
flowchart TB
    subgraph Node["Node BC（节点定义）"]
        TD[node-definition]
        TR[node-registry]
        TS[node-simulator]
        TL[node-library]
        SE[schema-engine]
    end

    subgraph Graph["Graph BC（图结构）"]
        FS[forest-structure]
        FN[forest-snapshot]
        DC[dag-compute]
        FV[forest-visitor]
        FD[forest-diff]
    end

    subgraph Exec["Execution BC（执行编排）"]
        WR[workflow-run]
        PSM[phase-state-machine]
        CS[cascade-state]
        RS[run-step]
        ID[idempotency]
        CC[cancellation]
    end

    subgraph P1["Phase1 BC（JSON 验证）"]
        SC[structure-check]
        SCE[scenario-engine]
        SCM[scenario-comparator]
        FA[failure-attribution]
        HC[handler-chain]
        RL[reflection-loop]
    end

    subgraph P2["Phase2 BC（代码生成）"]
        CP[code-planner]
        CG[code-generator]
        CA[code-assembler]
        CSN[code-snapshot]
        CT[codegen-target]
    end

    subgraph P3["Phase3 BC（沙箱验证）"]
        SR[static-reflector]
        SP[sandbox-provisioner]
        SCC[sandbox-compiler]
        SCX[sandbox-executor]
        CSY[case-synthesizer]
        DR[dynamic-reflector]
        FLC[fix-loop-controller]
    end

    subgraph Rev["Review BC（评审）"]
        RW[review-workflow]
        RC[review-comment]
    end

    Node --> Graph
    Graph --> Exec
    Exec --> P1
    P1 --> P2
    P2 --> P3
    Exec --> Rev
    Node -.读.-> P1
    Node -.读.-> P2
```

### 1.4 分布式部署拓扑

```
                            ┌─────────────────┐
                            │   Load Balancer │ (HAProxy / Nginx)
                            └────┬───────┬────┘
                                 │       │
                ┌────────────────┘       └────────────────┐
                │                                          │
        ┌───────▼──────┐                          ┌───────▼──────┐
        │  API Node 1  │                          │  API Node N  │
        │  (FastAPI)   │  ...  水平扩展  ...      │  (FastAPI)   │
        └──────┬───────┘                          └──────┬───────┘
               │                                          │
               └──────────────────┬───────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────▼────┐              ┌─────▼─────┐            ┌──────▼─────┐
   │ MySQL   │              │  MongoDB  │            │   Redis    │
   │ Primary │◄────同步────►│  Replica  │            │  Cluster   │
   │ +Replica│              │   Set     │            │ (3 master) │
   └─────────┘              └───────────┘            └────┬───────┘
                                                          │
                                                          │ Pub/Sub + Streams
                                                          │
        ┌─────────────────────────────────────────────────┼─────────────────┐
        │                         │                       │                 │
  ┌─────▼──────┐           ┌──────▼──────┐         ┌──────▼──────┐    ┌────▼────┐
  │ Worker 1   │           │ Worker 2    │         │ Worker N    │    │  Cron   │
  │ (Celery)   │           │ (Celery)    │   ...   │ (Celery)    │    │ Beat    │
  │ phase1/2   │           │ phase1/2    │         │ phase3 (沙箱)│    │ (单例)  │
  └─────┬──────┘           └─────┬───────┘         └──────┬──────┘    └─────────┘
        │                        │                        │
        │                        │                        ▼
        │                        │              ┌─────────────────┐
        │                        │              │ Docker Sandbox  │
        │                        │              │  Pool (隔离网络) │
        │                        │              └─────────────────┘
        │                        │
        └────────────────────────┴────────► LLM Provider (Claude / OpenAI)
```

**拓扑要点：**

1. **API 层**：完全无状态；每个节点持有 DB 连接池、Redis 连接池；通过 LB 任意路由。
2. **Worker 层**：分队列部署
   - `phase1_queue`: CPU 密集 + LLM IO，多实例
   - `phase2_queue`: LLM IO 密集，多实例
   - `phase3_queue`: 沙箱密集，需要 Docker Daemon，**仅部署在带 Docker 的节点**
   - `low_priority_queue`: 后台清理、Schema 迁移
3. **状态存储**：
   - MySQL：业务主数据 + 状态字段（用于状态机的乐观锁）
   - MongoDB：trace 与执行明细（写多读少，分片友好）
   - Redis：分布式锁、Pub/Sub、幂等键缓存、限流
4. **领导选举**：Cron Beat、特定后台任务（如孤儿 Run 清理）必须单例运行 → 使用 Redis Redlock 选主
5. **沙箱**：独立的 Worker Pool，每次任务启动一个一次性容器，资源配额 + 网络隔离 + cgroup

### 1.5 模块依赖总图

```mermaid
flowchart LR
    subgraph Edge["Edge"]
        AG[api-gateway]
        WS[websocket-pusher]
    end

    subgraph App["Application"]
        WK[worker-runtime]
        PB[pipeline-builder]
        PV[pipeline-variant]
    end

    subgraph Domain["Domain (只定义接口)"]
        NODE[Node 5个]
        GRAPH[Graph 5个]
        EXEC[Execution 5个]
        P1B[Phase1 6个]
        P2B[Phase2 5个]
        P3B[Phase3 7个]
        REV[Review 2个]
    end

    subgraph Integr["Integration"]
        LLM[LLM 6个]
        SBX[sandbox-runtime]
    end

    subgraph Cross["⊥ Cross-Cutting (正交)"]
        TR[trace-bus]
        MX[metrics]
        AU[audit-log]
        AR[auth-rbac]
        FF[feature-flag]
        SV[secret-vault]
    end

    subgraph Infra["Infrastructure (实现接口)"]
        DB[mysql-store]
        MG[mongo-trace]
        RD[redis-pubsub]
        DK[docker-driver]
        SM[schema-migration]
    end

    AG --> App
    WS --> App
    App --> Domain
    App -.DI注入.-> Infra
    Domain -.接口.-> Infra
    Domain --> Integr
    Integr --> Infra
    Cross -.被任何层引用.-> Domain
    Cross -.被任何层引用.-> App
    Cross -.被任何层引用.-> Integr
    Cross --> Infra
```

**依赖规则（强制）：**

- 上层可依赖下层；下层**不得**依赖上层
- **Domain 层只定义接口**（Repository ABC、Gateway ABC），由 Application 层通过 DI 注入 Infrastructure 实现
- Domain 层代码中**不允许** `import sqlalchemy`、`import motor`、`import redis`、`import docker`
- 同层模块之间**优先通过领域事件解耦**，必要时通过定义良好的接口直接调用
- Cross-Cutting 是正交维度，任何层可引用，但 Cross-Cutting 不得反向依赖业务层
- Integration 层是抗腐层（ACL）：领域代码**不允许**直接 import LLM SDK / Docker SDK

### 1.6 核心交互序列（Run 完整生命周期）

```mermaid
sequenceDiagram
    participant U as User
    participant API as api-gateway
    participant Idem as idempotency
    participant WR as workflow-run
    participant Q as redis-pubsub
    participant W as worker-runtime
    participant PSM as phase-state-machine
    participant P1 as Phase1 BC
    participant P2 as Phase2 BC
    participant P3 as Phase3 BC
    participant TB as trace-bus

    U->>API: POST /runs (idem_key)
    API->>Idem: check_or_register(idem_key)
    Idem-->>API: NEW
    API->>WR: create(graph_version_id)
    WR->>WR: status=pending
    WR-->>API: run_id
    API->>Q: enqueue(run_id)
    API-->>U: 202 Accepted

    Q->>W: dequeue
    W->>WR: load(run_id)
    W->>PSM: transition(pending→running)
    PSM->>TB: emit(RunStarted)

    W->>P1: execute(state)
    P1->>PSM: phase1_started
    P1-->>W: state{phase1_verdict=valid}
    PSM->>TB: emit(Phase1Done)

    W->>P2: execute(state)
    P2-->>W: state{code_units=[...]}
    PSM->>TB: emit(Phase2Done)

    W->>P3: execute(state)
    P3-->>W: state{phase3_verdict=done}
    PSM->>TB: emit(Phase3Done)

    W->>PSM: transition(running→success)
    W->>WR: persist(final_verdict)
    PSM->>TB: emit(RunFinished)
    TB->>Q: publish(run.finished, run_id)
    Q->>API: subscribe
    API->>U: WebSocket push
```

------

## 第 2 章 模块清单（52 个模块）

### 2.1 全模块目录

| #                                                            | 模块                | 层级        | 限界上下文 | 主语言 | 部署单元    | 关键依赖（Port 接口 ★ 标注）            |
| ------------------------------------------------------------ | ------------------- | ----------- | ---------- | ------ | ----------- | --------------------------------------- |
| **L1 Domain — Node（5 个）**                                 |                     |             |            |        |             |                                         |
| 1.1                                                          | node-definition     | Domain      | Node       | Python | API+Worker  | schema-engine                           |
| 1.2                                                          | node-registry       | Domain      | Node       | Python | API+Worker  | ★NodeRegistryPort, ★CachePort           |
| 1.3                                                          | node-simulator      | Domain      | Node       | Python | Worker      | llm-agent-loop                          |
| 1.4                                                          | node-library        | Domain      | Node       | Python | API         | node-definition, auth-rbac              |
| 1.5                                                          | schema-engine       | Domain      | Node       | Python | shared lib  | jsonschema                              |
| **L1 Domain — Graph（5 个）**                                |                     |             |            |        |             |                                         |
| 2.1                                                          | forest-structure    | Domain      | Graph      | Python | API+Worker  | node-registry                           |
| 2.2                                                          | forest-snapshot     | Domain      | Graph      | Python | API+Worker  | ★GraphRepositoryPort                    |
| 2.3                                                          | dag-compute         | Domain      | Graph      | Python | shared lib  | networkx                                |
| 2.4                                                          | forest-visitor      | Domain      | Graph      | Python | shared lib  | -                                       |
| 2.5                                                          | forest-diff         | Domain      | Graph      | Python | API         | dag-compute                             |
| **L1 Domain — Execution（5 个，idempotency 已迁至应用层）**  |                     |             |            |        |             |                                         |
| 3.1                                                          | workflow-run        | Domain      | Execution  | Python | API+Worker  | ★WorkflowRunRepositoryPort              |
| 3.2                                                          | phase-state-machine | Domain      | Execution  | Python | shared lib  | trace-bus                               |
| 3.3                                                          | cascade-state       | Domain      | Execution  | Python | shared lib  | -                                       |
| 3.4                                                          | run-step            | Domain      | Execution  | Python | Worker      | ★RunStepRepositoryPort, ★TraceStorePort |
| 3.5                                                          | cancellation        | Domain      | Execution  | Python | API+Worker  | ★CancellationPort                       |
| **L1 Domain — Phase1（6 个，新增 phase1-reflector）**        |                     |             |            |        |             |                                         |
| 4.1                                                          | structure-check     | Domain      | Phase1     | Python | Worker      | forest-visitor                          |
| 4.2                                                          | scenario-engine     | Domain      | Phase1     | Python | Worker      | node-simulator, llm-agent-loop          |
| 4.3                                                          | scenario-comparator | Domain      | Phase1     | Python | shared lib  | -                                       |
| 4.4                                                          | failure-attribution | Domain      | Phase1     | Python | Worker      | -                                       |
| 4.5                                                          | handler-chain       | Domain      | Phase1     | Python | shared lib  | trace-bus                               |
| 4.6                                                          | phase1-reflector    | Domain      | Phase1     | Python | Worker      | llm-agent-loop, scenario-engine         |
| **L1 Domain — Phase2（5 个）**                               |                     |             |            |        |             |                                         |
| 5.1                                                          | code-planner        | Domain      | Phase2     | Python | Worker      | dag-compute, llm-agent-loop             |
| 5.2                                                          | code-generator      | Domain      | Phase2     | Python | Worker      | codegen-target, llm-agent-loop          |
| 5.3                                                          | code-assembler      | Domain      | Phase2     | Python | Worker      | codegen-target                          |
| 5.4                                                          | code-snapshot       | Domain      | Phase2     | Python | Worker      | ★CodeSnapshotRepositoryPort             |
| 5.5                                                          | codegen-target      | Domain      | Phase2     | Python | shared lib  | -                                       |
| **L1 Domain — Phase3（7 个）**                               |                     |             |            |        |             |                                         |
| 6.1                                                          | static-reflector    | Domain      | Phase3     | Python | Worker      | llm-agent-loop                          |
| 6.2                                                          | sandbox-provisioner | Domain      | Phase3     | Python | Worker      | sandbox-runtime                         |
| 6.3                                                          | sandbox-compiler    | Domain      | Phase3     | Python | Worker      | sandbox-runtime                         |
| 6.4                                                          | sandbox-executor    | Domain      | Phase3     | Python | Worker      | sandbox-runtime                         |
| 6.5                                                          | case-synthesizer    | Domain      | Phase3     | Python | Worker      | llm-agent-loop                          |
| 6.6                                                          | dynamic-reflector   | Domain      | Phase3     | Python | Worker      | llm-agent-loop                          |
| 6.7                                                          | fix-loop-controller | Domain      | Phase3     | Python | Worker      | phase-state-machine                     |
| **L1 Domain — Review（2 个）**                               |                     |             |            |        |             |                                         |
| 7.1                                                          | review-workflow     | Domain      | Review     | Python | API         | ★ReviewRepositoryPort                   |
| 7.2                                                          | review-comment      | Domain      | Review     | Python | API         | ★CommentRepositoryPort                  |
| **L2 Application（6 个，idempotency 从 Domain 迁入）**       |                     |             |            |        |             |                                         |
| 8.1                                                          | api-gateway         | App         | -          | Python | API Node    | All Domain                              |
| 8.2                                                          | websocket-pusher    | App         | -          | Python | API Node    | redis-pubsub                            |
| 8.3                                                          | worker-runtime      | App         | -          | Python | Worker Node | All Phase                               |
| 8.4                                                          | pipeline-builder    | App         | Execution  | Python | Worker      | LangGraph                               |
| 8.5                                                          | pipeline-variant    | App         | Execution  | Python | shared lib  | feature-flag                            |
| 8.6                                                          | idempotency         | App         | -          | Python | API+Worker  | redis-pubsub, mysql-store               |
| **L3 Integration（6 个）**                                   |                     |             |            |        |             |                                         |
| 9.1                                                          | llm-provider        | Integration | -          | Python | shared lib  | secret-vault                            |
| 9.2                                                          | llm-tool-use        | Integration | -          | Python | shared lib  | -                                       |
| 9.3                                                          | llm-output-schema   | Integration | -          | Python | shared lib  | schema-engine                           |
| 9.4                                                          | llm-prompt-cache    | Integration | -          | Python | shared lib  | redis-pubsub                            |
| 9.5                                                          | llm-agent-loop      | Integration | -          | Python | shared lib  | llm-*                                   |
| 9.6                                                          | sandbox-runtime     | Integration | -          | Python | shared lib  | docker-driver                           |
| **L4 Cross-Cutting（侧切面，7 个，新增 llm-cost-governor）** |                     |             |            |        |             |                                         |
| 10.1                                                         | trace-bus           | Cross       | -          | Python | shared lib  | mongo-trace, redis-pubsub               |
| 10.2                                                         | metrics             | Cross       | -          | Python | shared lib  | Prometheus client                       |
| 10.3                                                         | audit-log           | Cross       | -          | Python | shared lib  | mysql-store                             |
| 10.4                                                         | auth-rbac           | Cross       | -          | Python | shared lib  | mysql-store                             |
| 10.5                                                         | feature-flag        | Cross       | -          | Python | shared lib  | redis-pubsub                            |
| 10.6                                                         | secret-vault        | Cross       | -          | Python | shared lib  | env / KMS                               |
| 10.7                                                         | llm-cost-governor   | Cross       | -          | Python | shared lib  | redis-pubsub, metrics                   |
| **L5 Infrastructure（5 个）**                                |                     |             |            |        |             |                                         |
| 11.1                                                         | mysql-store         | Infra       | -          | Python | shared lib  | SQLAlchemy                              |
| 11.2                                                         | mongo-trace         | Infra       | -          | Python | shared lib  | motor                                   |
| 11.3                                                         | redis-pubsub        | Infra       | -          | Python | shared lib  | redis-py                                |
| 11.4                                                         | docker-driver       | Infra       | -          | Python | shared lib  | docker SDK                              |
| 11.5                                                         | schema-migration    | Infra       | -          | Python | CLI + Cron  | alembic                                 |

> **统计**：领域层 35 + 应用层 6 + 集成层 6 + 横切面 7 + 基础设施 5 = **52 个模块**（不含 Port 接口定义）
>
> **Port 接口说明**：标注 ★ 的依赖表示领域层定义了抽象 Port 接口（ABC），由基础设施层或集成层提供具体实现，通过 DI 注入。领域代码中 **import 的是 Port ABC，不是 mysql-store/redis-pubsub 等具体模块**。

### 2.2 部署单元映射

| 部署单元         | 包含模块                                                    | 副本数（建议）    | 状态                 |
| ---------------- | ----------------------------------------------------------- | ----------------- | -------------------- |
| API Node         | api-gateway, websocket-pusher, 所有 Domain（只读 + 短事务） | ≥2                | 无状态               |
| Worker (general) | worker-runtime + Phase1/Phase2 模块 + LLM 集成              | ≥2                | 无状态               |
| Worker (sandbox) | worker-runtime + Phase3 + sandbox-runtime + docker-driver   | ≥2                | 无状态（容器是状态） |
| Cron Beat        | schema-migration trigger, 孤儿清理, 指标聚合                | 1（leader 选举）  | 单例                 |
| MySQL            | mysql-store 数据                                            | 1 主 + N 从       | 有状态               |
| MongoDB          | mongo-trace 数据                                            | 副本集（3 节点）  | 有状态               |
| Redis            | redis-pubsub + 锁 + 缓存                                    | Cluster 3 主 3 从 | 有状态               |

### 2.3 数据流总览

```
                           ┌───────────────┐
                  保存图    │  forest-      │
                  ────────► │  structure    │
                           │  + snapshot   │
                           └───────┬───────┘
                                   │ 版本化
                                   ▼
                           ┌───────────────┐
                  触发 Run │  workflow-    │
                  ────────►│  run          │ ──持久化──► MySQL
                           └───────┬───────┘
                                   │ 入队
                                   ▼
                           ┌───────────────┐
                           │  Redis Queue  │
                           └───────┬───────┘
                                   │ 出队
                                   ▼
                           ┌───────────────┐
                           │  worker-      │
                           │  runtime      │
                           └───────┬───────┘
                                   │ 加载 state
                                   ▼
                  ┌────────────────┴────────────────┐
                  │        cascade-state            │ ◄──贯穿三阶段──┐
                  └────────────────┬────────────────┘                │
                                   │                                 │
              ┌────────────────────┼────────────────────┐            │
              ▼                    ▼                    ▼            │
        ┌─────────┐          ┌─────────┐          ┌─────────┐        │
        │ Phase1  │ ────────►│ Phase2  │ ────────►│ Phase3  │ ───────┘
        └────┬────┘          └────┬────┘          └────┬────┘
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                                  ▼
                          ┌──────────────┐
                          │ trace-bus    │ ──► MongoDB (trace)
                          │              │ ──► Redis (实时推送)
                          └──────────────┘
                                  │
                                  ▼
                          ┌──────────────┐
                          │ websocket-   │ ──► User
                          │ pusher       │
                          └──────────────┘
```

### 2.4 模块详细设计的统一模板

**第 3-6 章每个模块按以下结构呈现：**

```
### X.Y <module-name>
- 限界上下文：xxx
- 部署位置：API / Worker / shared lib
- 依赖：列出依赖的模块
- 被依赖：列出谁会调用本模块
- 核心职责：3-5 条
- 关键模型：聚合根/实体/值对象（如适用）
- 公开接口：方法签名
- 状态机：（如适用，引用第 7 章）
- 持久化：（如有）
- 领域事件：（如发布）
- 扩展点：（如有插件机制）
- 分布式考虑：并发、幂等、超时、降级
- 反模式与禁止：明确不允许什么
- 单元测试关键场景
```

------

## 第 3 章 Node/Graph 域模块详细设计

### 3.1 Node 域模块（5 个）

#### 3.1.1 `node-definition`（节点定义）

- **限界上下文**：Node
- **部署位置**：API + Worker（shared lib）
- **依赖**：schema-engine
- **被依赖**：node-registry, node-library, forest-structure, code-generator
- **核心职责**
  1. 定义 `NodeTemplate` 聚合根、`NodeTemplateVersion` 实体、`NodeTemplateDefinition` 值对象
  2. 校验模板定义的合法性（input/output schema 自洽、edge_semantics 不重复）
  3. 计算定义哈希用于版本去重
  4. 提供 `freeze_to_snapshot()` 方法供图保存时冻结模板
  5. **D3A 留白点**：`NodeTemplateDefinition` 是结构稳定的载体，具体 D3A 节点的字段定义后续作为数据填入
- **关键模型**

```python
@dataclass(frozen=True)
class NodeTemplateDefinition:
    """模板的不变定义体（值对象）"""
    description: str
    input_schema: dict        # JSON Schema
    output_schema: dict       # JSON Schema
    simulator: JsonSimulatorSpec
    edge_semantics: tuple[EdgeSemantic, ...]
    code_hints: CodeGenerationHints
    extensions: Mapping[str, Any]   # 扩展点：未来加字段不破坏向后兼容

    schema_version: int = 1   # 定义自身的 schema 版本

    def compute_hash(self) -> str:
        """规范化 JSON 后 SHA256"""
class NodeTemplate:
    """聚合根"""
    id: str                    # tpl_xxxxxxxx
    name: str                  # PascalCase
    display_name: str
    category: str
    scope: Scope               # GLOBAL | PRIVATE
    owner_id: int | None
    current_version_id: str
    status: TemplateStatus     # DRAFT | ACTIVE | DEPRECATED
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None  # 软删除
```

- **公开接口**

```python
class TemplateValidator:
    def validate(self, defn: NodeTemplateDefinition) -> ValidationReport: ...
    def validate_schema_self_consistency(self, schema: dict) -> None: ...

class DefinitionFactory:
    def create_v1(self, raw: dict) -> NodeTemplateDefinition: ...
    def upgrade(self, old: NodeTemplateDefinition, target_v: int) -> NodeTemplateDefinition: ...
```

- **状态机**：见 §7.7（NodeTemplate 状态机）
- **持久化**：MySQL `t_node_template` + `t_node_template_version`
- **扩展点**
  - `extensions: Mapping[str, Any]`：定义体的开放字段，遵循 "未识别字段保留 + 警告" 原则
  - `schema_version`：支持多版本并存，配合 `DefinitionFactory.upgrade` 平滑升级
- **分布式考虑**
  - 模板定义只读时大量并发，写时通过 `node-registry` 的乐观锁串行
  - 哈希计算必须确定性（dict 排序、数字标准化）
- **反模式**
  - ❌ 在定义中直接耦合 D3A 字段（应放 extensions 或 input_schema 的具体内容里）
  - ❌ 在 description 中嵌入结构化数据（应该用 extensions）
- **关键测试**
  - `test_definition_hash_stability`：相同语义不同字段顺序，哈希必须相等
  - `test_extensions_unknown_field`：未知字段保留并发警告
  - `test_schema_version_upgrade`：v1 升级到 v2 不丢字段

------

#### 3.1.2 `node-registry`（节点注册表）

- **限界上下文**：Node
- **部署位置**：API + Worker
- **依赖**：mysql-store, redis-pubsub, node-definition
- **被依赖**：forest-structure（构建图时解析模板）, scenario-engine（执行时拿到 simulator）
- **核心职责**
  1. 提供按 `(name, owner_id, scope, version)` 维度的模板查找
  2. 二级缓存：进程内 LRU + Redis 共享缓存，TTL + 显式失效
  3. Scope 解析规则：private 优先于 global（同名时）
  4. 模板版本写入时通过分布式锁保证唯一性
  5. 发布 `TemplateUpdated` 事件触发缓存失效广播
- **公开接口**

```python
class NodeTemplateRegistry:
    async def get(
        self,
        name: str,
        owner_id: int | None,
        scope: Scope = Scope.GLOBAL,
        version: int | str = "current",
    ) -> NodeTemplate: ...

    async def get_by_id(self, template_id: str) -> NodeTemplate: ...

    async def resolve_for_user(self, name: str, user_id: int) -> NodeTemplate:
        """按 private 优先 → global 兜底的规则解析"""

    async def invalidate(self, template_id: str) -> None: ...
    async def invalidate_all(self) -> None: ...

    def simulator_of(self, template: NodeTemplate) -> NodeSimulator: ...
```

- **缓存层次**

```
┌──────────────────────────────┐
│ Process LRU (100, 60s TTL)  │  ← 同一进程内复用
└────────────┬─────────────────┘
             │ miss
             ▼
┌──────────────────────────────┐
│ Redis Cache (300s TTL)       │  ← 跨进程共享
└────────────┬─────────────────┘
             │ miss
             ▼
┌──────────────────────────────┐
│ MySQL                         │  ← 真值
└──────────────────────────────┘
```

- **缓存失效协议**
  - 写操作：DB 写入成功 → `redis_del(key)` → `redis_publish(template:invalidated, template_id)`
  - 读操作订阅 channel，收到失效消息后清进程内 LRU
- **分布式考虑**
  - 锁：写新版本时加 `lock:tpl_version:{template_id}`，超时 5s
  - 缓存击穿：使用 single-flight 模式（Redis SETNX 哨兵 + 等待）
  - 缓存穿透：不存在的查询用空值占位 30s
  - 一致性：写后读保证（先 DB 后失效），最终一致延迟 < 1s
- **反模式**
  - ❌ 直接读 MySQL 不走 registry（破坏缓存协议）
  - ❌ 缓存 NodeSimulator 实例（应缓存 Template，每次构造 Simulator）
- **关键测试**
  - `test_resolve_private_overrides_global`
  - `test_cache_invalidation_propagation`：节点 A 写入 → 节点 B 立即看到新版
  - `test_cache_stampede`：1000 并发查询 miss key，仅 1 次 DB

------

#### 3.1.3 `node-simulator`（模拟器）

- **限界上下文**：Node
- **部署位置**：Worker
- **依赖**：llm-agent-loop, schema-engine
- **被依赖**：scenario-engine
- **核心职责**
  1. 定义 `NodeSimulator` 抽象基类
  2. 实现 `PurePythonSimulator`、`LlmSimulator`、`HybridSimulator`
  3. 模拟器工厂：根据 `JsonSimulatorSpec.engine` 创建对应实例
  4. 强制 simulator 输出符合 `output_schema`（forced output）
  5. **无状态**：每次 `run()` 不带状态，所有外部依赖通过 `SimContext` 注入
- **关键模型**

```python
@dataclass(frozen=True)
class SimContext:
    """模拟器执行上下文"""
    run_id: str
    instance_id: str
    bundle_id: str | None
    upstream_outputs: Mapping[str, Any]
    tables: Mapping[str, list]
    tracer: TraceEmitter
    deadline: datetime
    cancel_token: CancelToken

@dataclass(frozen=True)
class SimResult:
    output_json: dict
    outgoing_edges: list[OutgoingEdge]
    warnings: tuple[str, ...]
    duration_ms: int
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

class NodeSimulator(ABC):
    @abstractmethod
    async def run(
        self,
        fields: Mapping[str, Any],
        input_json: Mapping[str, Any],
        ctx: SimContext,
    ) -> SimResult: ...

    @abstractmethod
    def kind(self) -> Literal["pure", "llm", "hybrid"]: ...
```

- **公开接口**

```python
class NodeSimulatorFactory:
    def __init__(self, registry: dict[str, type[NodeSimulator]]): ...
    def register(self, kind: str, cls: type[NodeSimulator]) -> None: ...
    def create(self, template: NodeTemplate, llm: LLMAgent) -> NodeSimulator: ...
```

- **扩展点**
  - 注册新 `kind`：实现 `NodeSimulator` 子类 → 工厂注册即可，不动核心
  - 例：未来加 `WasmSimulator`（用于 D3A 高性能仿真）只需新增类
- **分布式考虑**
  - **无状态**：可在 Worker 间任意调度
  - 超时：`ctx.deadline` 强制截止，超时抛 `SimulatorTimeout`
  - 取消：`ctx.cancel_token` 周期性检查（每次 LLM 调用前后）
  - LLM 失败重试：见 §6.3.5（llm-agent-loop）
- **反模式**
  - ❌ 在 simulator 实例上保存状态（不能跨调用）
  - ❌ 在 simulator 内部直接调 OpenAI SDK（应通过 `LLMAgent`）
  - ❌ 输出不符合 schema 时静默截断（应抛 `SchemaViolation`）
- **关键测试**
  - `test_pure_simulator_deterministic`：相同输入相同输出
  - `test_llm_simulator_forced_schema`：强制输出 schema，违规则报错
  - `test_simulator_timeout_respected`：deadline 到达后立即返回
  - `test_simulator_cancel_propagates`：取消令牌触发后停止

------

#### 3.1.4 `node-library`（节点库）

- **限界上下文**：Node
- **部署位置**：API
- **依赖**：node-definition, node-registry, auth-rbac
- **被依赖**：api-gateway（模板管理 API）
- **核心职责**
  1. 全局模板与私有模板的管理与权限控制
  2. 模板的发布、废弃、复制、Fork 操作
  3. 模板的搜索、分类、标签
  4. 模板的导入导出（JSON Pack）
  5. **D3A 留白点**：内置 D3A 模板包作为种子数据，可后续填充
- **公开接口**

```python
class TemplateLibraryService:
    async def publish(self, template_id: str, by_user: int) -> None: ...
    async def deprecate(self, template_id: str, by_user: int) -> None: ...
    async def fork_to_private(self, template_id: str, owner_id: int) -> str: ...
    async def search(self, query: SearchQuery, viewer_id: int) -> list[NodeTemplate]: ...
    async def export_pack(self, template_ids: list[str]) -> bytes: ...
    async def import_pack(self, data: bytes, by_user: int) -> ImportReport: ...
```

- **权限规则**

| 操作 | global | private(own)  | private(other) |
| ---- | ------ | ------------- | -------------- |
| 查看 | 所有人 | 所有者+管理员 | 拒绝           |
| 编辑 | 管理员 | 所有者        | 拒绝           |
| Fork | 任何人 | 所有者        | 拒绝           |
| 废弃 | 管理员 | 所有者        | 拒绝           |

- **领域事件**：`TemplatePublished`, `TemplateDeprecated`, `TemplateForked`
- **分布式考虑**
  - Fork 操作非幂等 → 加 `idempotency_key`
  - 导入大包：分块 + 事务保护
- **反模式**
  - ❌ 模板复制后还共享版本（必须深拷贝并新建版本树）
- **关键测试**
  - `test_fork_creates_independent_lineage`
  - `test_import_atomic_rollback_on_error`

------

#### 3.1.5 `schema-engine`（JSON Schema 引擎）

- **限界自上下文**：Node（共享 lib）
- **部署位置**：shared lib
- **依赖**：jsonschema 第三方库
- **被依赖**：node-definition, llm-output-schema, forest-visitor
- **核心职责**
  1. 封装 jsonschema 库，统一 Draft 版本（Draft 2020-12）
  2. 提供 `validate(data, schema) → ValidationReport` 接口
  3. 提供 schema 自身合法性校验
  4. 提供 schema 的等价比较（用于版本兼容性判断）
  5. 提供 schema 的合并与差异（forward-compat 检测）
- **公开接口**

```python
class SchemaEngine:
    def validate(self, data: Any, schema: dict) -> ValidationReport: ...
    def check_self_consistent(self, schema: dict) -> None: ...
    def is_backward_compatible(self, old: dict, new: dict) -> bool:
        """new 是否可以接收所有 old 接受的数据（向后兼容）"""
    def diff(self, old: dict, new: dict) -> SchemaDiff: ...
    def normalize(self, schema: dict) -> dict:
        """规范化用于 hash"""
```

- **分布式考虑**：纯函数，无状态，可任意复用
- **关键测试**
  - `test_backward_compat_add_optional_field`
  - `test_breaks_on_required_field_addition`
  - `test_normalize_idempotent`

------

### 3.2 Graph 域模块（5 个）

#### 3.2.1 `forest-structure`（森林结构）

- **限界上下文**：Graph
- **部署位置**：API + Worker
- **依赖**：node-registry
- **被依赖**：forest-snapshot, dag-compute, scenario-engine, code-planner
- **核心职责**
  1. 定义 `CascadeForest`、`Bundle`、`NodeInstance`、`Edge` 不可变数据结构
  2. 提供 `CascadeForestBuilder` 从原始 JSON 构建森林（解析模板、填充 snapshot）
  3. 引用完整性检查（边/Bundle 引用的 instance_id 必须存在）
  4. 字段值合法性检查（按 `template_snapshot.input_schema`）
  5. 不变性：所有数据结构 frozen，修改返回新实例
- **关键模型**

```python
@dataclass(frozen=True)
class CascadeForest:
    graph_version_id: str
    version_number: int
    bundles: tuple[Bundle, ...]
    node_instances: tuple[NodeInstance, ...]
    edges: tuple[Edge, ...]
    metadata: Mapping[str, Any]
    schema_version: int = 1

    def with_node(self, node: NodeInstance) -> "CascadeForest": ...   # 不可变更新
    def without_node(self, instance_id: str) -> "CascadeForest": ...
    def with_edge(self, edge: Edge) -> "CascadeForest": ...
```

- **公开接口**

```python
class CascadeForestBuilder:
    def __init__(self, registry: NodeTemplateRegistry, schema: SchemaEngine): ...
    async def build(self, raw: dict) -> CascadeForest: ...
    async def freeze_template_snapshots(self, raw: dict) -> dict:
        """保存前调用：把每个 instance 的 template_id 解析为 template_snapshot"""
```

- **分布式考虑**：
  - 构建是 CPU 密集 + IO（registry 查询）；构建结果可缓存（只读时）
  - `freeze_template_snapshots` 使用 `node-registry` 加锁查询，避免读到正在升级的模板
- **反模式**
  - ❌ 直接修改 `CascadeForest` 字段（必须返回新实例）
  - ❌ Build 阶段只存 template_id 不冻结 snapshot（破坏快照原则）
- **关键测试**
  - `test_build_resolves_templates`
  - `test_freeze_makes_immutable_snapshot`
  - `test_with_node_returns_new_instance`

------

#### 3.2.2 `forest-snapshot`（快照与版本化）

- **限界上下文**：Graph
- **部署位置**：API + Worker
- **依赖**：mysql-store, forest-structure
- **被依赖**：workflow-run（执行时加载快照）
- **核心职责**
  1. `Graph` 与 `GraphVersion` 聚合根的持久化
  2. 保存新版本时：序列化 `CascadeForest` → MySQL JSON 列；冻结模板 snapshot
  3. 加载版本：MySQL → 反序列化 → `CascadeForest`
  4. 版本号自增（行级锁保证）
  5. 软删除支持
- **关键模型**

```python
class Graph:                       # 聚合根（图，不含具体快照）
    id: str
    name: str
    description: str
    owner_id: int
    current_version_id: str | None
    status: GraphStatus            # ACTIVE | ARCHIVED
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

class GraphVersion:                # 实体
    id: str
    graph_id: str
    version_number: int            # 自增
    snapshot: dict                 # 序列化的 CascadeForest（JSON）
    snapshot_hash: str
    state: VersionState            # DRAFT | SAVED | VALIDATED | ARCHIVED
    validated_at: datetime | None
    created_by: int
    created_at: datetime
```

- **公开接口**

```python
class GraphRepository:
    async def create(self, dto: GraphCreate) -> str: ...
    async def get(self, graph_id: str) -> Graph: ...
    async def update_meta(self, graph_id: str, name: str, desc: str) -> None: ...
    async def soft_delete(self, graph_id: str) -> None: ...

class GraphVersionRepository:
    async def save_new_version(
        self,
        graph_id: str,
        forest: CascadeForest,
        created_by: int,
    ) -> GraphVersion: ...
    async def get(self, version_id: str) -> GraphVersion: ...
    async def get_by_number(self, graph_id: str, n: int) -> GraphVersion: ...
    async def list_versions(self, graph_id: str) -> list[GraphVersion]: ...
    async def transition(self, version_id: str, to_state: VersionState) -> GraphVersion: ...
```

- **状态机**：见 §7.8（GraphVersion 状态机）
- **持久化**：MySQL `t_cascade_graph` + `t_graph_version`（snapshot 列建议 LongTextJSON 或 MEDIUMBLOB+gzip）
- **领域事件**：`GraphVersionSaved`, `GraphVersionValidated`
- **分布式考虑**
  - 版本号冲突：唯一约束 `(graph_id, version_number)` + 行级锁保护自增
  - 大快照（>1MB）：考虑压缩存储；分页加载
- **反模式**
  - ❌ 修改已保存的 `GraphVersion.snapshot`（一旦保存即不可变）
  - ❌ 直接 SQL UPDATE 状态（必须经状态机）
- **关键测试**
  - `test_concurrent_version_save_no_duplicate_number`
  - `test_snapshot_hash_stable`
  - `test_archived_version_load`

------

#### 3.2.3 `dag-compute`（DAG 计算）

- **限界上下文**：Graph
- **部署位置**：shared lib
- **依赖**：networkx
- **被依赖**：forest-visitor, scenario-engine, code-planner
- **核心职责**
  1. 给定 `CascadeForest`，计算其 DAG 视图集合（每个根一个 DAG）
  2. 拓扑排序（用于代码生成顺序、场景执行顺序）
  3. 环检测
  4. 入度/出度查询、根节点查询、孤儿节点查询
  5. 可达性查询、跨 Bundle 查询
- **关键模型**

```python
@dataclass(frozen=True)
class DagView:
    dag_index: int
    root: str                      # root instance_id
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    spans_bundles: tuple[str, ...] # 跨越的 bundle_id 集合
    topo_order: tuple[str, ...]    # 预计算的拓扑序

class DagCompute:
    @staticmethod
    def compute_views(forest: CascadeForest) -> list[DagView]: ...

    @staticmethod
    def topological_sort(forest: CascadeForest) -> list[str]: ...

    @staticmethod
    def detect_cycles(forest: CascadeForest) -> list[list[str]]: ...

    @staticmethod
    def find_roots(forest: CascadeForest) -> list[str]: ...

    @staticmethod
    def find_orphans(forest: CascadeForest) -> list[str]: ...

    @staticmethod
    def reachable_from(forest: CascadeForest, src: str) -> set[str]: ...
```

- **分布式考虑**：纯函数，结果可基于 `snapshot_hash` 缓存
- **反模式**
  - ❌ 在循环中重复调用 `compute_views`（O(N²) 退化），应一次性计算缓存
- **关键测试**
  - `test_topo_sort_deterministic`：相同输入相同顺序（用 instance_id 字典序破除歧义）
  - `test_cycle_detection_finds_all`
  - `test_disconnected_forest_multi_dag`

------

#### 3.2.4 `forest-visitor`（Visitor 框架）

- **限界上下文**：Graph
- **部署位置**：shared lib
- **依赖**：dag-compute, schema-engine
- **被依赖**：structure-check, scenario-engine, dynamic-reflector
- **核心职责**
  1. `ForestVisitor` 抽象基类（支持只读遍历）
  2. 内置 Visitor：`CycleChecker`, `NodeRefChecker`, `EdgeSemanticChecker`, `SchemaValidator`, `OrphanFinder`, `BundleConsistencyChecker`
  3. `ValidationReport` 聚合（errors + warnings）
  4. **插件注册**：可注册自定义 Visitor，由 `DesignValidator` 统一调度
  5. 支持串行 / 并行执行（独立 Visitor 可并行）
- **公开接口**

```python
class ForestVisitor(ABC):
    name: ClassVar[str]
    severity: ClassVar[Literal["error", "warning"]] = "error"
    parallel_safe: ClassVar[bool] = True

    @abstractmethod
    def visit(self, forest: CascadeForest) -> list[ValidationIssue]: ...

class VisitorRegistry:
    def register(self, visitor: type[ForestVisitor]) -> None: ...
    def list(self) -> list[type[ForestVisitor]]: ...

class DesignValidator:
    def __init__(self, registry: VisitorRegistry): ...
    async def run(self, forest: CascadeForest) -> ValidationReport:
        """并行执行所有 parallel_safe 的 Visitor"""
```

- **扩展点**
  - 新 Visitor：实现 `ForestVisitor` 子类 + 调用 `registry.register()`
  - 例：未来加 `D3ANamingConvention` Visitor 用于检查 D3A 节点命名
- **分布式考虑**
  - Visitor 是纯函数，结果按 `(snapshot_hash, visitor_name, visitor_version)` 缓存到 Redis
- **反模式**
  - ❌ Visitor 修改 forest（必须只读）
  - ❌ Visitor 之间相互依赖（应通过 DesignValidator 编排顺序）
- **关键测试**
  - `test_visitor_registry_dynamic_add`
  - `test_validator_parallel_execution`
  - `test_validator_cache_hit`

------

#### 3.2.5 `forest-diff`（版本 Diff/Merge）

- **限界上下文**：Graph
- **部署位置**：API
- **依赖**：dag-compute
- **被依赖**：api-gateway（版本对比 API）
- **核心职责**
  1. 计算两个 `GraphVersion` 之间的差异（节点添加/删除/修改、边变化、Bundle 变化）
  2. 提供按 Bundle / DAG 维度的差异视图
  3. 生成结构化 patch（用于审计、回滚）
  4. 不实现自动 merge（人工评审场景下不需要，避免错误合并）
- **公开接口**

```python
@dataclass(frozen=True)
class ForestDiff:
    added_nodes: tuple[NodeInstance, ...]
    removed_nodes: tuple[NodeInstance, ...]
    modified_nodes: tuple[NodeChange, ...]
    added_edges: tuple[Edge, ...]
    removed_edges: tuple[Edge, ...]
    bundle_changes: tuple[BundleChange, ...]

class ForestDiffer:
    @staticmethod
    def diff(old: CascadeForest, new: CascadeForest) -> ForestDiff: ...
    @staticmethod
    def to_patch(diff: ForestDiff) -> dict: ...
```

- **分布式考虑**：纯函数，无状态
- **关键测试**
  - `test_diff_detects_field_value_change`
  - `test_diff_handles_bundle_split`

------

## 第 4 章 Execution/Phase1 域模块详细设计

### 4.1 Execution 域模块（6 个）

#### 4.1.1 `workflow-run`（运行聚合根）

- **限界上下文**：Execution
- **部署位置**：API + Worker
- **依赖**：mysql-store, phase-state-machine, trace-bus
- **被依赖**：api-gateway（创建/查询）, worker-runtime（执行）, run-step（关联）
- **核心职责**
  1. 定义 `WorkflowRun` 聚合根，封装一次执行的完整生命周期
  2. 持久化运行元信息（status, verdicts, timestamps, error）
  3. 强制所有状态变更经过 `phase-state-machine`（不允许直接 UPDATE）
  4. 乐观锁保护并发更新（version 字段）
  5. 提供查询接口（按用户、按图版本、按时间范围）
- **关键模型**

```python
class WorkflowRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Phase1Verdict(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    INCONCLUSIVE = "inconclusive"

class Phase2Status(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class Phase3Verdict(str, Enum):
    DONE = "done"
    DESIGN_BUG = "design_bug"
    FIX_EXHAUSTED = "fix_exhausted"

@dataclass
class WorkflowRun:
    id: str                            # r_xxxxxxxx
    graph_version_id: str
    status: WorkflowRunStatus
    phase1_verdict: Phase1Verdict | None
    phase2_status: Phase2Status | None
    phase3_verdict: Phase3Verdict | None
    final_verdict: Literal["valid", "invalid", "inconclusive"] | None
    review_status: ReviewStatus | None

    started_at: datetime | None
    finished_at: datetime | None
    triggered_by: int
    pipeline_variant: str              # "full" | "phase1_only" | "phase1_phase2" | ...
    options: Mapping[str, Any]
    idempotency_key: str | None

    error_code: str | None             # ErrorCode 枚举字符串
    error_message: str | None
    error_phase: int | None            # 1 | 2 | 3 | None

    version: int                        # 乐观锁版本号
    created_at: datetime
    updated_at: datetime
```

- **公开接口**

```python
class WorkflowRunRepository(ABC):
    async def create(self, run: WorkflowRun) -> str: ...
    async def get(self, run_id: str) -> WorkflowRun: ...
    async def get_with_lock(self, run_id: str) -> WorkflowRun: ...   # SELECT FOR UPDATE
    async def update(self, run: WorkflowRun) -> WorkflowRun:
        """乐观锁：where version = old_version；冲突抛 OptimisticLockError"""
    async def list_by_user(
        self,
        user_id: int,
        status: WorkflowRunStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowRun]: ...

class WorkflowRunService:
    """聚合根的应用服务（封装事务边界）"""
    async def create_run(self, dto: RunCreateDTO) -> WorkflowRun: ...
    async def transition_status(
        self, run_id: str, new_status: WorkflowRunStatus, *, by: str
    ) -> WorkflowRun:
        """通过 PhaseStateMachine 校验后更新（含乐观锁重试）"""
    async def record_phase_verdict(
        self, run_id: str, phase: int, verdict: str
    ) -> WorkflowRun: ...
    async def fail(self, run_id: str, code: str, msg: str, phase: int) -> WorkflowRun: ...
    async def finish_success(self, run_id: str, final: str) -> WorkflowRun: ...
```

- **状态机**：见 §7.1（WorkflowRun 主状态机）
- **持久化**：MySQL `t_workflow_run`（version 列做乐观锁）
- **领域事件**：`RunCreated`, `RunStarted`, `RunFinished`, `RunCancelled`, `RunFailed`
- **分布式考虑**
  - 创建：API 节点写入；幂等键去重见 §4.1.5
  - 更新：Worker 节点更新；乐观锁失败重试 3 次；3 次失败抛错由上层决策（通常意味着冲突 → 中止）
  - 查询：从库读，最终一致；高频查询走 Redis 缓存
- **反模式**
  - ❌ 直接 `UPDATE t_workflow_run SET status = ...` 不走状态机
  - ❌ 在 Worker 中持有 `WorkflowRun` 对象跨阶段（应每次重新加载）
- **关键测试**
  - `test_optimistic_lock_conflict_retries`
  - `test_invalid_state_transition_rejected`
  - `test_concurrent_finish_only_one_wins`

------

#### 4.1.2 `phase-state-machine`（阶段状态机 — 核心）

- **限界上下文**：Execution
- **部署位置**：shared lib
- **依赖**：trace-bus
- **被依赖**：workflow-run, fix-loop-controller, pipeline-builder
- **核心职责**
  1. **集中管理所有状态转移规则**，杜绝散落在各 Step 中的 `if/else` 状态判断
  2. 提供 `transition(run, new_status)` 校验后转移
  3. 提供 `next_action(run)` 决策下一步（根据当前 status + verdicts 推算）
  4. 发布每次转移为领域事件
  5. 防御非法转移（抛 `InvalidStateTransition`）
- **关键设计：把 v1 的 `PhaseRouter` 散乱逻辑全部收口到这里**

```python
class PhaseStateMachine:
    """所有阶段状态转移的唯一入口"""

    # 主状态机（WorkflowRunStatus）
    MAIN_TRANSITIONS: dict[WorkflowRunStatus, set[WorkflowRunStatus]] = {
        WorkflowRunStatus.PENDING:   {WorkflowRunStatus.RUNNING, WorkflowRunStatus.CANCELLED},
        WorkflowRunStatus.RUNNING:   {WorkflowRunStatus.SUCCESS, WorkflowRunStatus.FAILED, WorkflowRunStatus.CANCELLED},
        WorkflowRunStatus.SUCCESS:   set(),  # 终态
        WorkflowRunStatus.FAILED:    set(),  # 终态
        WorkflowRunStatus.CANCELLED: set(),  # 终态
    }

    # 阶段调度规则（pipeline_variant 影响）
    @classmethod
    def next_phase(
        cls,
        run: WorkflowRun,
        variant: PipelineVariant,
    ) -> Literal["phase1", "phase2", "phase3", "done"]:
        if run.phase1_verdict is None:
            return "phase1"
        if run.phase1_verdict != Phase1Verdict.VALID:
            return "done"  # phase1 失败直接结束
        if not variant.includes_phase2():
            return "done"
        if run.phase2_status is None:
            return "phase2"
        if run.phase2_status == Phase2Status.FAILED and not variant.allow_phase3_on_p2_fail():
            return "done"
        if not variant.includes_phase3():
            return "done"
        if run.phase3_verdict is None:
            return "phase3"
        return "done"

    @classmethod
    def compute_final_verdict(cls, run: WorkflowRun) -> Literal["valid", "invalid", "inconclusive"]:
        # 显式表，而不是散落的推断
        if run.phase1_verdict == Phase1Verdict.INVALID:
            return "invalid"
        if run.phase1_verdict == Phase1Verdict.INCONCLUSIVE:
            return "inconclusive"
        if run.phase3_verdict == Phase3Verdict.DESIGN_BUG:
            return "invalid"
        if run.phase3_verdict == Phase3Verdict.FIX_EXHAUSTED:
            return "inconclusive"
        if run.phase3_verdict == Phase3Verdict.DONE:
            return "valid"
        # 仅 Phase1+2 配置（无 Phase3）
        if run.phase2_status == Phase2Status.SUCCESS:
            return "valid"
        if run.phase2_status == Phase2Status.FAILED:
            return "invalid"
        return "inconclusive"

    @classmethod
    def validate_main_transition(
        cls, current: WorkflowRunStatus, new: WorkflowRunStatus
    ) -> None:
        if new not in cls.MAIN_TRANSITIONS.get(current, set()):
            raise InvalidStateTransition(f"{current} → {new} not allowed")

    @classmethod
    def transition(
        cls,
        run: WorkflowRun,
        new_status: WorkflowRunStatus,
        emitter: TraceEmitter | None = None,
    ) -> WorkflowRun:
        cls.validate_main_transition(run.status, new_status)
        new_run = replace(run, status=new_status, updated_at=utcnow(),
                          version=run.version + 1)
        if emitter:
            emitter.emit("run.status.transitioned", {
                "run_id": run.id, "from": run.status, "to": new_status,
            })
        return new_run
```

- **Phase1/Phase3 子状态机**：单独实现（见 §7.3 / §7.5），但同样收口在本模块
- **领域事件**：每次转移发 `state.transitioned` 事件
- **分布式考虑**
  - 状态机本身是纯函数，跨节点行为一致
  - 转移结果写入由 `workflow-run` 模块加乐观锁
- **反模式**（✱ 必须严格执行）
  - ❌ 在任何 Step / Handler / Router 中写 `if state["phase1_verdict"] == "valid": ...`，应统一调 `next_phase()`
  - ❌ 在 LangGraph 的 conditional edge 函数里写复杂逻辑（应只是 `return state_machine.next_phase(...)`）
- **关键测试**
  - `test_invalid_transition_raises`
  - `test_next_phase_decision_table`：穷举每种 verdict 组合
  - `test_final_verdict_truth_table`

------

#### 4.1.3 `cascade-state`（执行上下文状态容器）

- **限界上下文**：Execution
- **部署位置**：shared lib
- **依赖**：（无）
- **被依赖**：所有 Phase 模块
- **核心职责**
  1. 定义贯穿三阶段的执行状态 TypedDict
  2. 提供初始化、序列化、减肥（trim）方法
  3. 显式版本号 `schema_version`，支持升级迁移
  4. 字段命名规范化（修复 v1 的 `provided_scenarios` / `scenarios` 歧义）
- **⚠️ 语义澄清：CascadeState 是 Copy-on-Write 可变容器，不是值对象**

```
v2 文档将 CascadeState 标注为"值对象"但实际以 mutable dict 方式使用，存在矛盾。
v3 修正：CascadeState 是一个 **带版本控制的可变容器（Mutable State Bag）**，
类似 LangGraph 的 State 概念——每个 Step 接收 state、修改、返回。
不是 DDD 中的 Value Object。

设计约束：
- 每个 Step 只允许写自己负责的字段（通过 TypedDict 的类型约束暗示）
- 写操作在 Step 内部同步进行，不存在跨 Step 并发写
- 每次 Phase 结束后序列化持久化（MongoDB），用于崩溃恢复
- 在 Worker 间传递时通过 Redis / Celery 序列化，不共享内存引用
```

- **大小控制策略**

```
CascadeState 随执行推进会持续增长，需要控制：

1. messages（LLM 对话历史）：每个 Phase 结束后做 trim，只保留
   system_prompt + 最后 3 轮对话 + 关键 tool_use_result
   预估：从无限增长 → 固定 ~50KB/Phase

2. composite_code（代码文件集合）：仅保留最新版本
   历史版本通过 code_snapshot 独立持久化
   预估：固定 ~200KB

3. execution_results：仅保留摘要（pass/fail/error + duration）
   完整 stdout/stderr 写入 MongoDB RunStep
   预估：从无限增长 → 固定 ~10KB

4. 总大小预算：CascadeState 序列化后不超过 2MB
   超出 → 强制 trim → 记录 warning
```

- **关键模型**

```python
class CascadeState(TypedDict, total=False):
    # ===== 元信息 =====
    schema_version: int                # 当前为 1
    run_id: str
    graph_version_id: str
    pipeline_variant: str
    started_at: str                    # ISO format
    deadline: str                      # ISO format

    # ===== 输入 =====
    raw_graph_json: dict
    parsed_forest: dict | None
    scenarios: list[dict]              # 用户提供的测试场景（合并 v1 的 provided_scenarios + scenarios）
    options: dict

    # ===== Phase1 输出 =====
    validation_errors: list[ValidationIssue]
    handler_traces: list[HandlerTrace]
    current_handler: str | None
    scenario_results: list[ScenarioResult]
    node_outputs: Mapping[str, dict]
    phase1_verdict: Literal["valid", "invalid", "inconclusive"] | None

    # ===== Phase2 输出 =====
    code_skeleton: dict | None
    code_units: list[CodeUnit]
    composite_code: dict | None        # {filepath: content}
    code_snapshot_ids: list[str]
    static_issues: list[StaticIssue]
    phase2_status: Literal["pending", "success", "failed", "skipped"] | None

    # ===== Phase3 输出 =====
    compile_result: CompileResult | None
    sandbox_cases: list[SandboxCase]
    execution_results: list[ExecutionResult]
    outer_fix_iter: int
    phase3_verdict: Literal["done", "design_bug", "fix_exhausted"] | None

    # ===== 决策 =====
    decision: Decision                 # 当前决策
    final_verdict: Literal["valid", "invalid", "inconclusive"] | None

    # ===== 溯源 =====
    messages: list[Mapping]            # LLM 对话历史
    step_history: list[str]            # 已执行的 step 名

class Decision(str, Enum):
    IN_PROGRESS = "in_progress"
    HANDLER_PASS = "handler_pass"
    HANDLER_FAIL = "handler_fail"
    FIX_SPEC = "fix_spec"
    ADD_SCENARIO = "add_scenario"
    FIX_CODE = "fix_code"
    DESIGN_BUG = "design_bug"
    DONE = "done"
```

- **公开接口**

```python
class CascadeStateOps:
    @staticmethod
    def init(run_id: str, gv_id: str, raw_json: dict,
             scenarios: list[dict], variant: str) -> CascadeState: ...

    @staticmethod
    def trim_for_persist(state: CascadeState) -> CascadeState:
        """剥离不持久化的字段（如完整 messages），保留可重建关键字段"""

    @staticmethod
    def upgrade(state: dict, target_v: int) -> CascadeState:
        """schema_version 升级"""

    @staticmethod
    def serialize(state: CascadeState) -> bytes:  # for MongoDB
        """JSON-safe + 紧凑"""
```

- **分布式考虑**
  - 跨 Worker 传递：通过 LangGraph 的 state 入参 + 持久化到 MongoDB（崩溃恢复）
  - 体积大时（如 messages 数百条）：分块存储，主表只存索引
  - 字段类型严格：Worker 间序列化必须用 JSON-safe 类型
- **反模式**（✱ 关键）
  - ❌ 在 `messages` 的 content 字段中嵌入结构化 JSON 字符串（应放独立字段）
  - ❌ 用同一字段承载多种语义（如 `scenarios` 既是输入又是中间输出）
  - ❌ 字段命名不一致（v1 教训）
- **关键测试**
  - `test_init_default_values`
  - `test_trim_removes_volatile_fields`
  - `test_upgrade_v1_to_v2_preserves_data`

------

#### 4.1.4 `run-step`（步骤实体与历史）

- **限界上下文**：Execution
- **部署位置**：Worker
- **依赖**：mysql-store, mongo-trace
- **被依赖**：所有 Phase Step
- **核心职责**
  1. 每个 Step 执行时记录一个 `RunStep` 实体（success/failed/skipped）
  2. 主表存摘要（MySQL），明细存 MongoDB（input/output state、tool_calls、llm_calls）
  3. 提供按 phase / 按 status / 按时间的查询
  4. 支持失败重试时新增同 step_name 的新记录（iteration_index 区分）
- **关键模型**

```python
@dataclass
class RunStep:
    id: str                           # s_xxxxxxxx
    run_id: str
    phase: int                        # 1 | 2 | 3
    step_name: str                    # "structure_check" | "code_generator" | ...
    iteration_index: int              # 同 step 多次执行的序号
    status: Literal["success", "failed", "skipped"]
    mongo_ref: str                    # MongoDB ObjectId 引用
    summary: Mapping[str, Any]
    duration_ms: int
    error_code: str | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime
```

- **公开接口**

```python
class RunStepRepository:
    async def create_started(self, run_id, phase, step_name, iteration) -> str: ...
    async def finish_success(self, step_id, summary, duration_ms, mongo_ref) -> None: ...
    async def finish_failed(self, step_id, code, msg, duration_ms, mongo_ref) -> None: ...
    async def list(self, run_id, phase=None) -> list[RunStep]: ...

class StepDetailStore:
    async def write(self, run_id: str, step_id: str, payload: dict) -> str: ...  # 返回 mongo_ref
    async def read(self, mongo_ref: str) -> dict: ...
```

- **持久化**
  - MySQL `t_run_step`（主表，索引 `(run_id, phase, started_at)`）
  - MongoDB `run_step_details`（明细，TTL 90 天）
- **领域事件**：`StepStarted`, `StepFinished`
- **分布式考虑**
  - 写入失败容忍：MongoDB 写失败不阻塞 Worker；用 best-effort 策略 + outbox 表补偿
  - MongoDB 慢：异步批量写（buffer 100 条 / 1s flush）
- **反模式**
  - ❌ 把整个 state 写入 MySQL（应只摘要）
- **关键测试**
  - `test_step_detail_outbox_recovery`：MongoDB 不可用时 step 仍记录到 MySQL
  - `test_iteration_index_grows_on_retry`

------

#### 4.1.5 `idempotency`（幂等控制）

- **限界上下文**：Execution
- **部署位置**：API
- **依赖**：redis-pubsub, mysql-store
- **被依赖**：api-gateway（创建 Run）, llm-agent-loop（LLM 调用）, sandbox-compiler（编译）
- **核心职责**
  1. 通用幂等键管理：`(scope, key) → result_ref` 映射
  2. 双层存储：Redis 短期（10 分钟）+ MySQL 长期（30 天）
  3. 三种策略：`first-write-wins`、`return-existing`、`reject-duplicate`
  4. 自动从请求头 `Idempotency-Key` 提取
  5. 支持显式 invalidate（用于幂等键 TTL 内重复使用）
- **关键模型**

```python
@dataclass(frozen=True)
class IdempotencyKey:
    scope: str                         # "create_run" | "llm_call" | "compile"
    key: str
    user_id: int | None

class IdempotencyResult(Enum):
    NEW = "new"                        # 第一次，本次请求继续执行
    EXISTING = "existing"              # 已有结果，返回缓存
    IN_PROGRESS = "in_progress"        # 正在执行（请稍后或返回 202）
```

- **公开接口**

```python
class IdempotencyService:
    async def check_or_register(
        self, key: IdempotencyKey, ttl_seconds: int = 600
    ) -> tuple[IdempotencyResult, str | None]:
        """返回 (状态, 已有结果引用)"""

    async def register_result(
        self, key: IdempotencyKey, result_ref: str, persist: bool = True
    ) -> None: ...

    async def invalidate(self, key: IdempotencyKey) -> None: ...
```

- **算法**

```
1. SET NX scope:key value=IN_PROGRESS px=ttl
   - 成功 → 返回 NEW
   - 失败 → 读现有值
       IN_PROGRESS → 返回 IN_PROGRESS
       result_ref → 返回 EXISTING
2. 调用方执行业务逻辑
3. 成功 → register_result(key, result_ref)
   - SET scope:key result_ref px=ttl_long
   - 异步落库 MySQL
4. 失败 → invalidate(key)
   - DEL scope:key（允许重试）
```

- **分布式考虑**
  - Redis 主从切换可能丢失键 → MySQL 持久化兜底
  - 客户端重试间隔 < TTL：返回 IN_PROGRESS 让客户端等待
  - **崩溃恢复**：Worker 崩溃后键残留 IN_PROGRESS → 由后台任务扫描超时键自动清理
- **反模式**
  - ❌ 业务方自己写 SETNX（不一致），统一用本服务
- **关键测试**
  - `test_concurrent_first_write_wins`
  - `test_in_progress_returns_existing_after_complete`
  - `test_crash_recovery_clears_stale_keys`

------

#### 4.1.6 `cancellation`（取消与清理）

- **限界上下文**：Execution
- **部署位置**：API + Worker
- **依赖**：redis-pubsub, workflow-run
- **被依赖**：worker-runtime, sandbox-executor
- **核心职责**
  1. 用户/系统发起取消 → 写入 `cancel_token:{run_id}` 到 Redis
  2. Worker 在每个 Step 起止处与每次 LLM/Tool 调用前后检查 cancel_token
  3. 检测到取消 → 优雅退出当前 Step，状态置为 `cancelled`
  4. 资源清理：终止沙箱容器、释放分布式锁、刷新 Trace
  5. 防御取消风暴（同 run 短时间内多次取消请求合并）
- **公开接口**

```python
class CancellationService:
    async def request_cancel(self, run_id: str, by_user: int, reason: str) -> None: ...
    async def is_cancelled(self, run_id: str) -> bool: ...
    async def get_cancel_info(self, run_id: str) -> CancelInfo | None: ...

class CancelToken:
    """传给 Step 的轻量观察对象（带本地 1s 缓存避免风暴）"""
    def __init__(self, run_id: str, svc: CancellationService): ...
    def check(self) -> None:
        """检查并抛 CancelledError"""
    def is_set(self) -> bool: ...
```

- **领域事件**：`RunCancelRequested`, `RunCancelHonored`
- **分布式考虑**
  - 取消令牌存 Redis Hash：`cancel:{run_id} → {by, reason, at}`，TTL 24h
  - 跨 Worker：广播取消事件 → 各 Worker 立即 invalidate 本地缓存
  - 超时未响应：30s 后强制杀进程（系统级最后兜底）
- **反模式**
  - ❌ 取消后还继续写 state（必须立即停止）
  - ❌ 取消时不清理沙箱容器（资源泄漏）
- **关键测试**
  - `test_cancel_during_phase1_stops_current_handler`
  - `test_cancel_terminates_sandbox`
  - `test_cancel_idempotent`

------

### 4.2 Phase1 域模块（5 个）

#### 4.2.1 `structure-check`（结构检查 Handler）

- **限界上下文**：Phase1
- **部署位置**：Worker
- **依赖**：forest-visitor
- **被依赖**：handler-chain
- **核心职责**
  1. Phase1 Handler 链的第一站
  2. 调用 `DesignValidator` 执行所有 Visitor
  3. 汇总错误为 `ValidationIssue` 列表写入 state
  4. 决定 pass / fail（任一 error 级别 issue → fail）
  5. 不调 LLM，纯 Python，**确定性**
- **公开接口**

```python
class StructureCheckHandler(HandlerStep):
    name = "structure_check"
    handler_order = 10

    def __init__(self, validator: DesignValidator): ...

    async def _handle(self, state: CascadeState, trace: TraceEmitter) -> HandlerOutcome: ...
```

- **分布式考虑**：纯 CPU，无 IO 副作用；同 forest 多次调用结果一致 → 可缓存
- **关键测试**
  - `test_collects_all_visitor_errors`
  - `test_warning_only_passes`
  - `test_caches_by_forest_hash`

------

#### 4.2.2 `scenario-engine`（场景执行引擎）

- **限界上下文**：Phase1
- **部署位置**：Worker
- **依赖**：node-simulator, llm-agent-loop, dag-compute, scenario-comparator, failure-attribution
- **被依赖**：handler-chain (ScenarioRunHandler)
- **核心职责**
  1. 对每个 `Scenario` 在森林上完整跑一遍（按拓扑序触发节点）
  2. 每个 NodeInstance 调用对应 simulator 产出 `output_json`
  3. 汇总每个根节点的最终输出
  4. 与 `expected_output` 字段级对比
  5. 失败时归因（design / scenario / simulator）
- **关键模型**

```python
@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    actual_output: Mapping[str, Any]
    match: bool
    mismatch_detail: Mapping[str, Any] | None
    node_outputs: Mapping[str, dict]      # instance_id → output
    tool_call_count: int
    llm_call_count: int
    duration_ms: int
    attribution: Literal["design_bug", "scenario_bug", "simulator_bug", "unknown"] | None
    attribution_reason: str | None
    agent_stopped_reason: str
    error: str | None
```

- **公开接口**

```python
class ScenarioRunner:
    def __init__(
        self,
        registry: NodeTemplateRegistry,
        sim_factory: NodeSimulatorFactory,
        comparator: ScenarioComparator,
        attributor: FailureAttributor,
        agent: LLMAgent,
    ): ...

    async def run_one(
        self,
        forest: CascadeForest,
        scenario: Scenario,
        ctx: SimContext,
    ) -> ScenarioResult: ...

    async def run_all(
        self,
        forest: CascadeForest,
        scenarios: list[Scenario],
        ctx: SimContext,
    ) -> list[ScenarioResult]:
        """并行执行（默认并发度 4）"""
```

- **分布式考虑**
  - 单 scenario 内：节点按拓扑序串行（有依赖）
  - 跨 scenario 之间：默认并行（独立）
  - 并发度：可配置，默认 `min(4, len(scenarios))`，避免 LLM 限流
  - 取消：每个节点起止检查 `cancel_token`
- **反模式**
  - ❌ 跨 scenario 共享状态（必须独立 SimContext）
  - ❌ 把 simulator 的 `output_json` 与 `outgoing_edges` 混在一个字段（v1 教训）
- **关键测试**
  - `test_topological_execution_order`
  - `test_parallel_scenarios_isolated`
  - `test_cancel_propagates_to_simulators`

------

#### 4.2.3 `scenario-comparator`（场景对比器）

- **限界上下文**：Phase1
- **部署位置**：shared lib
- **依赖**：（无）
- **被依赖**：scenario-engine
- **核心职责**
  1. 字段级深度对比 `expected_output` vs `actual_output`
  2. 支持忽略字段（`ignore_paths`）、模糊匹配（数值容差）
  3. 输出结构化 mismatch 报告（具体到 JSON path）
  4. **绝不**通过 LLM 文本判断"是否匹配"
  5. 修复 v1 反模式：禁止从 LLM 输出推断 valid/invalid
- **公开接口**

```python
@dataclass(frozen=True)
class CompareOptions:
    ignore_paths: tuple[str, ...] = ()
    numeric_tolerance: float = 0.0
    list_order_sensitive: bool = True

@dataclass(frozen=True)
class MismatchPath:
    path: str                  # "$.result.code" | "$.items[3].name"
    expected: Any
    actual: Any
    reason: str                # "value_diff" | "missing" | "extra" | "type_diff"

class ScenarioComparator:
    @staticmethod
    def compare(
        expected: Mapping[str, Any],
        actual: Mapping[str, Any],
        opts: CompareOptions = CompareOptions(),
    ) -> tuple[bool, list[MismatchPath]]: ...
```

- **分布式考虑**：纯函数
- **反模式**（✱ 关键）
  - ❌ `if "design error" in llm_output: invalid`
  - ❌ 用模糊比对（应严格 deep_equal，可控容差）
- **关键测试**
  - `test_strict_deep_equal`
  - `test_numeric_tolerance`
  - `test_ignore_paths`
  - `test_path_reporting_accurate`

------

#### 4.2.4 `failure-attribution`（失败归因）

- **限界上下文**：Phase1
- **部署位置**：Worker
- **依赖**：llm-agent-loop（可选，用于辅助归因）
- **被依赖**：scenario-engine
- **核心职责**
  1. 当 scenario 失败时，归因到三类问题：
     - `design_bug`: 设计本身有缺陷（用户应该改图）
     - `scenario_bug`: 测试场景定义有误（用户应该改 expected）
     - `simulator_bug`: 模拟器实现错误（开发者应该修代码）
     - `unknown`: 无法判断
  2. 算法：先用规则过滤明显模式 → 再用 LLM 辅助分类
  3. **强制结构化输出**：LLM 返回必须符合 schema，不允许自由文本
- **公开接口**

```python
class FailureAttributor:
    def __init__(self, agent: LLMAgent): ...

    async def attribute(
        self,
        scenario: Scenario,
        actual: Mapping[str, Any],
        mismatch: list[MismatchPath],
        node_outputs: Mapping[str, dict],
        forest: CascadeForest,
    ) -> tuple[str, str]:   # (attribution, reason)
        """先规则后 LLM；LLM 强制 forced_output_schema"""
```

- **分布式考虑**：可缓存（按场景+森林+actual 的 hash）
- **反模式**
  - ❌ 让 LLM 用自然语言下结论（应 forced schema）
- **关键测试**
  - `test_rule_based_obvious_simulator_bug`
  - `test_llm_forced_schema_attribution`

------

#### 4.2.5 `handler-chain`（Handler 链框架）

- **限界上下文**：Phase1
- **部署位置**：shared lib
- **依赖**：trace-bus, phase-state-machine
- **被依赖**：pipeline-builder
- **核心职责**
  1. 定义 `HandlerStep` 抽象基类（`name`, `handler_order`, `_handle`）
  2. 链式调度：按 `handler_order` 执行；任一失败短路
  3. 每个 Handler 的 trace 独立记录（`HandlerTrace`）
  4. 提供 `HandlerRegistry` 支持插件化新增 Handler
  5. 决策结果统一收口到 `phase-state-machine`
- **关键模型**

```python
@dataclass(frozen=True)
class HandlerOutcome:
    decision: Literal["pass", "fail"]
    reason: str
    issues: list[ValidationIssue]
    extra: Mapping[str, Any] = field(default_factory=dict)

class HandlerStep(ABC):
    name: ClassVar[str]
    handler_order: ClassVar[int]

    async def __call__(
        self, state: CascadeState, trace: TraceEmitter
    ) -> CascadeState:
        outcome = await self._handle(state, trace)
        return self._merge(state, outcome)

    @abstractmethod
    async def _handle(
        self, state: CascadeState, trace: TraceEmitter
    ) -> HandlerOutcome: ...

class HandlerRegistry:
    def register(self, handler: type[HandlerStep]) -> None: ...
    def list_ordered(self) -> list[type[HandlerStep]]: ...

class HandlerChainExecutor:
    async def run(
        self, state: CascadeState, registry: HandlerRegistry, trace: TraceEmitter
    ) -> CascadeState:
        """按 order 串行；fail 立即短路；每个 Handler 写一条 RunStep"""
```

- **状态机**：见 §7.3（Phase1 Handler 链状态机）
- **扩展点**
  - 新 Handler：实现 `HandlerStep` 子类 + `registry.register()`
  - 例：未来加 `coverage_check` Handler 检查场景覆盖率
- **分布式考虑**
  - 每个 Handler 独立可重试；前面 Handler 通过的可缓存
  - Handler 之间通过 state 通信，不持有跨调用状态
- **反模式**
  - ❌ Handler 内部直接修改 `state["phase1_verdict"]`（应通过 outcome）
  - ❌ 多 Handler 写同一字段竞争
- **关键测试**
  - `test_chain_short_circuits_on_first_fail`
  - `test_dynamic_handler_registration`
  - `test_each_handler_emits_run_step`

------

#### 4.2.6 `phase1-reflector`（SDD/TDD 反思循环）

- **限界上下文**：Phase1
- **部署位置**：Worker
- **依赖**：llm-agent-loop, scenario-engine, forest-structure
- **被依赖**：handler-chain（作为 Handler 内部调用）
- **核心职责**
  1. 当 scenario_run Handler 判定 FAIL 后，驱动 SDD/TDD 反思循环
  2. SDD（Specification-Driven Development）反思：修改节点 field_values → 重跑场景
  3. TDD（Test-Driven Development）反思：添加新 scenario → 重跑场景
  4. 反思循环最多 3 次迭代（可配置）
  5. 反思结果通过 forced_output_schema 获取（不允许自由文本判断）
  6. 记录每次反思的决策和修改到 RunStep
- **关键模型**

```python
class ReflectionDecision(str, Enum):
    FIX_SPEC = "fix_spec"       # SDD：修改节点定义
    ADD_SCENARIO = "add_scenario"  # TDD：添加测试场景
    GIVE_UP = "give_up"        # 放弃，标记为 FAIL

@dataclass(frozen=True)
class ReflectionOutcome:
    decision: ReflectionDecision
    modifications: list[dict]   # field_value 修改列表 / 新增 scenario 列表
    reason: str
    iteration: int

class Phase1Reflector:
    MAX_ITERATIONS: ClassVar[int] = 3

    async def reflect_loop(
        self,
        state: CascadeState,
        failed_scenario_results: list[ScenarioResult],
        trace: TraceEmitter,
    ) -> CascadeState:
        """
        反思循环：
        1. LLM 分析失败原因 → ReflectionDecision
        2. 应用修改（fix_spec 或 add_scenario）
        3. 重新执行场景
        4. 仍失败 → 下一轮迭代（最多 MAX_ITERATIONS 次）
        5. 仍失败 → give_up
        """

    async def _analyze_failure(
        self,
        results: list[ScenarioResult],
        state: CascadeState,
    ) -> ReflectionOutcome:
        """forced_output_schema 获取反思决策"""
```

- **状态机**：嵌入在 §7.3（Phase1 Handler 链状态机）的 SDD/TDD 内层循环
- **领域事件**：`ReflectionStarted`, `ReflectionDecisionMade`, `ReflectionIterationFinished`
- **分布式考虑**
  - 反思循环在单 Worker 内串行执行
  - 每次迭代结束持久化 state（含 modifications）用于崩溃恢复
- **反模式**
  - ❌ 在 handler-chain 或 scenario-engine 中直接实现反思逻辑（应收口到本模块）
  - ❌ LLM 自由文本判断"修改什么"（必须 forced schema）
- **关键测试**
  - `test_sdd_fixes_field_value_and_reruns`
  - `test_tdd_adds_scenario_and_reruns`
  - `test_max_iterations_gives_up`
  - `test_reflection_decision_forced_schema`

------

## 第 5 章 Phase2 / Phase3 / Review 域模块详细设计

### 5.1 Phase2 域模块（5 个）

#### 5.1.1 `code-planner`（代码骨架规划）

- **限界上下文**：Phase2
- **部署位置**：Worker
- **依赖**：dag-compute, llm-agent-loop
- **被依赖**：pipeline-builder
- **核心职责**
  1. 基于 `parsed_forest` 和 `dag-compute` 结果，规划代码模块结构
  2. 确定 Bundle → class/namespace 的映射规则
  3. 确定节点实例 → 函数/方法的映射规则
  4. 确定边 → 调用/跳转关系
  5. 输出 `CodeSkeleton`（代码结构规划结果，供 code-generator 使用）
  6. **D3A 留白点**：映射规则目前是抽象的，具体 D3A 指令到 C++ 代码的映射模板后续填充
- **关键模型**

```python
@dataclass(frozen=True)
class CodeSkeleton:
    modules: tuple[CodeModule, ...]      # 顶层模块列表
    bundle_order: tuple[str, ...]      # 按拓扑序的 bundle 名单
    node_to_function: Mapping[str, str] # instance_id → 函数名
    bundle_to_class: Mapping[str, str] # bundle_id → 类名

@dataclass(frozen=True)
class CodeModule:
    name: str
    type: Literal["header", "source", "main"]
    dependencies: tuple[str, ...]
    included_instances: tuple[str, ...]
```

- **公开接口**

```python
class CodePlannerStep(BasePipelineStep):
    name = "code_planner"
    phase = 2

    async def _do(self, state: CascadeState) -> CascadeState:
        skeleton = self._plan(state["parsed_forest"], state["scenarios"])
        state["code_skeleton"] = asdict(skeleton)
        return state
```

- **分布式考虑**：纯函数，输入相同输出相同，可按 `forest_snapshot_hash` 缓存
- **关键测试**
  - `test_bundle_order_matches_topo_sort`
  - `test_skleton_deterministic`

------

#### 5.1.2 `code-generator`（按 Bundle 生成）

- **限界上下文**：Phase2
- **部署位置**：Worker
- **依赖**：codegen-target, llm-agent-loop, node-registry
- **被依赖**：code-assembler
- **核心职责**
  1. 对每个 Bundle，调用 `codegen-target` 按模板生成代码片段
  2. 对每个 NodeInstance，调用 LLM 生成节点内联代码（使用 `template_snapshot.code_hints`）
  3. 输出 `CodeUnit` 列表
  4. **D3A 留白点**：具体 D3A 节点 → C++ 代码的 prompt 模板和生成规则在 `codegen-target` 中预留
- **关键模型**

```python
@dataclass
class CodeUnit:
    bundle_id: str
    bundle_name: str
    language: str                    # "cpp"
    filepath: str
    code: str
    node_instances: tuple[str, ...]
    hash: str                        # 用于缓存验证
```

- **公开接口**

```python
class CodeGeneratorStep(BasePipelineStep):
    name = "code_generator"
    phase = 2

    async def _do(self, state: CascadeState) -> CascadeState:
        units = []
        for bundle_id in state["code_skeleton"]["bundle_order"]:
            unit = await self._generate_bundle(bundle_id, state)
            units.append(asdict(unit))
        state["code_units"] = units
        return state
```

- **状态机**：见 §7.4（Phase2 代码生成状态机）
- **扩展点**
  - 新语言目标：实现 `CodegenTarget` 子类 + 注册工厂
  - 例：未来加 `RustCodegenTarget` 只需新增类，不动 code-generator 逻辑
- **分布式考虑**
  - 跨 Bundle 并行生成（独立 CodeUnit）
  - 同 Bundle 内节点串行（依赖代码顺序）
  - 生成结果可按 `CodeUnit.hash` 缓存（相同输入相同代码）
- **反模式**
  - ❌ 直接拼接字符串生成代码（必须通过 CodegenTarget 模板）
  - ❌ 跨 Bundle 共享状态
- **关键测试**
  - `test_parallel_bundle_generation`
  - `test_hash_cache_hit`

------

#### 5.1.3 `code-assembler`（组装完整程序）

- **限界上下文**：Phase2
- **部署位置**：Worker
- **依赖**：codegen-target
- **被依赖**：pipeline-builder
- **核心职责**
  1. 将所有 `CodeUnit` 按 `code_skeleton` 组装成完整可编译的程序
  2. 生成 `main.cpp` / `CMakeLists.txt` 等工程文件
  3. 输出 `composite_code: dict[str, str]`（filepath → content）
  4. 生成编译命令和参数
  5. **D3A 留白点**：主函数模板、D3A 入口点模板后续填充
- **公开接口**

```python
class CodeAssemblerStep(BasePipelineStep):
    name = "code_assembler"
    phase = 2

    async def _do(self, state: CascadeState) -> CascadeState:
        composite = self._assemble(
            state["code_units"],
            state["code_skeleton"],
        )
        state["composite_code"] = composite
        return state
```

- **分布式考虑**：纯函数
- **关键测试**
  - `test_assemble_produces_valid_cmake`
  - `test_assemble_includes_all_units`

------

#### 5.1.4 `code-snapshot`（代码快照存储）

- **限界上下文**：Phase2
- **部署位置**：Worker
- **依赖**：mysql-store
- **被依赖**：code-generator（保存快照）
- **核心职责**
  1. 每次完整代码生成（或重大修复后）保存一个 `CodeSnapshot`
  2. 快照内容：`files`（dict）、`overall_hash`、`issues_fixed`、`node_to_code`
  3. 支持按 `overall_hash` 去重（相同代码仅存一份）
  4. 支持快照间的 `issues_fixed` diff
- **关键模型**

```python
class CodeSnapshot:
    id: str                         # cs_xxxxxxxx
    run_id: str
    iteration: int                   # 0 = initial, 1+ = fixed
    source: Literal["initial", "fixed_after_static", "fixed_after_dynamic"]
    files: Mapping[str, str]          # filepath → content
    overall_hash: str                # SHA256(all files)
    issues_fixed: tuple[dict, ...]
    node_to_code: Mapping[str, str]  # instance_id → 代码片段
    created_at: datetime
```

- **公开接口**

```python
class CodeSnapshotRepository:
    async def save(self, snapshot: CodeSnapshot) -> str: ...
    async def get(self, snapshot_id: str) -> CodeSnapshot | None: ...
    async def get_by_hash(self, hash: str) -> CodeSnapshot | None: ...
    async def list_by_run(self, run_id: str) -> list[CodeSnapshot]: ...
```

- **状态机**：见 §7.4
- **分布式考虑**：快照按 hash 去重，同一代码跨 Run 共享
- **关键测试**
  - `test_hash_dedup_identical_code`
  - `test_iteration_tracking`

------

#### 5.1.5 `codegen-target`（代码生成目标抽象）

- **限界上下文**：Phase2
- **部署位置**：shared lib
- **依赖**：（无）
- **被依赖**：code-generator, code-assembler
- **核心职责**
  1. 定义 `CodegenTarget` 接口（抽象层，不绑定具体语言）
  2. 提供 `CppCodegenTarget` 默认实现
  3. 管理代码模板（文件模板、类模板、函数签名模板）
  4. **D3A 留白点**：D3A 指令 → C++ 代码的具体映射模板在此定义和加载
  5. 版本化的目标语言定义（同一 Target 可有多个版本）
- **关键模型**

```python
class CodegenTarget(ABC):
    language: ClassVar[str]

    @abstractmethod
    def bundle_class_template(self, bundle: Bundle, nodes: list[NodeInstance]) -> str: ...

    @abstractmethod
    def node_function_template(self, node: NodeInstance, edges: list[Edge]) -> str: ...

    @abstractmethod
    def entry_point_template(self, skeleton: CodeSkeleton) -> str: ...

    @abstractmethod
    def cmake_template(self, skeleton: CodeSkeleton) -> str: ...

class CppCodegenTarget(CodegenTarget):
    language = "cpp"
    # 具体的 C++ 模板实现
    # D3A 指令相关的模板也在此（待定）
```

- **扩展点**（✱ 关键扩展性机制）
  - 加新语言：实现 `CodegenTarget` 子类即可
  - 换模板：在不换语言的情况下换一套模板（如 D3A v1 vs v2）
- **分布式考虑**：纯函数
- **反模式**
  - ❌ 在 code-generator 中硬编码 C++ 字符串拼接（应走模板）
  - ❌ D3A 映射逻辑耦合在 code-generator（应全在 CodegenTarget 里）
- **关键测试**
  - `test_cpp_target_produces_valid_code`
  - `test_template_swappable`

------

### 5.2 Phase3 域模块（7 个）

#### 5.2.1 `static-reflector`（静态反思）

- **限界上下文**：Phase3
- **部署位置**：Worker
- **依赖**：llm-agent-loop, schema-engine
- **被依赖**：fix-loop-controller
- **核心职责**
  1. 对 `composite_code` 做静态分析（通过 LLM 或规则引擎）
  2. 检测编译错误、链接错误、类型错误
  3. 输出 `static_issues: list[StaticIssue]`
  4. 判断：有 issue → 回修代码；无 issue → 进入编译
  5. **强制 forced_output_schema**：LLM 返回必须符合 IssueListSchema，不允许自然语言
- **关键模型**

```python
@dataclass(frozen=True)
class StaticIssue:
    severity: Literal["error", "warning", "info"]
    file: str
    line: int | None
    message: str
    code: str                        # 错误码，如 "UNUSED_VAR"
    can_auto_fix: bool
    fix_suggestion: str | None
```

- **公开接口**

```python
class StaticReflectorStep(BasePipelineStep):
    name = "outer_static_reflector"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        issues = await self._reflect(state["composite_code"], state["code_skeleton"])
        state["static_issues"] = [asdict(i) for i in issues]
        return state
```

- **状态机**：见 §7.6（Phase3 外层修复循环）
- **分布式考虑**：可按 `overall_hash` 缓存 static_issues 结果
- **反模式**
  - ❌ LLM 返回自由文本让 Worker 自己解析（必须 forced schema）
- **关键测试**
  - `test_forced_schema_issues_list`
  - `test_cache_by_code_hash`

------

#### 5.2.2 `sandbox-provisioner`（沙箱编排）

- **限界上下文**：Phase3
- **部署位置**：Worker（sandbox 节点）
- **依赖**：sandbox-runtime
- **被依赖**：fix-loop-controller
- **核心职责**
  1. 管理沙箱容器生命周期：provision → ready → destroyed
  2. 从容器池中借出容器，用完归还
  3. 容器资源配额：CPU、内存、磁盘、网络（隔离网络）
  4. 容器清理策略：超时自动杀、网络隔离保证
  5. 异常容器检测与隔离
- **公开接口**

```python
class SandboxProvisioner:
    async def acquire(self, run_id: str, image: str) -> ContainerHandle: ...
    async def release(self, handle: ContainerHandle) -> None: ...
    async def destroy(self, handle: ContainerHandle) -> None: ...
    async def health_check(self, handle: ContainerHandle) -> bool: ...
```

- **状态机**：见 §7.10（Sandbox Container 状态机）
- **分布式考虑**
  - 容器池：预先启动 N 个 warm 容器，避免每次启动延迟
  - 容器分配：Redis 分布式锁 `lock:container:{handle_id}`
  - 孤儿容器清理：Cron 任务扫描超30分钟未归还的容器
- **反模式**
  - ❌ Worker 直接调 Docker SDK（应走 sandbox-runtime 抽象）
  - ❌ 容器不归还（资源泄漏）
- **关键测试**
  - `test_container_pool_exhaustion_handling`
  - `test_orphan_container_cleanup`
  - `test_container_isolation_enforced`

------

#### 5.2.3 `sandbox-compiler`（编译引擎）

- **限界上下文**：Phase3
- **部署位置**：Worker（sandbox 节点）
- **依赖**：sandbox-runtime
- **被依赖**：fix-loop-controller
- **核心职责**
  1. 在沙箱容器中执行编译（cmake + make）
  2. 捕获 stdout / stderr / exit_code
  3. 编译产物哈希校验
  4. 超时控制（默认 5 分钟）
  5. 输出 `CompileResult`
- **关键模型**

```python
@dataclass(frozen=True)
class CompileResult:
    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    artifacts: Mapping[str, str]     # binary_name → container 内路径
    duration_ms: int
    overall_hash: str               # 所有 artifacts 的合并 hash
```

- **公开接口**

```python
class SandboxCompilerStep(BasePipelineStep):
    name = "sandbox_compiler"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        result = await self._compile(state["composite_code"], state["sandbox_handle"])
        state["compile_result"] = asdict(result)
        return state
```

- **状态机**：见 §7.6（编译子状态机）
- **幂等性**：相同 `composite_code` 的编译结果可按 `overall_hash` 缓存
- **分布式考虑**
  - 编译占用资源重，容器独占；通过 Redis 队列限流
  - 编译失败不阻塞修复循环（进反思 → 回修代码）
- **关键测试**
  - `test_compile_success_capture_artifacts`
  - `test_compile_timeout_kills_container`
  - `test_hash_stable_across_runs`

------

#### 5.2.4 `sandbox-executor`（执行引擎）

- **限界上下文**：Phase3
- **部署位置**：Worker（sandbox 节点）
- **依赖**：sandbox-runtime
- **被依赖**：fix-loop-controller
- **核心职责**
  1. 在编译产物中执行测试用例
  2. 支持 stdin / file input 两种输入模式
  3. 捕获 stdout / stderr / exit_code / signal / duration
  4. 超时控制（单用例默认 30s）
  5. 输出 `ExecutionResult`
- **关键模型**

```python
@dataclass(frozen=True)
class ExecutionResult:
    case_id: str
    verdict: Literal["pass", "fail", "error", "timeout"]
    stdout: bytes
    stderr: bytes
    exit_code: int
    signal: str | None
    duration_ms: int
    error: str | None
```

- **公开接口**

```python
class SandboxExecutorStep(BasePipelineStep):
    name = "sandbox_executor"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        results = await self._execute(
            state["compile_result"],
            state["sandbox_cases"],
            state["sandbox_handle"],
        )
        state["execution_results"] = [asdict(r) for r in results]
        return state
```

- **分布式考虑**
  - 用例间并行（独立 ExecutionResult）
  - 容器隔离：每个 Run 的执行在独立容器，网络完全隔离
  - 资源计量：记录 CPU / 内存峰值用于计费
- **关键测试**
  - `test_case_timeout_enforced`
  - `test_isolation_between_cases`
  - `test_result_serialization_stable`

------

#### 5.2.5 `case-synthesizer`（用例合成）

- **限界上下文**：Phase3
- **部署位置**：Worker
- **依赖**：llm-agent-loop
- **被依赖**：fix-loop-controller
- **核心职责**
  1. 基于 Phase1 的场景执行结果，合成 Phase3 沙箱用例
  2. 生成 `SandboxCase` 列表（input_bytes / input_spec + expected）
  3. **D3A 留白点**：D3A 格式的用例合成规则（如输入二进制格式、expected 格式）后续填充
  4. 保证用例覆盖度（每个 DAG 路径至少一个用例）
- **关键模型**

```python
@dataclass
class SandboxCase:
    id: str
    run_id: str
    scenario_name: str
    input_bytes: bytes | None
    input_spec: dict                 # JSON Schema for input
    expected: Mapping[str, Any]
    actual: Mapping[str, Any] | None
    verdict: Literal["pass", "fail", "error", "timeout"] | None
    duration_ms: int
    timeout_seconds: int = 30
```

- **公开接口**

```python
class CaseSynthesizerStep(BasePipelineStep):
    name = "outer_scenario_synthesizer"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        cases = await self._synthesize(
            state["scenario_results"],
            state["code_skeleton"],
        )
        state["sandbox_cases"] = [asdict(c) for c in cases]
        return state
```

- **分布式考虑**：纯函数，可按 scenario_results hash 缓存
- **关键测试**
  - `test_coverage_each_dag_path`
  - `test_d3a_format_respected`（D3A 定后补）

------

#### 5.2.6 `dynamic-reflector`（动态反思 + 决策）

- **限界上下文**：Phase3
- **部署位置**：Worker
- **依赖**：llm-agent-loop
- **被依赖**：fix-loop-controller
- **核心职责**
  1. 分析 `execution_results`，判断 verdict
  2. 决策：done / design_bug / fix_code
  3. 如果是 design_bug，生成归因报告
  4. 如果是 fix_code，给出修改建议
  5. **强制 forced_output_schema**：禁止自由文本推断 verdict
- **公开接口**

```python
class DynamicReflectorStep(BasePipelineStep):
    name = "outer_dynamic_reflector"
    phase = 3

    async def _do(self, state: CascadeState) -> CascadeState:
        verdict, reason, fix = await self._reflect(
            state["execution_results"],
            state["code_skeleton"],
        )
        state["decision"] = verdict
        state["fix_suggestion"] = fix
        return state
```

- **状态机**：见 §7.5（Phase3 动态反思）
- **分布式考虑**：可按 `(code_hash, execution_results_hash)` 缓存
- **反模式**
  - ❌ 从 LLM 自然语言输出推断 verdict（必须 forced schema）
- **关键测试**
  - `test_verdict_determined_by_schema_not_text`

------

#### 5.2.7 `fix-loop-controller`（修复循环控制器）

- **限界上下文**：Phase3
- **部署位置**：Worker
- **依赖**：phase-state-machine, sandbox-provisioner
- **被依赖**：pipeline-builder
- **核心职责**
  1. 控制 Phase3 外层修复循环（`outer_fix_iter` ∈ [0, MAX]）
  2. 每个 iteration：static → compile → synthesize → execute → dynamic
  3. 超过 MAX 迭代次数 → `fix_exhausted`
  4. 迭代状态持久化（崩溃恢复）
  5. 与 `phase-state-machine` 交互，驱动整体 Phase3 verdict
- **公开接口**

```python
class FixLoopController:
    async def run_iteration(
        self,
        state: CascadeState,
        ctx: SimContext,
    ) -> tuple[CascadeState, bool]:   # (state, should_continue)
        """
        返回 (state, should_continue)
        should_continue = False → 修复循环结束
        """

    def can_continue(self, state: CascadeState) -> bool:
        return (
            state["decision"] == "fix_code"
            and state["outer_fix_iter"] < MAX_FIX_ITER
        )
```

- **状态机**：见 §7.5（Phase3 外层修复循环状态机）
- **持久化**：每个 iteration 结束后立即持久化 state（含 `outer_fix_iter`）
- **分布式考虑**
  - 单 Worker 串行执行一个 Run 的所有 iteration（避免竞态）
  - 崩溃恢复：按 `outer_fix_iter` 重启迭代
- **反模式**
  - ❌ 不持久化 iteration 状态（崩溃后丢失进度）
- **关键测试**
  - `test_iteration_persists_on_each_step`
  - `test_exhaust_after_max_iterations`
  - `test_crash_recovery_continues_from_iter`

------

### 5.3 Review 域模块（2 个）

#### 5.3.1 `review-workflow`（评审工作流）

- **限界上下文**：Review
- **部署位置**：API
- **依赖**：mysql-store
- **被依赖**：api-gateway
- **核心职责**
  1. 管理评审生命周期（发起 → 评审中 → 通过/拒绝/需修改）
  2. 与 `WorkflowRun` 关联
  3. 强制状态机（不支持跳过状态）
  4. 支持多轮评审（需修改 → 重新提交 → 再次评审）
- **关键模型**

```python
class ReviewStatus(str, Enum):
    NONE = "none"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"

@dataclass
class GraphReview:
    id: str                         # rv_xxxxxxxx
    run_id: str
    reviewer_id: int
    verdict: ReviewStatus | None
    summary: str
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

- **公开接口**

```python
class ReviewWorkflowService:
    async def initiate(self, run_id: str, reviewer_id: int) -> GraphReview: ...
    async def approve(self, review_id: str, summary: str) -> GraphReview: ...
    async def reject(self, review_id: str, summary: str) -> GraphReview: ...
    async def request_revision(self, review_id: str, summary: str) -> GraphReview: ...
    async def get_by_run(self, run_id: str) -> GraphReview | None: ...
```

- **状态机**：见 §7.9（Review 状态机）
- **领域事件**：`ReviewInitiated`, `ReviewApproved`, `ReviewRejected`, `ReviewRevisionRequested`
- **分布式考虑**：乐观锁保护并发评审（reviewer_id + version）
- **关键测试**
  - `test_cannot_skip_status`
  - `test_multi_round_review`

------

#### 5.3.2 `review-comment`（批注系统）

- **限界上下文**：Review
- **部署位置**：API
- **依赖**：mysql-store
- **被依赖**：api-gateway
- **核心职责**
  1. 对节点实例 / Bundle / 边 / 图 级别添加批注
  2. 批注的解析状态（resolved / unresolved）
  3. 支持回复（嵌套批注）
  4. 批注变更历史
- **关键模型**

```python
@dataclass
class ReviewComment:
    id: str                         # cm_xxxxxxxx
    review_id: str
    author_id: int
    parent_id: str | None           # 回复嵌套
    target_type: Literal["node_instance", "bundle", "edge", "graph"]
    target_ref: str                  # instance_id / bundle_id / ...
    body: str
    resolved: bool
    resolved_by: int | None
    resolved_at: datetime | None
    created_at: datetime
```

- **公开接口**

```python
class ReviewCommentService:
    async def add(self, review_id: str, dto: CommentCreateDTO) -> ReviewComment: ...
    async def resolve(self, comment_id: str, by_user: int) -> ReviewComment: ...
    async def list_by_review(self, review_id: str) -> list[ReviewComment]: ...
```

- **领域事件**：`CommentAdded`, `CommentResolved`
- **分布式考虑**：评论操作最终一致
- **关键测试**
  - `test_nested_comments_retrieved_together`
  - `test_resolve_is_idempotent`

------

## 第 6 章 应用层 / 集成层 / 横切关注点 / 基础设施

### 6.1 Application Layer（应用层 — 5 个模块）

#### 6.1.1 `api-gateway`（API 网关）

- **限界上下文**：Application
- **部署位置**：API Node
- **依赖**：所有 Domain 模块, auth-rbac, idempotency
- **被依赖**：外部客户端（HTTP/WS）
- **核心职责**
  1. 接收所有 REST 请求，路由到对应 Domain Service
  2. 请求 DTO 校验（pydantic）
  3. 认证（JWT / Session）→ `auth-rbac` 鉴权
  4. 幂等键处理（从 `Idempotency-Key` header 提取）
  5. 响应 DTO 转换
  6. OpenAPI / Swagger 文档生成
  7. **统一分页、过滤、排序规范**
  8. **统一错误响应格式**
  9. **API 版本化**
- **API 版本化**

```
所有路由前缀 /api/v1/
未来不兼容变更 → /api/v2/（保留 v1 6 个月）
版本号仅在路由前缀体现，不走 Header
```

- **统一请求/响应规范**

```python
# 分页请求
class PaginationParams:
    page: int = 1              # 1-based
    page_size: int = 20        # max 100
    sort_by: str = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"

# 分页响应
class PagedResponse[T]:
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool

# 统一错误响应
class ErrorResponse:
    error_code: str            # 见附录 B
    message: str
    details: dict | None
    trace_id: str              # 贯穿 trace_id
    timestamp: str

# HTTP 状态码规范
# 200 OK — 成功（含业务失败，如 verdict=invalid）
# 201 Created — 创建成功
# 202 Accepted — 异步任务已接受
# 400 Bad Request — DTO 校验失败
# 401 Unauthorized — 认证失败
# 403 Forbidden — 鉴权失败
# 404 Not Found — 资源不存在
# 409 Conflict — 幂等冲突 / 乐观锁冲突
# 429 Too Many Requests — 限流
# 500 Internal Server Error — 未处理异常
# 503 Service Unavailable — 依赖不可用
# 504 Gateway Timeout — 超时
```

- **完整路由设计（55 条）**

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  Graph 域路由（11 条）                                                          ║
╠═══════════╦═══════════════════════════════════════╦════════════════════════════╣
║ 方法      ║ 路径                                  ║ 说明                       ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║ POST      ║ /api/v1/graphs                        ║ 创建图                     ║
║ GET       ║ /api/v1/graphs                        ║ 列表图（分页+过滤）        ║
║ GET       ║ /api/v1/graphs/{id}                   ║ 获取图详情                 ║
║ PUT       ║ /api/v1/graphs/{id}                   ║ 更新图元信息               ║
║ DELETE    ║ /api/v1/graphs/{id}                   ║ 软删除图                   ║
║ POST      ║ /api/v1/graphs/{id}/versions          ║ 保存新版本                 ║
║ GET       ║ /api/v1/graphs/{id}/versions          ║ 列表版本（分页）           ║
║ GET       ║ /api/v1/graphs/{id}/versions/{vid}    ║ 获取单个版本详情           ║
║ POST      ║ /api/v1/graphs/{id}/versions/{vid}/validate ║ 触发版本验证        ║
║ POST      ║ /api/v1/graphs/{id}/versions/{vid}/archive  ║ 归档版本           ║
║ GET       ║ /api/v1/graphs/{id}/diff              ║ 版本 Diff（?v1=&v2=）     ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║  Run 域路由（10 条）                                                            ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║ POST      ║ /api/v1/runs                          ║ 触发 Run（Idem-Key）       ║
║ GET       ║ /api/v1/runs                          ║ 列表 Run（分页+状态过滤）  ║
║ GET       ║ /api/v1/runs/{id}                     ║ 查询 Run 详情              ║
║ POST      ║ /api/v1/runs/{id}/cancel              ║ 取消 Run                   ║
║ POST      ║ /api/v1/runs/{id}/retry               ║ 重新触发（基于同一版本）   ║
║ GET       ║ /api/v1/runs/{id}/steps               ║ 步骤历史（分页）           ║
║ GET       ║ /api/v1/runs/{id}/steps/{sid}         ║ 单步骤详情                 ║
║ GET       ║ /api/v1/runs/{id}/state               ║ 当前 CascadeState 快照     ║
║ GET       ║ /api/v1/runs/{id}/trace               ║ Trace 详情                 ║
║ GET       ║ /api/v1/runs/{id}/code-snapshots      ║ 关联的代码快照列表         ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║  Template 域路由（12 条）                                                       ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║ POST      ║ /api/v1/templates                     ║ 创建模板（草稿）           ║
║ GET       ║ /api/v1/templates                     ║ 搜索模板（分页+分类+Scope）║
║ GET       ║ /api/v1/templates/{id}                ║ 获取模板详情               ║
║ PUT       ║ /api/v1/templates/{id}                ║ 更新模板（草稿状态）       ║
║ DELETE    ║ /api/v1/templates/{id}                ║ 软删除模板                 ║
║ POST      ║ /api/v1/templates/{id}/publish        ║ 发布模板（DRAFT→ACTIVE）   ║
║ POST      ║ /api/v1/templates/{id}/deprecate      ║ 废弃模板（ACTIVE→DEPRECATED）║
║ POST      ║ /api/v1/templates/{id}/fork           ║ Fork 为私有模板            ║
║ GET       ║ /api/v1/templates/{id}/versions       ║ 模板版本历史               ║
║ POST      ║ /api/v1/templates/import              ║ 批量导入（JSON Pack）      ║
║ POST      ║ /api/v1/templates/export              ║ 批量导出（JSON Pack）      ║
║ POST      ║ /api/v1/templates/{id}/simulate       ║ 试运行模拟器               ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║  Review 域路由（9 条）                                                          ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║ POST      ║ /api/v1/reviews                       ║ 发起评审                   ║
║ GET       ║ /api/v1/reviews                       ║ 列表评审（分页+状态过滤）  ║
║ GET       ║ /api/v1/reviews/{id}                  ║ 获取评审详情               ║
║ POST      ║ /api/v1/reviews/{id}/approve          ║ 通过评审                   ║
║ POST      ║ /api/v1/reviews/{id}/reject           ║ 拒绝评审                   ║
║ POST      ║ /api/v1/reviews/{id}/request-revision ║ 请求修改                   ║
║ POST      ║ /api/v1/reviews/{id}/comments         ║ 添加批注                   ║
║ GET       ║ /api/v1/reviews/{id}/comments         ║ 列表批注                   ║
║ POST      ║ /api/v1/comments/{id}/resolve         ║ 解决批注                   ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║  管理 / 运维路由（8 条）                                                        ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║ GET       ║ /api/v1/users/me                      ║ 当前用户信息               ║
║ GET       ║ /api/v1/admin/users                   ║ 用户管理（admin）          ║
║ PUT       ║ /api/v1/admin/users/{id}/role         ║ 修改角色（admin）          ║
║ GET       ║ /api/v1/admin/feature-flags           ║ 特性开关列表               ║
║ PUT       ║ /api/v1/admin/feature-flags/{key}     ║ 修改开关                   ║
║ GET       ║ /api/v1/admin/audit-logs              ║ 审计日志查询               ║
║ GET       ║ /health                               ║ 健康检查                   ║
║ GET       ║ /metrics                              ║ Prometheus scrape          ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║  WebSocket 路由（3 条）                                                         ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║ WS        ║ /ws/runs/{id}                         ║ Run 实时状态推送           ║
║ WS        ║ /ws/runs/{id}/logs                    ║ Run 实时日志流             ║
║ WS        ║ /ws/reviews/{id}                      ║ 评审实时协作               ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║  辅助路由（2 条）                                                               ║
╠═══════════╬═══════════════════════════════════════╬════════════════════════════╣
║ GET       ║ /api/v1/schemas/{name}                ║ 获取 JSON Schema 定义      ║
║ GET       ║ /api/v1/stats/dashboard               ║ 统计面板数据               ║
╚═══════════╩═══════════════════════════════════════╩════════════════════════════╝
```

- **限流策略**

```
全局：1000 req/min per API Node
按用户：100 req/min per user_id
写操作（POST/PUT/DELETE）：30 req/min per user_id
Run 触发：10 req/min per user_id（防止滥用）
模板导入：2 req/min per user_id（大操作）
```

- **持久化**：无（透传 Domain）
- **分布式考虑**
  - 无状态，水平扩展
  - DB 连接池（每节点 20-50 连接）
  - 请求超时（5s 读 / 30s 写）
  - 所有响应携带 `X-Trace-Id` header
  - 所有列表接口支持 `?fields=` 字段选择（减少传输量）
- **关键测试**
  - `test_auth_rejected_without_token`
  - `test_idempotency_key_propagates`
  - `test_pagination_boundary`
  - `test_error_response_format`
  - `test_rate_limit_enforcement`
  - `test_api_version_routing`

------

#### 6.1.2 `websocket-pusher`（实时推送）

- **限界上下文**：Application
- **部署位置**：API Node
- **依赖**：redis-pubsub
- **被依赖**：worker-runtime（发布事件）
- **核心职责**
  1. 维护 WebSocket 连接池（`run_id → set[client_id]`）
  2. 订阅 Redis Pub/Sub 的 `run.*` 频道
  3. 事件路由到对应 Run 的所有在线客户端
  4. 心跳保活（30s ping/pong）
  5. 重连后支持补发最近 N 条事件
- **消息格式**

```json
{
  "type": "run.updated",
  "run_id": "r_xxx",
  "data": {
    "status": "running",
    "phase": 1,
    "verdict": null,
    "updated_at": "2026-04-27T..."
  }
}
```

- **消息类型**：`run.created`, `run.started`, `run.step_finished`, `run.phase_finished`, `run.finished`, `run.cancelled`, `run.failed`
- **分布式考虑**
  - Redis Pub/Sub 做扇出（1 发布 → N 订阅）
  - 连接按 `run_id` 路由，减少无效广播
  - 客户端断线：自动清理（心跳超时检测）
- **反模式**
  - ❌ 在 WebSocket 消息中放敏感数据（只有 Run 状态，不含代码/Schema）
- **关键测试**
  - `test_client_receives_all_events`
  - `test_reconnect_catches_up`

------

#### 6.1.3 `worker-runtime`（Worker 运行时）

- **限界上下文**：Application
- **部署位置**：Worker Node
- **依赖**：celery, 所有 Phase Domain 模块, phase-state-machine
- **被依赖**：celery beat（调度任务）
- **核心职责**
  1. 从 Redis 队列消费任务（`phase1_queue`, `phase2_queue`, `phase3_queue`, `low_priority_queue`）
  2. 加载 `WorkflowRun`（with lock）→ 初始化 `CascadeState`
  3. 调用 `phase-state-machine.next_phase()` 确定当前阶段
  4. 调度对应 Phase 的 Step 链
  5. 每个 Step 起止更新 RunStep + MongoDB Trace
  6. 阶段完成后更新 `WorkflowRun` 状态（via `phase-state-machine`）
  7. 崩溃恢复：从 MongoDB 恢复最近 Step，重新执行
- **任务路由**

```python
@celery.task(bind=True, max_retries=3)
def execute_run(self, run_id: str, resume_step_id: str | None = None):
    ...
```

- **分布式考虑**
  - Worker 按队列分组：`phase3_queue` 只部署在有 Docker 的节点
  - 任务预取：每个 Worker 每次最多拿 1 个任务
  - 失败重试：指数退避（10s, 30s, 90s）
  - 内存限制：每个 Worker 进程最多 2GB
- **反模式**
  - ❌ Worker 内持有 Run 状态跨任务（每个任务必须完全独立）
  - ❌ 直接 import Domain 模块以外的外部 SDK（如 OpenAI SDK → 必须走 Integration 层）
- **关键测试**
  - `test_crash_recovery_resumes_from_last_step`
  - `test_worker_isolated_from_sdk_directly`

------

#### 6.1.4 `pipeline-builder`（LangGraph 装配）

- **限界上下文**：Application
- **部署位置**：Worker
- **依赖**：LangGraph, 所有 Phase Domain, phase-state-machine, feature-flag
- **被依赖**：worker-runtime
- **核心职责**
  1. 根据 `pipeline_variant` 构建不同的 LangGraph StateGraph
  2. 注册所有 Phase Step 为 Graph Node
  3. 用 `phase-state-machine.next_phase()` 作为 conditional edge 函数
  4. 提供统一的 `run(state) → state` 入口
  5. 支持变体：`full`（P1→P2→P3）、`phase1_only`、`phase1_phase2`、`phase3_direct`
- **关键模型**

```python
class PipelineBuilder:
    def __init__(self, variant: PipelineVariant): ...

    def build(self) -> StateGraph:
        g = StateGraph(CascadeState)
        # 注册所有 Phase Step
        # 注册 conditional_edges（统一走 phase-state-machine）
        return g.compile()

    def run(self, initial_state: CascadeState) -> CascadeState:
        graph = self.build()
        return graph.invoke(initial_state)
```

- **扩展点**
  - 新 Phase：注册新 Node + 新 Edge → PipelineBuilder 自动装配
  - 新变体：在 `pipeline-variant` 中定义节点和边组合
- **关键测试**
  - `test_variant_full_runs_all_phases`
  - `test_variant_phase1_only_stops_after_phase1`

------

#### 6.1.5 `pipeline-variant`（流水线变体管理）

- **限界上下文**：Application
- **部署位置**：shared lib
- **依赖**：feature-flag
- **被依赖**：pipeline-builder, workflow-run
- **核心职责**
  1. 定义所有流水线变体（variant = 哪些 Phase 执行、如何组合）
  2. 提供变体查询接口
  3. 支持实验性变体（feature-flag 开关）
  4. 变体的 Phase 路由规则（`includes_phase2()`, `allow_phase3_on_p2_fail()`）
- **关键模型**

```python
class PipelineVariant(str, Enum):
    FULL = "full"                      # Phase1 → Phase2 → Phase3
    PHASE1_ONLY = "phase1_only"        # 仅 Phase1
    PHASE1_PHASE2 = "phase1_phase2"    # Phase1 → Phase2
    PHASE3_DIRECT = "phase3_direct"    # 直接 Phase3（用于 re-run）

class VariantConfig:
    includes_phase1: bool
    includes_phase2: bool
    includes_phase3: bool
    allow_phase3_on_p2_fail: bool
    max_phase1_iterations: int = 3
    max_fix_iter: int = 5
```

- **扩展点**：新变体只需在 Enum 中加值，不需要改代码
- **关键测试**
  - `test_variant_routing_rules`

------

#### 6.1.6 `idempotency`（幂等控制 — 从 Domain 迁入 Application）

- **限界上下文**：Application（✱ v2 中错误地放在 Domain/Execution，v3 修正）
- **部署位置**：API + Worker
- **依赖**：redis-pubsub, mysql-store
- **被依赖**：api-gateway, worker-runtime
- **核心职责**
  1. API 层幂等：从 `Idempotency-Key` header 提取唯一键，Redis setnx 占位
  2. Worker 层幂等：`run_id + step_name + iteration_index` 组合键
  3. LLM 调用幂等：`SHA256(provider + model + messages + tools)` 组合键
  4. 幂等结果持久化（MySQL outbox）+ 缓存（Redis TTL）
  5. 冲突处理：IN_PROGRESS → 409 或 202；已完成 → 返回缓存结果
- **设计理由（为什么不在 Domain 层）**

```
幂等控制是一个技术关注点，不是核心业务逻辑：
- 它依赖 Redis setnx、MySQL outbox 等基础设施细节
- 它横跨多个 Domain（Run、Template、Review 都需要）
- 它的实现方式随基础设施选型变化（Redis → Memcached → DynamoDB）
- 它属于"请求处理管道"的一部分，由 Application 层编排
```

- **公开接口**

```python
class IdempotencyService:
    async def check_or_register(
        self, key: str, ttl_s: int = 600
    ) -> IdempotencyStatus:
        """NEW / IN_PROGRESS / COMPLETED(result_ref)"""

    async def mark_completed(
        self, key: str, result_ref: str, ttl_s: int = 86400
    ) -> None: ...

    async def get_cached_result(self, key: str) -> str | None: ...
```

- **分布式考虑**
  - Redis setnx 保证原子性
  - TTL 防止孤儿键（IN_PROGRESS 最多活 600s）
  - MySQL outbox 用于 Redis 不可用时的降级
- **关键测试**
  - `test_duplicate_request_returns_cached`
  - `test_in_progress_returns_409`
  - `test_expired_key_allows_retry`

------

### 6.2 Integration Layer（集成层 — 6 个模块）

#### 6.2.1 `llm-provider`（LLM Provider 抽象）

- **限界上下文**：Integration
- **部署位置**：shared lib
- **依赖**：secret-vault
- **被依赖**：llm-agent-loop
- **核心职责**
  1. 定义 `LLMProvider` 抽象接口
  2. 实现 `ClaudeProvider`（Anthropic）、`OpenAIProvider`
  3. 统一调用签名：`chat(messages, tools, output_schema, ...) → LLMResponse`
  4. Provider 选择（按模板或全局配置）
  5. **强制所有 LLM 调用必须走这里**，禁止直接 import anthropic/openai SDK
- **关键模型**

```python
class LLMResponse(TypedDict):
    content: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    model: str
    llm_latency_ms: int

class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[Tool] | None,
        output_schema: dict | None,
        temperature: float,
        max_tokens: int,
        metadata: dict,
    ) -> LLMResponse: ...

    @abstractmethod
    def provider_name(self) -> str: ...
```

- **扩展点**：加新 Provider → 实现 `LLMProvider` 即可，不需要改业务代码
- **分布式考虑**：无状态；连接池管理（每 Provider 10 连接）
- **反模式**
  - ❌ 任何业务代码直接 import anthropic SDK（必须通过本模块）
- **关键测试**
  - `test_provider_interface_all_implementations`
  - `test_no_direct_sdk_imports_in_domain`

------

#### 6.2.2 `llm-tool-use`（Tool Use 协议）

- **限界上下文**：Integration
- **部署位置**：shared lib
- **依赖**：llm-provider
- **被依赖**：llm-agent-loop
- **核心职责**
  1. 定义项目内 Tool Use 的标准协议（基于 Anthropic / OpenAI 格式）
  2. `ToolUseResult` 结构：**严格分离** `output_json`（结构数据）和 `content`（人类可读摘要）
  3. 提供 `ToolUseResult` 序列化 / 反序列化
  4. **修复 v1 反模式**：禁止在 content 字段嵌入结构化 JSON
- **关键模型**

```python
@dataclass(frozen=True)
class ToolUseResult:
    output_json: dict              # 纯结构数据（符合 output_schema）
    outgoing_edges: list[OutgoingEdge]  # 纯结构数据
    content: str                   # 人类可读摘要（用于调试/日志）
    warnings: tuple[str, ...] = ()
    tokens_in: int = 0
    tokens_out: int = 0

class OutgoingEdge(TypedDict):
    edge_id: str
    semantic: str                  # edge_semantics.field
    target_instance_id: str
    output_field: str             # 本节点 output 中用于该边的字段
```

- **反模式**（✱ 修复 v1）
  - ❌ `content = f"Node output: {json.dumps(output)}"`（结构数据混入文本）
  - ✅ `result.content = "Node X returned 3 items"`（摘要）+ `result.output_json = {...}`（数据）
- **关键测试**
  - `test_output_json_never_in_content`
  - `test_tool_result_deserialization_stable`

------

#### 6.2.3 `llm-output-schema`（Forced Schema 输出）

- **限界上下文**：Integration
- **部署位置**：shared lib
- **依赖**：schema-engine, llm-provider
- **被依赖**：llm-agent-loop, failure-attribution, dynamic-reflector, static-reflector
- **核心职责**
  1. **强制 LLM 输出结构化 JSON**：通过 `output_schema` 参数传给 LLM Provider
  2. 提供 schema 模板库（verdict / attribution / code_fix / static_issue 等）
  3. 验证 LLM 实际返回是否符合 schema（schema-engine）
  4. 验证失败时：自动重试（最多 2 次）→ 仍失败抛 `LLMSchemaViolation`
  5. **修复 v1 反模式**：禁止从 LLM 自由文本推断状态
- **关键模型**

```python
SCHEMA_TEMPLATES: dict[str, dict] = {
    "verdict": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["done", "design_bug", "fix_code"],
            },
            "reason": {"type": "string"},
        },
        "required": ["decision", "reason"],
    },
    "attribution": {
        "type": "object",
        "properties": {
            "attribution": {
                "type": "string",
                "enum": ["design_bug", "scenario_bug", "simulator_bug", "unknown"],
            },
            "reason": {"type": "string"},
        },
        "required": ["attribution", "reason"],
    },
    # ... 其他模板
}

class LLMOutputSchemaService:
    async def forced_chat(
        self,
        provider: LLMProvider,
        messages: list[ChatMessage],
        template_name: str,
        **kwargs,
    ) -> dict:
        """调用 LLM，强制 output_schema，重试验证"""
```

- **反模式**（✱ 关键）
  - ❌ `if "design_bug" in llm_text: verdict = "design_bug"`
  - ✅ `output = await forced_chat(provider, messages, "verdict"); verdict = output["decision"]`
- **关键测试**
  - `test_forced_schema_rejects_invalid_output`
  - `test_retries_on_schema_violation`

------

#### 6.2.4 `llm-prompt-cache`（Prompt 模板缓存）

- **限界上下文**：Integration
- **部署位置**：shared lib
- **依赖**：redis-pubsub
- **被依赖**：llm-agent-loop
- **核心职责**
  1. 缓存**编译后的 prompt 模板**（系统提示 + 场景模板 + 变量槽位），避免重复渲染和 token 计数
  2. Cache Key = `SHA256(template_name + template_version)`
  3. 每个缓存条目包含：渲染后的文本、token 数估算、变量列表
  4. 缓存失效：模板文件修改 → 广播失效
  5. 命中率统计（Prometheus metrics）
- **⚠️ 与 LLM 调用幂等缓存的区别**

```
本模块缓存的是 prompt 模板的编译结果，不是 LLM 的返回值。

  llm-prompt-cache：缓存 prompt 模板渲染结果（避免重复渲染 + 重复 token 计数）
  idempotency + §8.2.3：缓存 LLM 调用返回结果（避免重复消耗 token + 钱）

两者互不替代。
```

- **缓存策略**
  - LRU 逐出（max 10000 entries）
  - TTL：7 天
  - 写穿透：miss 时计算并存入 Redis
- **分布式考虑**
  - 跨 Worker 共享 Redis 缓存
  - 失效广播：Redis Pub/Sub channel `prompt:invalidated`
- **关键测试**
  - `test_cache_hit_saves_tokens`
  - `test_template_change_invalidates`

------

#### 6.2.5 `llm-agent-loop`（Agent 循环）

- **限界上下文**：Integration
- **部署位置**：shared lib
- **依赖**：llm-provider, llm-tool-use, llm-output-schema, llm-prompt-cache, node-simulator
- **被依赖**：scenario-engine, code-generator, static-reflector, failure-attribution, dynamic-reflector
- **核心职责**
  1. 实现 Agent 循环：发消息 → 接收 Tool Use → 执行 Tool → 收集结果 → 继续
  2. 循环终止条件：LLM 返回 stop / max_turns / token_limit / cancel_token
  3. 支持多轮 Tool Use（跨 NodeInstance）
  4. 记录每次 LLM 调用到 `messages` 列表
  5. **统一处理重试、断路器、超时**
- **关键模型**

```python
class AgentLoopResult(TypedDict):
    final_content: str
    stop_reason: str
    total_turns: int
    tool_calls: list[ToolUseResult]
    total_tokens_in: int
    total_tokens_out: int
    messages: list[ChatMessage]

class LLMAgent:
    async def run(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[Tool],
        max_turns: int = 20,
        cancel_token: CancelToken | None = None,
    ) -> AgentLoopResult: ...
```

- **断路器**：LLM 连续失败 3 次 → 断路器打开，60s 后半开
- **分布式考虑**：每个 AgentLoop 调用独立幂等键（防止重试时重复执行）
- **关键测试**
  - `test_circuit_breaker_opens_on_repeated_failure`
  - `test_cancel_token_stops_loop`

------

#### 6.2.6 `sandbox-runtime`（沙箱运行时抽象）

- **限界上下文**：Integration
- **部署位置**：shared lib
- **依赖**：docker-driver
- **被依赖**：sandbox-provisioner, sandbox-compiler, sandbox-executor
- **核心职责**
  1. 定义 `SandboxRuntime` 抽象接口（不绑定 Docker）
  2. 实现 `DockerSandboxRuntime`
  3. 提供统一的容器操作：启动命令、复制文件、读取结果
  4. 资源限制：CPU、内存、磁盘、超时
  5. **未来扩展**：加 `FirecrackerRuntime`、`KataRuntime` 只需实现接口
- **关键模型**

```python
class SandboxRuntime(ABC):
    @abstractmethod
    async def run_command(
        self,
        cmd: list[str],
        stdin: bytes | None,
        timeout_s: int,
        cpu_limit: float,
        mem_limit_mb: int,
    ) -> CommandResult: ...

    @abstractmethod
    async def copy_file(self, container_id: str, src: str, dst: str) -> None: ...

    @abstractmethod
    async def read_file(self, container_id: str, path: str) -> bytes: ...
```

- **扩展点**（✱ 关键）
  - 新沙箱技术：实现 `SandboxRuntime` 子类即可，不动业务代码
- **分布式考虑**：同 sandbox-provisioner
- **关键测试**
  - `test_runtime_interface_contract`
  - `test_resource_limits_enforced`

------

### 6.3 Cross-Cutting Concerns（横切关注点 — 6 个模块）

#### 6.3.1 `trace-bus`（Trace/事件总线）

- **限界上下文**：Cross-Cutting
- **部署位置**：shared lib（所有节点）
- **依赖**：mongo-trace, redis-pubsub
- **被依赖**：所有 Domain 模块
- **核心职责**
  1. 定义统一事件模型 `DomainEvent`
  2. 发布 / 订阅总线
  3. 每个 Run 分配全局 `trace_id`（UUID），贯穿所有阶段
  4. 事件持久化到 MongoDB（含 trace_id）
  5. 实时事件通过 Redis Pub/Sub 扇出到 WebSocket
- **关键模型**

```python
@dataclass(frozen=True)
class DomainEvent:
    event_id: str                    # ev_xxxxxxxx
    trace_id: str                    # 全局链路 ID
    span_id: str                     # 当前节点 ID
    event_type: str                  # "run.created" | "phase.finished" | ...
    aggregate_id: str                # "r_xxx" | "tpl_xxx" | ...
    payload: Mapping[str, Any]
    occurred_at: datetime
    schema_version: int = 1

class TraceEmitter:
    def emit(self, event_type: str, payload: dict) -> None:
        """异步发布事件（不阻塞主流程）"""

    def emit_and_wait(self, event_type: str, payload: dict) -> None:
        """同步发布（仅用于必须等待副作用的场景）"""
```

- **分布式考虑**
  - 事件发布幂等（`event_id` 唯一）
  - 订阅端按 `event_type` 过滤
  - MongoDB 写入异步批量（buffer 100 / 50ms）
- **关键测试**
  - `test_trace_id_propagates_all_phases`
  - `test_event_ordering`

------

#### 6.3.2 `metrics`（指标采集）

- **限界上下文**：Cross-Cutting
- **部署位置**：shared lib
- **依赖**：Prometheus client library
- **被依赖**：所有 Domain 模块
- **核心职责**
  1. 定义指标类型：Counter、Gauge、Histogram、Summary
  2. 关键指标：
     - `run_started_total`、`run_finished_total`（Counter，按 final_verdict 标签）
     - `phase_duration_seconds`（Histogram，按 phase 标签）
     - `llm_tokens_total`（Counter，按 provider/model 标签）
     - `sandbox_compile_duration_seconds`（Histogram）
     - `active_runs`（Gauge）
  3. Prometheus scrape 端点（`/metrics`）
  4. 自定义标签（`run_id`、`phase`、`variant`）
- **分布式考虑**：每节点独立采集 → Prometheus 聚合
- **关键测试**
  - `test_labels_propagate`

------

#### 6.3.3 `audit-log`（审计日志）

- **限界上下文**：Cross-Cutting
- **部署位置**：shared lib
- **依赖**：mysql-store
- **被依赖**：api-gateway, workflow-run
- **核心职责**
  1. 记录所有写操作（who、when、what、how）
  2. 覆盖：Run 创建/取消、图保存/删除、模板发布/废弃、评审操作、权限变更
  3. 防篡改：仅追加，不可修改或删除
  4. 保留期：1 年
- **关键模型**

```python
class AuditLog:
    id: str
    user_id: int
    action: str                     # "run.create" | "template.publish" | ...
    target_type: str
    target_id: str
    ip_address: str
    user_agent: str
    payload: dict                   # 操作详情
    occurred_at: datetime
```

- **分布式考虑**：异步批量写（不阻塞主流程）
- **关键测试**
  - `test_immutable_after_write`

------

#### 6.3.4 `auth-rbac`（权限与角色）

- **限界上下文**：Cross-Cutting
- **部署位置**：shared lib
- **依赖**：mysql-store
- **被依赖**：api-gateway, node-library
- **核心职责**
  1. 定义角色：`admin`、`editor`、`viewer`
  2. 定义权限矩阵（见 `node-library` §3.1.4）
  3. 资源级别权限：`private` 模板只能 owner 访问
  4. API 中间件：在请求处理前鉴权
- **权限矩阵**

| 操作       | viewer | editor | admin |
| ---------- | ------ | ------ | ----- |
| 查看公开图 | ✅      | ✅      | ✅     |
| 创建图     | ❌      | ✅      | ✅     |
| 触发 Run   | ❌      | ✅      | ✅     |
| 发布模板   | ❌      | ❌      | ✅     |
| 废弃模板   | ❌      | ❌      | ✅     |
| 管理用户   | ❌      | ❌      | ✅     |

- **分布式考虑**：RBAC 缓存在 Redis（TTL 60s），变更时主动失效
- **关键测试**
  - `test_private_resource_owner_only`
  - `test_admin_bypass`

------

#### 6.3.5 `feature-flag`（特性开关）

- **限界上下文**：Cross-Cutting
- **部署位置**：shared lib
- **依赖**：redis-pubsub
- **被依赖**：pipeline-variant, node-registry
- **核心职责**
  1. 运行时开关（不重部署）
  2. 按用户/租户/全局维度的开关
  3. 支持实验性 Phase/Handler 灰度
  4. 开关变更事件（订阅后实时生效）
- **关键模型**

```python
@dataclass
class FeatureFlag:
    key: str
    enabled: bool
    rollout_percentage: float | None  # None = 100%
    user_ids: list[int] | None       # 白名单
    variants: list[str] | None       # 多变体支持
```

- **示例使用**：`if await ff.is_enabled("phase3_direct", user_id): ...`
- **分布式考虑**：Redis 缓存 + Pub/Sub 即时失效
- **关键测试**
  - `test_rollout_percentage`
  - `test_change_propagates_without_restart`

------

#### 6.3.6 `secret-vault`（密钥管理）

- **限界上下文**：Cross-Cutting
- **部署位置**：shared lib
- **依赖**：env / AWS KMS / HashiCorp Vault
- **被依赖**：llm-provider, docker-driver
- **核心职责**
  1. 所有密钥（LLM API Key、Docker Registry 凭证、DB 密码）不落源代码
  2. 运行时从环境变量 / KMS 获取
  3. 提供统一接口：`get_secret(key_name) → str`
  4. 密钥轮转支持（通过 versioned secret）
- **反模式**
  - ❌ 密钥写入配置文件或代码（CI/CD 环境变量注入）
  - ❌ 密钥打印到日志
- **关键测试**
  - `test_secret_not_in_logs`
  - `test_missing_secret_raises`

------

### 6.4 Infrastructure Layer（基础设施 — 5 个模块）

#### 6.4.1 `mysql-store`（MySQL 存储）

- **限界上下文**：Infrastructure
- **依赖**：SQLAlchemy 2.x + aiomysql
- **被依赖**：所有有持久化需求的 Domain 模块
- **核心职责**
  1. 统一 DB Session 管理（同步 / 异步）
  2. 连接池配置（每节点 20-50 连接）
  3. 事务边界定义
  4. 乐观锁字段（`version` 列）混入 Mixin
  5. 软删除 Mixin（`deleted_at`）
  6. 迁移管理（见 schema-migration）
- **分布式考虑**
  - 只读请求走从库
  - 写请求走主库
  - 连接池满时排队（max_overflow=10，超时 30s）
- **关键测试**
  - `test_optimistic_lock_retry_on_conflict`
  - `test_soft_delete_preserves_data`

------

#### 6.4.2 `mongo-trace`（MongoDB Trace）

- **限界上下文**：Infrastructure
- **依赖**：motor（异步 driver）
- **被依赖**：run-step, trace-bus
- **核心职责**
  1. Trace 集合管理（`run_step_details`、`sandbox_traces`）
  2. 批量写入优化（buffer + flush）
  3. TTL Index（90 天自动过期）
  4. 分片策略：`run_id` 作为片键
  5. 读写分离（从 Secondary 读历史，从 Primary 写新数据）
- **分布式考虑**
  - 副本集 3 节点（1 主 2 从）
  - 写失败：落 outbox 表 + 后台补偿任务
- **关键测试**
  - `test_ttl_index_enforced`
  - `test_outbox_recovery`

------

#### 6.4.3 `redis-pubsub`（Redis 消息）

- **限界上下文**：Infrastructure
- **依赖**：redis-py（cluster mode）
- **被依赖**：websocket-pusher, trace-bus, idempotency, cancellation, node-registry
- **核心职责**
  1. Pub/Sub 频道管理
  2. 分布式锁（Redlock 算法）
  3. 队列（Stream-based）作为 Celery broker 替代
  4. 缓存（见各模块的缓存策略）
  5. 限流（滑动窗口）
- **分布式考虑**
  - Cluster 模式（3 主 3 从）
  - Pipeline 批量操作减少 RTT
  - 锁 TTL 必须大于操作超时
- **关键测试**
  - `test_redlock_acquires_and_releases`
  - `test_stream_consumer_recovery`

------

#### 6.4.4 `docker-driver`（Docker 驱动）

- **限界上下文**：Infrastructure
- **依赖**：docker SDK for Python
- **被依赖**：sandbox-runtime
- **核心职责**
  1. 封装 Docker API（不直接暴露给业务层）
  2. 镜像预热（Phase3 Worker 启动时拉取）
  3. 容器网络隔离（bridge network + `network_mode: none`）
  4. 资源限制（ulimit、cgroup）
  5. 镜像清理策略（按标签保留 N 个，untagged 定期清理）
- **分布式考虑**
  - 每 sandbox Worker 节点独立 Docker Daemon
  - 镜像通过 registry 分布式拉取（不要从单机推送）
- **关键测试**
  - `test_network_isolation_enforced`
  - `test_container_cleanup_after_timeout`

------

#### 6.4.5 `schema-migration`（Schema 演进）

- **限界上下文**：Infrastructure

- **依赖**：Alembic

- **被依赖**：无（独立 CLI + Cron）

- **核心职责**

  1. 所有 MySQL schema 变更通过 Alembic 迁移脚本
  2. 迁移脚本命名规范：`{timestamp}_{description}.py`
  3. 支持零停机迁移（膨胀列 + 立即回填 + 最终约束）
  4. 迁移前检查、回滚计划
  5. 迁移锁（防止并发迁移）

- **迁移流程**

  ```
  1. 提出 Migration Proposal（含：升级路径、降级路径、影响分析）
  2. 在 staging 环境验证
  3. 生产低峰期执行（Celery Cron）
  4. 监控错误率 + 慢查询
  5. 如有问题，执行回滚脚本
  ```

- **关键测试**

  - `test_migration_idempotent`
  - `test_rollback_restores_schema`

------

## 第 7 章 12 个状态机完整规约

> **每个状态机的规范格式：**
>
> - 状态定义 + 含义说明
> - 完整状态转移图（Mermaid）
> - 转移条件（每条边的触发条件）
> - 不变式（转移后必须满足的约束）
> - 非法转移处理策略
> - 并发保护机制
> - 崩溃恢复策略
> - 超时策略
> - 发布事件

------

### §7.1 WorkflowRun 主状态机

**聚合根**：`WorkflowRun` **状态字段**：`status: WorkflowRunStatus`

#### 状态定义

| 状态        | 含义                                                         |
| ----------- | ------------------------------------------------------------ |
| `PENDING`   | Run 已创建，等待 Worker 认领                                 |
| `RUNNING`   | Worker 正在执行中                                            |
| `SUCCESS`   | 所有阶段完成且最终判定 valid                                 |
| `FAILED`    | 任意阶段失败（phase1 invalid / phase2 failed 非 design_bug / 系统错误） |
| `CANCELLED` | 用户主动取消                                                 |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> PENDING: create_run
    PENDING --> RUNNING: worker_picks_up
    PENDING --> CANCELLED: cancel (PENDING only)

    RUNNING --> SUCCESS: phase3_done & verdict=valid
    RUNNING --> FAILED: phase1_invalid | phase3_design_bug | unhandled_error
    RUNNING --> CANCELLED: cancel (RUNNING)

    SUCCESS --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

#### 转移规则

| 当前    | 触发                                | 目标      | 条件                                                        |
| ------- | ----------------------------------- | --------- | ----------------------------------------------------------- |
| PENDING | worker_picks_up                     | RUNNING   | Run 被 dequeue                                              |
| PENDING | cancel                              | CANCELLED | 用户请求 + 尚未被认领                                       |
| RUNNING | phase_state_machine.final = valid   | SUCCESS   | phase3_verdict == DONE && final_verdict == valid            |
| RUNNING | phase_state_machine.final = invalid | FAILED    | phase1_verdict == INVALID \|\| phase3_verdict == DESIGN_BUG |
| RUNNING | cancel                              | CANCELLED | 用户请求 + RUNNING 状态                                     |
| RUNNING | unhandled_exception                 | FAILED    | Worker 捕获未处理异常                                       |

#### 不变式

```
1. PENDING 状态只能由 create_run 写入
2. SUCCESS / FAILED / CANCELLED 为终态，不可再转移
3. status 变更必须通过 phase-state-machine.transition()
4. 每个转移必须写入 updated_at
5. version 字段乐观锁每次 +1
```

#### 并发保护

```python
# 乐观锁
UPDATE t_workflow_run
SET status = :new, version = version + 1, updated_at = :now
WHERE id = :id AND version = :expected_version
-- 命中 0 行 → OptimisticLockError → 重试 3 次
```

#### 崩溃恢复

```
Worker 崩溃 → Run 留在 RUNNING
定时扫描（每 5min）：SELECT * FROM t_workflow_run WHERE status = 'RUNNING' AND updated_at < now() - 30min
→ 重新入队（phase1_queue）
→ 注意：Phase3 外层修复迭代的中间状态从 MongoDB RunStep 恢复
```

#### 超时策略

```
RUNNING 状态超过 2 小时无进展 → 自动标记为 FAILED (TIMEOUT)
（outer_fix_iter 已达上限 + 阶段卡住的情况）
```

#### 发布事件

`RunCreated`, `RunStarted`, `RunFinished`, `RunCancelled`, `RunFailed`, `RunStatusTransitioned`

------

### §7.2 Phase 调度状态机

**关联**：WorkflowRun 上的阶段编排

#### 状态定义

每个 Phase 有独立状态：`phase1_status / phase2_status / phase3_status`

| 状态          | 含义                         |
| ------------- | ---------------------------- |
| `NOT_STARTED` | 未开始                       |
| `RUNNING`     | 执行中                       |
| `PASSED`      | 成功完成                     |
| `FAILED`      | 失败                         |
| `SKIPPED`     | 跳过（variant 不包含该阶段） |

#### 状态图（单 Phase）

```mermaid
stateDiagram-v2
    [*] --> NOT_STARTED
    NOT_STARTED --> RUNNING: start_phase
    RUNNING --> PASSED: all_handlers_passed
    RUNNING --> FAILED: handler_failed & cannot_recover
    RUNNING --> PASSED: handler_failed & can_recover & max_iter_reached
    NOT_STARTED --> SKIPPED: variant_excludes
    RUNNING --> SKIPPED: cancel
```

#### 调度顺序（由 phase-state-machine.next_phase 决定）

```
Phase1 未开始 → 开始 Phase1
Phase1 PASSED → variant.includes_phase2() ? 开始 Phase2 : 结束
Phase1 FAILED → 结束（最终 invalid）
Phase2 PASSED → variant.includes_phase3() ? 开始 Phase3 : 结束
Phase2 FAILED → variant.allow_phase3_on_p2_fail() ? 开始 Phase3 : 结束
Phase3 PASSED / FAILED / SKIPPED → 结束
```

#### 不变式

```
1. phase2 只有在 phase1 PASSED 时才能开始
2. phase3 只有在 phase2 PASSED（或 allow）时才能开始
3. 前置 phase 为 FAILED 时，后续 phase 必须 SKIPPED 或 NOT_STARTED
```

#### 并发保护

```
phase 状态变更是 WorkflowRun 更新的一部分，受同一乐观锁保护
同一 Run 的两个 Worker 不能同时处理同一个 phase
```

#### 崩溃恢复

```
Phase 执行中断 → 从最后一个成功 RunStep 恢复（MongoDB）
Phase1 Handler 链：恢复时重新从 last_successful_handler.next 开始
Phase3 修复循环：恢复时 outer_fix_iter 保持，重新进入 static_check
```

#### 超时策略

```
Phase1 整体：30 分钟超时（超时 → FAILED）
Phase2 整体：60 分钟超时
Phase3 单次 iteration：10 分钟超时；总修复循环 2 小时超时
```

#### 发布事件

`Phase1Started`, `Phase1Finished`, `Phase2Started`, `Phase2Finished`, `Phase3Started`, `Phase3Finished`

------

### §7.3 Phase1 Handler 链状态机

**关联**：Phase1 内部 Handler 编排

#### 状态定义

每个 Handler 实例有独立状态：

| 状态      | 含义     |
| --------- | -------- |
| `PENDING` | 等待执行 |
| `RUNNING` | 执行中   |
| `PASS`    | 通过     |
| `FAIL`    | 失败     |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> H1_PENDING
    H1_PENDING --> H1_RUNNING: start
    H1_RUNNING --> H1_PASS: validator.ok
    H1_RUNNING --> H1_FAIL: not validator.ok
    H1_PASS --> H2_PENDING: next_handler
    H1_FAIL --> [*]: END (invalid)
    H2_PENDING --> H2_RUNNING: start
    H2_RUNNING --> H2_PASS: all_scenarios_pass
    H2_RUNNING --> H2_FAIL: any_scenario_fail
    H2_PASS --> [*]: END (valid, proceed to Phase2)
    H2_FAIL --> [*]: END (invalid)
```

#### 内层反思循环（SDD / TDD）

Handler 2（scenario_run）失败后，不立即退出，可能触发：

```
H2_FAIL
  → decision = "fix_spec" (SDD 反思)
  → 修改节点 field_values
  → 重新跑 H2
  → 或 decision = "add_scenario" (TDD 反思)
  → 添加新 scenario
  → 重新跑 H2
  → max 3 次迭代
  → 仍 FAIL → H2_FAIL 最终退出
```

#### 不变式

```
1. Handler 按 handler_order 严格串行执行
2. 任一 FAIL 立即短路（除非是 SDD/TDD 反思循环内）
3. 反思循环次数有上限（max 3 次）
```

#### 并发保护

```
Handler 在单一 Worker 内串行执行，无需并发保护
不同 Run 的 Handler 完全独立
```

#### 崩溃恢复

```
Handler 执行中断 → RunStep 状态为 RUNNING → 从该 Handler 重新执行
```

#### 发布事件

`HandlerStarted`, `HandlerFinished`, `HandlerDecisionMade`

------

### §7.4 Phase2 代码生成状态机

**关联**：Phase2 内部步骤编排

#### 状态定义

| 状态             | 含义             |
| ---------------- | ---------------- |
| `PLANNING`       | 代码骨架规划中   |
| `GENERATING`     | 逐 Bundle 生成中 |
| `ASSEMBLING`     | 组装完整程序     |
| `SNAPSHOT_SAVED` | 快照已保存       |
| `FAILED`         | 生成失败         |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> PLANNING
    PLANNING --> GENERATING: skeleton_ready
    GENERATING --> ASSEMBLING: all_units_ready
    ASSEMBLING --> SNAPSHOT_SAVED: composite_code_valid
    GENERATING --> FAILED: bundle_gen_error
    ASSEMBLING --> FAILED: assemble_error
    SNAPSHOT_SAVED --> GENERATING: fix_iter (Phase3 feedback)
```

#### 不变式

```
1. GENERATING 前必须有 PLANNING 完成
2. ASSEMBLING 前必须有所有 CodeUnit 生成完毕
3. SNAPSHOT_SAVED 后才能进入 Phase3 编译
```

#### 并发保护

```
CodeUnit 生成跨 Bundle 并行，同 Bundle 内串行
快照保存使用 CodeSnapshotRepository（乐观锁）
```

#### 崩溃恢复

```
中断 → 按最后成功步骤重新执行
snapshot 保存失败 → 重试 3 次
```

#### 发布事件

`CodePlanFinished`, `CodeUnitGenerated`, `CodeAssembled`, `CodeSnapshotSaved`

------

### §7.5 Phase3 外层修复循环状态机

**关联**：Phase3 整体迭代控制

#### 状态定义

```
outer_fix_iter: int ∈ [0, MAX_FIX_ITER]  (MAX = 5)

子状态：
  STATIC_CHECK → COMPILE → SYNTHESIZE → EXECUTE → DYNAMIC_CHECK
```

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> FIX_ITER_0

    FIX_ITER_0 --> STATIC_CHECK
    STATIC_CHECK --> HAS_ISSUES: has_issues
    STATIC_CHECK --> COMPILE: no_issues

    HAS_ISSUES --> CODE_GEN: fix_static
    CODE_GEN --> COMPILE

    COMPILE --> COMPILE_OK: exit_code == 0
    COMPILE --> COMPILE_FAIL: exit_code != 0
    COMPILE_FAIL --> CODE_GEN: retry_static_fix
    COMPILE_FAIL --> FIX_EXHAUSTED: max_iter

    COMPILE_OK --> SYNTHESIZE
    SYNTHESIZE --> EXECUTE
    EXECUTE --> DYNAMIC_CHECK

    DYNAMIC_CHECK --> DONE: decision = done
    DYNAMIC_CHECK --> DESIGN_BUG: decision = design_bug
    DYNAMIC_CHECK --> FIX_CODE: decision = fix_code

    FIX_CODE --> FIX_ITER_1: iter + 1
    FIX_ITER_1 --> STATIC_CHECK
    FIX_ITER_1 --> FIX_EXHAUSTED: iter >= MAX

    FIX_EXHAUSTED --> [*]
    DONE --> [*]
    DESIGN_BUG --> [*]
```

#### 转移条件

| 从            | 触发                            | 到            | 条件                    |
| ------------- | ------------------------------- | ------------- | ----------------------- |
| any           | iter >= MAX                     | FIX_EXHAUSTED | -                       |
| any           | decision = done                 | DONE          | -                       |
| any           | decision = design_bug           | DESIGN_BUG    | -                       |
| STATIC_CHECK  | has_issues                      | HAS_ISSUES    | static_issues not empty |
| STATIC_CHECK  | no_issues                       | COMPILE       | static_issues empty     |
| HAS_ISSUES    | fix applied                     | COMPILE       | -                       |
| COMPILE       | success                         | SYNTHESIZE    | compile_result.ok       |
| COMPILE       | failure & retries > 0           | CODE_GEN      | -                       |
| COMPILE       | failure & retries exhausted     | FIX_EXHAUSTED | -                       |
| DYNAMIC_CHECK | verdict = done                  | DONE          | -                       |
| DYNAMIC_CHECK | verdict = design_bug            | DESIGN_BUG    | -                       |
| DYNAMIC_CHECK | verdict = fix_code & iter < MAX | FIX_CODE      | -                       |

#### 不变式

```
1. outer_fix_iter 单调递增，永不递减
2. FIX_EXHAUSTED 为终态（最终 verdict = inconclusive）
3. DONE / DESIGN_BUG / FIX_EXHAUSTED 为终态
4. 每次 iteration 必须产生一个 CodeSnapshot
```

#### 并发保护

```
单一 Worker 串行执行一个 Run 的所有 iteration
（加锁 run_id，Redis 分布式锁）
```

#### 崩溃恢复

```
每次 iteration 结束持久化 state（含 outer_fix_iter）
重启后恢复 → 重新进入对应子状态
```

#### 超时策略

```
单次 iteration：10 分钟超时
总循环：2 小时超时（超时 → FIX_EXHAUSTED）
```

#### 发布事件

`FixLoopStarted`, `FixIterationStarted`, `FixIterationFinished`, `FixLoopEnded`

------

### §7.6 编译子状态机

**关联**：Phase3 内沙箱编译

#### 状态定义

| 状态        | 含义                |
| ----------- | ------------------- |
| `PREPARING` | 容器启动、文件复制  |
| `COMPILING` | cmake + make 执行中 |
| `OK`        | 编译成功，产物就绪  |
| `ERROR`     | 编译失败            |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> PREPARING
    PREPARING --> COMPILING: ready
    COMPILING --> OK: exit_code == 0
    COMPILING --> ERROR: exit_code != 0
    OK --> [*]
    ERROR --> [*]
```

#### 不变式

```
1. OK 状态后才允许进入 SYNTHESIZE
2. 编译产物（artifacts）哈希必须稳定（相同代码 → 相同哈希）
```

#### 超时策略

```
PREPARING: 60s
COMPILING: 300s (5min)
超时 → ERROR
```

------

### §7.7 NodeTemplate 状态机

**聚合根**：`NodeTemplate` **状态字段**：`status: TemplateStatus`

#### 状态定义

| 状态         | 含义                 |
| ------------ | -------------------- |
| `DRAFT`      | 草稿，可编辑         |
| `ACTIVE`     | 已激活，使用中       |
| `DEPRECATED` | 已废弃，不可新增使用 |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> DRAFT: create
    DRAFT --> ACTIVE: publish
    DRAFT --> DRAFT: save
    ACTIVE --> ACTIVE: new_version (自动完成)
    ACTIVE --> DEPRECATED: deprecate
    DEPRECATED --> [*]: archive (不可逆)
```

#### 转移规则

| 当前       | 触发                | 目标       |
| ---------- | ------------------- | ---------- |
| DRAFT      | publish             | ACTIVE     |
| ACTIVE     | new_version saved   | ACTIVE     |
| ACTIVE     | deprecate           | DEPRECATED |
| DEPRECATED | archive（系统自动） | -          |

#### 不变式

```
1. DEPRECATED 不可逆，不可再转回 ACTIVE
2. ACTIVE 模板删除前必须先 DEPRECATED
3. DEPRECATED 后新版本不能再基于它创建
```

#### 并发保护

```
UPDATE 时乐观锁 version 字段
```

------

### §7.8 GraphVersion 状态机

**实体**：`GraphVersion` **状态字段**：`state: VersionState`

#### 状态定义

| 状态        | 含义             |
| ----------- | ---------------- |
| `DRAFT`     | 草稿，未保存     |
| `SAVED`     | 已保存（不可变） |
| `VALIDATED` | Phase1 通过      |
| `ARCHIVED`  | 已归档           |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> DRAFT: create_version
    DRAFT --> SAVED: save
    DRAFT --> DRAFT: auto_save
    SAVED --> VALIDATED: phase1_passed
    SAVED --> ARCHIVED: user_archive
    VALIDATED --> ARCHIVED: user_archive
    ARCHIVED --> [*]: (终态)
```

#### 不变式

```
1. SAVED 后 snapshot 不可修改
2. VALIDATED 后才能触发 Run
3. ARCHIVED 后不可再用于 Run
```

------

### §7.9 Review 状态机

**聚合根**：`GraphReview` **状态字段**：`verdict: ReviewStatus`

#### 状态定义

| 状态             | 含义           |
| ---------------- | -------------- |
| `NONE`           | Run 创建时默认 |
| `PENDING`        | 评审进行中     |
| `APPROVED`       | 评审通过       |
| `REJECTED`       | 评审拒绝       |
| `NEEDS_REVISION` | 需要修改后重审 |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> NONE: run_created
    NONE --> PENDING: initiate_review
    PENDING --> APPROVED: approve
    PENDING --> REJECTED: reject
    PENDING --> NEEDS_REVISION: request_revision
    NEEDS_REVISION --> PENDING: resubmit
    REJECTED --> [*]: (终态)
    APPROVED --> [*]: (终态)
```

#### 不变式

```
1. APPROVED / REJECTED 为终态
2. NEEDS_REVISION → PENDING 后可再次流转
```

------

### §7.10 Sandbox Container 状态机

**实体**：`ContainerHandle` **状态字段**：`status: ContainerStatus`

#### 状态定义

| 状态           | 含义             |
| -------------- | ---------------- |
| `PROVISIONING` | 容器正在启动     |
| `READY`        | 就绪，可执行命令 |
| `RUNNING`      | 命令执行中       |
| `CLEANING`     | 执行完毕，清理中 |
| `DESTROYED`    | 已销毁（终态）   |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> PROVISIONING
    PROVISIONING --> READY: container_started
    READY --> RUNNING: exec_start
    RUNNING --> READY: exec_done
    READY --> CLEANING: release
    CLEANING --> DESTROYED: cleanup_done
    RUNNING --> CLEANING: timeout / force_kill
```

#### 不变式

```
1. DESTROYED 后不可再使用
2. RUNNING 超时强制进入 CLEANING
3. CLEANING 失败 → 标记为 orphan（由 Cron 兜底清理）
```

#### 超时策略

```
RUNNING 状态：默认 300s（可配置）
超时 → 强制杀进程 → CLEANING
```

#### 崩溃恢复

```
容器进程崩溃 → Cron 扫描 PROVISIONING / RUNNING 超时容器
→ 标记 DESTROYED → 归还容器池
```

------

### §7.11 LLM Call 状态机

**实体**：`LLMCall` **状态字段**：`status: LLMCallStatus`

#### 状态定义

| 状态        | 含义             |
| ----------- | ---------------- |
| `PENDING`   | 等待调度         |
| `SENDING`   | 请求发送中       |
| `STREAMING` | 流式接收中       |
| `DONE`      | 完成             |
| `RETRYING`  | 重试中           |
| `FAILED`    | 失败（重试耗尽） |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> SENDING: start
    SENDING --> STREAMING: first_token
    SENDING --> DONE: non_stream_done
    STREAMING --> DONE: last_token
    SENDING --> RETRYING: transient_error & retries < max
    STREAMING --> RETRYING: transient_error & retries < max
    RETRYING --> SENDING: retry
    SENDING --> FAILED: fatal_error | retries_exhausted
    STREAMING --> FAILED: fatal_error | retries_exhausted
```

#### 转移规则

| 当前              | 触发                 | 目标      | 条件            |
| ----------------- | -------------------- | --------- | --------------- |
| PENDING           | start                | SENDING   | -               |
| SENDING           | first_token          | STREAMING | streaming mode  |
| SENDING           | response_received    | DONE      | non-streaming   |
| STREAMING         | last_token           | DONE      | -               |
| SENDING/STREAMING | error & retries < 3  | RETRYING  | transient error |
| SENDING/STREAMING | error & retries >= 3 | FAILED    | -               |
| RETRYING          | retry                | SENDING   | -               |

#### 不变式

```
1. RETRYING 最多 3 次（指数退避：10s, 30s, 90s）
2. 幂等键保证重复请求不重复消费 token
3. DONE / FAILED 为终态
```

#### 并发保护

```
幂等键：SHA256(provider + model + messages + tools)
相同幂等键的并发请求：first-write-wins
```

#### 崩溃恢复

```
Worker 崩溃时正在进行的 LLM Call → 下次重试时检测幂等键
→ 若是自己发起的 → 等待完成或标记 FAILED
→ 若是其他 Worker → 返回已有结果
```

------

### §7.12 Scenario Execution 状态机

**关联**：Phase1 场景执行

#### 状态定义

每个 Scenario 执行有独立状态：

| 状态            | 含义             |
| --------------- | ---------------- |
| `PENDING`       | 等待执行         |
| `AGENT_RUNNING` | Agent 循环执行中 |
| `COMPARING`     | 执行完毕，对比中 |
| `ATTRIBUTING`   | 归因分析中       |
| `DONE`          | 完成             |
| `ERROR`         | 异常             |

#### 状态图

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> AGENT_RUNNING: start
    AGENT_RUNNING --> COMPARING: all_nodes_done
    AGENT_RUNNING --> ERROR: unhandled_exception
    COMPARING --> ATTRIBUTING: mismatch_detected
    COMPARING --> DONE: match
    ATTRIBUTING --> DONE: attribution_done
    DONE --> [*]
    ERROR --> [*]
```

#### 不变式

```
1. 每个 Scenario 必须走 COMPARING（即使 pass 也要比对）
2. 归因（ATTRIBUTING）仅在 mismatch 时触发
3. DONE 必须有明确的 verdict（match=True/False）
```

#### 并发保护

```
Scenario 之间完全独立，可并行执行
同一 Scenario 的多次执行（重试）通过 idempotency_key 合并
```

#### 崩溃恢复

```
Scenario 执行中断 → RunStep 记录中断点 → 重新执行时跳过已完成节点
```

#### 超时策略

```
单个 Scenario：5 分钟超时
超时 → ERROR → ScenarioResult.error = "TIMEOUT"
```

#### 发布事件

`ScenarioStarted`, `ScenarioFinished`, `ScenarioComparisonDone`, `ScenarioAttributionDone`

------

## 第 8 章 分布式与可靠性设计

### 8.1 可靠性设计原则

| 原则         | 具体措施                                      |
| ------------ | --------------------------------------------- |
| **失效安全** | 组件崩溃不影响整体；沙箱隔离；Worker 无状态   |
| **幂等设计** | 所有写操作幂等键；LLM 调用幂等；编译幂等      |
| **可恢复**   | 每个阶段持久化；崩溃后从最后状态恢复          |
| **最终一致** | 写后读保证（最终一致 < 1s）；状态机保证强一致 |
| **超时控制** | 所有 IO 操作有超时；超时→降级/重试            |
| **断路器**   | LLM 调用连续失败 3 次 → 断路器打开            |

### 8.2 幂等性设计（各层）

#### 8.2.1 API 层幂等

```
POST /runs
  Header: Idempotency-Key: {uuid}
  → redis.setnx(idemp_key, IN_PROGRESS, ttl=600s)
  → 业务处理
  → redis.set(idemp_key, result_ref, ttl=86400s)
  → MySQL 持久化

重复请求：
  存在且 IN_PROGRESS → 409 Conflict 或 202 Accepted
  存在且有 result_ref → 200 OK（返回缓存结果）
```

#### 8.2.2 Worker 层幂等

```
Phase Step 执行：
  每个 Step 有 idempotency_key = run_id + step_name + iteration_index
  → 执行前检查
  → 执行
  → 写入 Step 结果

崩溃恢复：
  Step RUNNING 且 updated_at > 30min → 重置为 PENDING 重新执行
```

#### 8.2.3 LLM 调用幂等

```
幂等键 = SHA256(provider + model + normalized_messages + tools + output_schema)
→ Redis setnx(idem_key, result, ttl=3600s)
→ 相同请求直接返回缓存结果（节省 token）
```

#### 8.2.4 编译幂等

```
composite_code overall_hash → 查询 CodeSnapshotRepository
  存在 → 复用 compile_result（相同代码无需重复编译）
  不存在 → 执行编译 → 存入 snapshot
```

### 8.3 分布式锁设计

#### 8.3.1 锁类型

| 锁           | 用途                     | TTL   | 算法    |
| ------------ | ------------------------ | ----- | ------- |
| Run 锁       | Worker 认领 Run          | 30min | Redlock |
| Phase 锁     | 防止同一 Run 两个 Worker | 15min | Redlock |
| Container 锁 | 容器分配                 | 10min | Redlock |
| 版本写入锁   | 模板版本号自增           | 5s    | Redlock |
| 领导选举     | Cron Beat 单例           | 15s   | Redlock |

#### 8.3.2 Redlock 实现

```python
class DistributedLock:
    async def acquire(self, key: str, ttl_s: int) -> bool:
        """尝试获取锁（TTL 到期自动释放）"""

    async def release(self, key: str, token: str) -> None:
        """释放锁（仅持有者能释放，Lua 脚本保证原子性）"""
```

#### 8.3.3 死锁预防

```
1. 所有锁 TTL 必须 > 操作超时时间
2. 禁止嵌套锁（同一线程不重复 acquire）
3. 超时锁自动释放（Redlock 自动）
4. 锁申请超时：5s，超时放弃
```

### 8.4 领导选举（单例任务）

#### 8.4.1 需要单例的任务

```
- Cron Beat（定时调度器）
- 孤儿 Run 清理任务（每 5min）
- MongoDB outbox 补偿任务（每 1min）
- 过期幂等键清理任务（每 10min）
```

#### 8.4.2 实现

```
Redis Redlock 选举：
  尝试获取 lock:leader:{task_name}
  TTL = 15s，续约每 5s
  成功 → 执行任务
  失败 → 等待下一次选举

选举周期 = 15s（确保 leader 崩溃后 15s 内选出新 leader）
```

### 8.5 断路器设计

```python
class CircuitBreaker:
    FAILURE_THRESHOLD = 3      # 连续失败 3 次
    RECOVERY_TIMEOUT = 60s     # 60s 后尝试半开
    HALF_OPEN_MAX_CALLS = 1    # 半开时最多 1 个请求

    def call(self, fn):
        if self.state == OPEN:
            raise CircuitOpenError
        try:
            result = fn()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            if self.failure_count >= self.FAILURE_THRESHOLD:
                self.state = OPEN
            raise
```

**应用场景**：

- LLM Provider 调用（连续 3 次失败 → 断路）
- MongoDB 写入（连续 3 次失败 → 降级到 MySQL outbox）
- Docker 操作（连续 2 次失败 → 降级到本地编译）

### 8.6 补偿与回滚

#### 8.6.1 Saga 补偿链

```
Run 创建成功 → Phase1 开始 → Phase2 开始 → Phase3 开始

任意步骤失败 → 按以下顺序补偿：
  Phase3 失败 → 无需补偿（无持久化变更）
  Phase2 失败 → 删除已创建的 CodeSnapshot
  Phase1 失败 → 无需补偿（无持久化变更）
```

#### 8.6.2 Outbox 模式（MongoDB 写入保障）

```
步骤：
  1. 业务操作 + outbox 记录 写在同一 MySQL 事务
  2. 后台任务每 1min 扫描 outbox
  3. 执行 MongoDB 写入
  4. 删除 outbox 记录

崩溃恢复：重启后继续扫描未完成的 outbox
```

### 8.7 崩溃恢复策略（按场景）

| 场景                        | 影响               | 恢复方式                                     |
| --------------------------- | ------------------ | -------------------------------------------- |
| Worker 在 Phase1 中崩溃     | Run 卡在 RUNNING   | 30min 后 Cron 重入队，从最后 RunStep 恢复    |
| Worker 在 Phase3 迭代中崩溃 | Run 卡在 RUNNING   | 恢复后从 `outer_fix_iter` 重新进入对应子状态 |
| API 节点崩溃                | 无状态，不影响     | LB 自动路由到其他节点                        |
| Redis Cluster 部分节点故障  | 缓存可用，锁不可用 | 降级：锁操作失败 → 拒绝写入                  |
| MySQL 主库故障              | 写不可用           | 自动切换到从库（只读）；写操作返回 503       |
| MongoDB 副本集故障          | Trace 写入暂缓     | 降级到 outbox + 本地 buffer                  |
| 沙箱容器不响应              | Run 卡住           | 容器超时（5min）→ 杀容器 → 标记 FAILED       |

### 8.8 限流与背压

```python
# API 层限流（按 user_id）
@limiter.limit("100/minute", key_func=lambda: g.user_id)
async def create_run(): ...

# Worker 队列限流
- phase1_queue: max 50 并发
- phase2_queue: max 30 并发
- phase3_queue: max 10 并发（沙箱资源密集）

# LLM 限流（按 provider）
- Claude: 50 req/min (user), 100 req/min (app)
- OpenAI: 60 req/min
```

### 8.9 监控与告警

| 指标                       | 告警阈值            |
| -------------------------- | ------------------- |
| Run 失败率                 | > 10% (5min window) |
| Phase1 平均耗时            | > 5min              |
| LLM 错误率                 | > 5%                |
| MongoDB 写入延迟 P99       | > 500ms             |
| 沙箱容器获取等待           | > 30s               |
| 活跃 Run 卡在 RUNNING > 2h | > 0                 |
| Worker CPU 使用率          | > 80% (持续 5min)   |

------

## 第 9 章 扩展性机制

### 9.1 插件注册体系总览

| 扩展点          | 接口/基类               | 注册位置                           | 示例                 |
| --------------- | ----------------------- | ---------------------------------- | -------------------- |
| 新 Handler      | `HandlerStep` 子类      | `HandlerRegistry.register()`       | `coverage_check`     |
| 新 Simulator    | `NodeSimulator` 子类    | `NodeSimulatorFactory.register()`  | `WasmSimulator`      |
| 新 Validator    | `ForestVisitor` 子类    | `VisitorRegistry.register()`       | `D3ANamingCheck`     |
| 新 LLM Provider | `LLMProvider` 子类      | `LLMProviderFactory.register()`    | `GeminiProvider`     |
| 新代码生成目标  | `CodegenTarget` 子类    | `CodegenTargetFactory.register()`  | `RustCodegenTarget`  |
| 新沙箱运行时    | `SandboxRuntime` 子类   | `SandboxRuntimeFactory.register()` | `FirecrackerRuntime` |
| 新 Phase        | `BasePipelineStep` 子类 | `PipelineBuilder` 装配             | `Phase4PerfTest`     |

### 9.2 Handler 扩展（示例：新增 coverage_check）

```python
# 1. 实现 Handler
class CoverageCheckHandler(HandlerStep):
    name = "coverage_check"
    handler_order = 30  # 在 scenario_run 之后

    async def _handle(self, state: CascadeState, trace: TraceEmitter) -> HandlerOutcome:
        coverage = compute_coverage(state["scenario_results"])
        if coverage < 0.8:
            return HandlerOutcome(
                decision="fail",
                reason=f"Coverage {coverage} < 0.8",
                issues=[],
            )
        return HandlerOutcome(decision="pass", reason="", issues=[])

# 2. 注册（boot 时或配置驱动）
handler_registry.register(CoverageCheckHandler)

# 3. 无需修改 Phase1 编排逻辑，HandlerChainExecutor 自动包含
```

### 9.3 LLM Provider 扩展（示例：加 Gemini）

```python
# 1. 实现 Provider
class GeminiProvider(LLMProvider):
    async def chat(self, messages, tools, output_schema, ...) -> LLMResponse:
        response = await gemini.generate_content(
            contents=messages_to_gemini_format(messages),
            tools=tools,
            generation_config={"response_mime_type": "application/json"} if output_schema else None,
        )
        return LLMResponse(...)

# 2. 注册
llm_provider_factory.register("gemini", GeminiProvider)

# 3. 配置使用
# settings: LLM_DEFAULT_PROVIDER=gemini
# 或在 Template 中指定 provider_override="gemini"
```

### 9.4 CodegenTarget 扩展（示例：加 Rust）

```python
# 1. 实现 Target
class RustCodegenTarget(CodegenTarget):
    language = "rust"

    def bundle_class_template(self, bundle, nodes) -> str:
        return f"pub struct {bundle.name} {{ ... }}"

# 2. 注册
codegen_target_factory.register("rust", RustCodegenTarget)

# 3. 使用
codegen_target = codegen_target_factory.get("rust")
```

### 9.5 SandboxRuntime 扩展（示例：加 Firecracker）

```python
# 1. 实现 Runtime
class FirecrackerRuntime(SandboxRuntime):
    async def run_command(self, cmd, stdin, timeout_s, cpu_limit, mem_limit_mb):
        # 使用 Firecracker SDK
        ...

# 2. 注册
sandbox_runtime_factory.register("firecracker", FirecrackerRuntime)

# 3. 配置
# settings: SANDBOX_RUNTIME=firecracker
```

### 9.6 Schema 演进策略

#### 9.6.1 CascadeState Schema 演进

```python
# 当前版本：schema_version = 1
# 升级到 v2：

MIGRATIONS: dict[int, Callable[[dict], dict]] = {
    1: lambda s: {
        **s,
        "schema_version": 2,
        # 新增字段默认值
        "retry_count": 0,
        # 旧字段重命名
        "provided_scenarios": s.get("scenarios", []),  # v1 教训
    },
    2: lambda s: {**s, "schema_version": 3, ...},
}

def upgrade_state(state: dict, target_v: int) -> CascadeState:
    current = state.get("schema_version", 1)
    while current < target_v:
        state = MIGRATIONS[current](state)
        current += 1
    return state
```

#### 9.6.2 向后兼容原则

```
1. 只添加字段，不删除字段
2. 只添加枚举值，不移除枚举值
3. 添加的字段必须有默认值
4. 重大变更：schema_version +major
```

#### 9.6.3 NodeTemplateDefinition 演进

```python
class NodeTemplateDefinition:
    schema_version: int = 1

    def upgrade(self, target_v: int) -> "NodeTemplateDefinition":
        # 按版本渐进升级
```

### 9.7 特性开关（灰度发布）

```python
# 开关定义
FEATURE_FLAGS = {
    "phase3_direct": FeatureFlag(key="phase3_direct", enabled=False, rollout=0.0),
    "rust_codegen": FeatureFlag(key="rust_codegen", enabled=True, rollout=0.1),
    "new_handler_chain": FeatureFlag(key="new_handler_chain", enabled=False, user_ids=[1,2,3]),
}

# 使用
if await ff.is_enabled("rust_codegen", user_id):
    target = codegen_target_factory.get("rust")
else:
    target = codegen_target_factory.get("cpp")
```

------

## 第 10 章 TBD（D3A 留白）与迁移路径

### 10.1 D3A 相关 TBD 项

| TBD 项             | 当前状态     | 依赖 D3A 什么        | 影响模块         | 现在能定的事                            |
| ------------------ | ------------ | -------------------- | ---------------- | --------------------------------------- |
| D3A 节点 Schema    | **完全 TBD** | 具体指令定义         | node-definition  | `NodeTemplateDefinition` 的结构载体已定 |
| D3A 输入格式       | **完全 TBD** | 指令输入格式         | case-synthesizer | 输入规范化为 JSON Schema（内容待填）    |
| D3A 输出格式       | **完全 TBD** | 指令输出格式         | case-synthesizer | 同上                                    |
| D3A → C++ 映射模板 | **完全 TBD** | 指令到代码的对应关系 | codegen-target   | `CodegenTarget` 接口已定，模板槽位已留  |
| D3A 节点模拟器     | **完全 TBD** | 模拟 D3A 节点行为    | node-simulator   | `HybridSimulator` 接口已定              |
| D3A 内置模板包     | **完全 TBD** | 官方 D3A 节点集      | node-library     | seed 数据位置已定                       |

### 10.2 后续补全 D3A 的操作路径

```
1. 确定 D3A 指令规范（JSON Schema + 语义）
   → 产出：dd3a-schema.json

2. 实现 codegen-target
   → 新建 CppD3ACodegenTarget 类
   → 注册 factory
   → 不动现有 Phase2 逻辑

3. 填充 node-library 种子数据
   → JSON Pack 导入
   → 不动 node-registry

4. 实现/扩展 simulator
   → 实现 D3ASimulator
   → 注册到 factory

5. 扩展 case-synthesizer
   → 加 D3A 格式支持
   → 不动 sandbox-executor
```

### 10.3 v1 → v2 迁移路径（针对已实现的 Phase1）

```
1. CascadeState schema_version 字段从无 → 1
   → 启动时自动升级

2. provided_scenarios + scenarios 合并
   → 代码层：CascadeState.scenarios 唯一来源
   → 数据迁移：MySQL 中 old scenarios + provided_scenarios → new scenarios
   → 迁移脚本：migrate_01_merge_scenarios.py

3. PhaseStateMachine 替代 PhaseRouter
   → 移除 PhaseRouter 所有条件判断
   → 替换为 phase_state_machine.next_phase()
   → 回归测试覆盖

4. Forced Schema 输出
   → llm-output-schema 服务化
   → 所有 LLM 调用改走 forced_chat()
   → 回归测试验证无自由文本推断

5. ToolUseResult 严格分离
   → 扫描所有 simulator 实现
   → 检查 output_json / content 分离
   → 回归测试验证
```

### 10.4 术语表（完整版）

| 术语            | 类型   | 定义                                                         |
| --------------- | ------ | ------------------------------------------------------------ |
| Aggregate Root  | DDD    | 唯一修改入口：WorkflowRun、CascadeForest、NodeTemplate、GraphReview |
| BC              | DDD    | Bounded Context，限界上下文                                  |
| Entity          | DDD    | 有生命周期：Bundle、NodeInstance、Edge、RunStep、GraphVersion |
| Value Object    | DDD    | 不可变：NodeTemplateDefinition、CascadeState、SimResult      |
| Domain Service  | DDD    | 无状态逻辑：DesignValidator、PhaseStateMachine、NodeSimulatorFactory |
| ACL             | DDD    | Anti-Corruption Layer，集成层                                |
| SimContext      | 系统   | Simulator 执行上下文                                         |
| SimResult       | 系统   | Simulator 执行结果                                           |
| HandlerOutcome  | 系统   | Phase1 Handler 执行结果                                      |
| Fix Loop        | 系统   | Phase3 外层修复循环（outer_fix_iter）                        |
| Idempotency Key | 可靠性 | 用于幂等控制的唯一键                                         |
| Redlock         | 可靠性 | Redis 分布式锁算法                                           |
| Outbox          | 可靠性 | 可靠消息模式：事务 + 异步消息                                |
| Circuit Breaker | 可靠性 | 断路器：快速失败防止级联                                     |
| Schema Version  | 演进   | 用于追踪状态对象的格式版本                                   |
| D3A             | 业务   | 指令集规范（待定）                                           |

### 10.5 错误码总表

| 错误码         | 含义             | HTTP 状态 | 处理方式               |
| -------------- | ---------------- | --------- | ---------------------- |
| `RUN_001`      | Run 不存在       | 404       | 幂等返回成功           |
| `RUN_002`      | 状态不允许此操作 | 409       | 返回错误信息           |
| `RUN_003`      | Run 已终态       | 409       | 幂等返回成功           |
| `GRAPH_001`    | 图不存在         | 404       | -                      |
| `GRAPH_002`    | 版本号冲突       | 409       | 提示刷新               |
| `TEMPLATE_001` | 模板不存在       | 404       | -                      |
| `TEMPLATE_002` | 权限不足         | 403       | -                      |
| `PHASE_001`    | Phase 执行超时   | 504       | 重新入队               |
| `PHASE_002`    | Handler 链失败   | 200       | verdict 已在 result 中 |
| `LLM_001`      | LLM 调用失败     | 503       | 断路器                 |
| `LLM_002`      | Schema 验证失败  | 500       | 重试 2 次              |
| `SANDBOX_001`  | 沙箱获取超时     | 503       | 重试                   |
| `SANDBOX_002`  | 编译失败         | 200       | verdict 在 result 中   |
| `IDEM_001`     | 幂等键冲突       | 409       | 返回已有结果           |
| `LOCK_001`     | 获取锁超时       | 503       | 重试                   |

### 10.6 领域事件总表

| 事件                    | 发布时机             | 消费者                       |
| ----------------------- | -------------------- | ---------------------------- |
| `RunCreated`            | 创建 Run             | WebSocket, AuditLog          |
| `RunStarted`            | Run 被 Worker 认领   | WebSocket, AuditLog          |
| `RunFinished`           | Run 达到终态         | WebSocket, AuditLog          |
| `RunCancelled`          | Run 被取消           | WebSocket, AuditLog          |
| `RunFailed`             | Run 失败             | WebSocket, AuditLog, Metrics |
| `Phase1Started`         | Phase1 开始          | WebSocket                    |
| `Phase1Finished`        | Phase1 结束          | WebSocket, Metrics           |
| `Phase2Started`         | Phase2 开始          | WebSocket                    |
| `Phase2Finished`        | Phase2 结束          | WebSocket, Metrics           |
| `Phase3Started`         | Phase3 开始          | WebSocket                    |
| `Phase3Finished`        | Phase3 结束          | WebSocket, Metrics           |
| `FixLoopStarted`        | 修复循环开始         | WebSocket                    |
| `FixIterationStarted`   | 每次修复迭代开始     | WebSocket                    |
| `FixIterationFinished`  | 每次修复迭代结束     | WebSocket                    |
| `FixLoopEnded`          | 修复循环结束         | WebSocket, Metrics           |
| `HandlerStarted`        | Handler 开始         | Trace                        |
| `HandlerFinished`       | Handler 结束         | Trace                        |
| `StepStarted`           | Step 开始            | Trace                        |
| `StepFinished`          | Step 结束            | Trace, Metrics               |
| `TemplatePublished`     | 模板发布             | TemplateRegistry, Cache      |
| `TemplateUpdated`       | 模板更新             | TemplateRegistry, Cache      |
| `TemplateDeprecated`    | 模板废弃             | TemplateRegistry             |
| `GraphVersionSaved`     | 图版本保存           | AuditLog                     |
| `GraphVersionValidated` | 图版本通过验证       | WebSocket                    |
| `ReviewInitiated`       | 评审发起             | AuditLog                     |
| `ReviewApproved`        | 评审通过             | AuditLog, WebSocket          |
| `ReviewRejected`        | 评审拒绝             | AuditLog, WebSocket          |
| `CommentAdded`          | 批注添加             | WebSocket                    |
| `CommentResolved`       | 批注已解析           | WebSocket                    |
| `ContainerAcquired`     | 沙箱容器获取         | Metrics                      |
| `ContainerReleased`     | 沙箱容器释放         | Metrics                      |
| `LLMCallCompleted`      | LLM 调用完成         | Metrics, AuditLog            |
| `RunStatusTransitioned` | Run 状态转移（通用） | Trace                        |

------

*文档版本: v2.0* *创建日期: 2026-04-27* *下次评审: D3A 规范确定后补全 TBD 项*
