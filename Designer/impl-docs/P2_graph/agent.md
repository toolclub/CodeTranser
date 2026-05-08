# Graph 画布 AI 辅助参考 (P2 agent)

> 此文档面向：**AI 辅助工具（Claude Code / Cursor / Copilot）与新协作者**。
>
> 用法：在让 AI 写本 BC 任何代码之前，把这份文档作为系统提示喂给它。AI 据此理解目录边界、分层约束、跨 BC 协议。
>
> 配套：`spec.md`（业务）、`impl.md`（工程）、`prototype.html`（原型）。

---

## 1. 给 AI 的总则（贴到 system prompt 顶部）

1. 本 BC 边界 = `src/d3a/graph/`，不允许向外写
2. **分层硬规矩**：
   - `domain/` 不允许 import `sqlalchemy / redis / fastapi / httpx`
   - `application/` 只能 import `domain/` 与 `ports/`，不能 import `infrastructure/`
   - `infrastructure/` 实现 `ports/`，是 SQL/Redis/HTTP 的唯一栖息地
3. **跨 BC 硬规矩**：
   - 想读上游（P1 命令模板）→ 仅通过 `ports/readonly/` 的接口
   - 不允许 `from d3a.command... import 聚合根 / 实体`
   - 跨 BC 引用对象只用 id + 版本号
4. **AI 写代码前先做的事**：
   - 业务规则改动 → 看 `spec.md` §4 不变量
   - DDL 改动 → 看 `impl.md` §5
   - 对外 API 改动 → 看 `impl.md` §2
5. AI 生成的领域规则 / 状态机 / 并发约束代码**必须人审**才合 main

---

## 2. 目录结构

> 只列目录，不列文件。每个目录用途写在右边。

```
src/d3a/graph/                              # 本 BC 根包，对外唯一 import 入口
├── domain/                                 # 领域层：业务规则与不变量集中处，纯 Python，无外部 IO
│   ├── forest/                             # Forest 子域：森林 / 树 / 节点 / 节点关系等聚合根、实体、值对象、领域事件
│   ├── dag/                                # DAG 子域：拓扑排序、Visitor、环检测等纯算法，全部值对象与无副作用服务
│   ├── cascade/                            # 级联子域：级联规则、触发匹配、传播策略
│   ├── bundle/                             # 节点束子域：Bundle 聚合根、暴露口契约、嵌套规则
│   └── shared/                             # 子域间共享：共用 VO（NodeId / Position / EdgeType 等）
│
├── ports/                                  # 端口层：领域定义的对外接口（Protocol/ABC），不含实现
│   ├── repositories/                       # 仓储口：Forest / Cascade / Bundle / SimulatorRun 各自的读写口
│   ├── readonly/                           # 跨 BC 只读口：访问 P1 命令模板快照、P5 鉴权信息
│   └── eventbus/                           # 事件总线口：发布本 BC 领域事件、订阅外部事件
│
├── application/                            # 应用层：用例编排（命令服务 / 查询服务），无业务规则，只组合
│   ├── commands/                           # 写场景用例：建森林、加节点、绑命令、连边、改级联、打包 Bundle…
│   ├── queries/                            # 读场景用例：森林概览、节点详情、影响面分析
│   └── dtos/                               # 跨层 DTO：API ↔ application ↔ domain 的隔离层
│
├── infrastructure/                         # 基础设施适配器层：实现 ports/，唯一可触碰外部技术的地方
│   ├── sql/                                # MySQL Adapter：ORM 映射 + 仓储实现 + 事务管理
│   ├── cache/                              # Redis Adapter：热森林缓存、分布式锁、协同光标
│   ├── eventbus/                           # 事件总线 Adapter：实现发布订阅，对接 Kafka/Redis Streams
│   └── readonly/                           # 跨 BC 只读 Adapter：调用 P1 暴露的命令模板查询接口
│
├── simulator/                              # 模拟器子系统：本身是一个完整的小六边形架构
│   ├── domain/                             # 模拟轨迹、断点、单步状态机
│   ├── application/                        # 启动模拟、单步、回放、暂停、影响面分析等用例
│   └── infrastructure/                     # 与 LangGraph 运行时只读对接、轨迹持久化
│
└── api/                                    # 驱动适配器：HTTP / WebSocket 暴露给 P6 前端
    ├── rest/                               # FastAPI 路由：森林 / 节点 / 边 / Cascade / Bundle CRUD
    ├── ws/                                 # WebSocket：协同光标广播、模拟器轨迹推送
    └── schemas/                            # Pydantic 请求/响应模型，是 application DTO 的对外形态

migrations/graph/                           # 本 BC 的 alembic 迁移脚本（编号由 P5 平台底座统一收口）

tests/
├── unit/graph/                             # 单元测试：纯领域逻辑，不接外部，覆盖率目标 ≥ 80%
├── integration/graph/                      # 集成测试：testcontainers 起真实 MySQL/Redis 跑全链路
└── e2e/graph/                              # 端到端测试：与前端 stub 联动，建森林 → 模拟器走通

impl-docs/P2_graph/                         # 本 BC 的设计 / 实施 / 原型四件套
                                            # （即本目录：spec.md / impl.md / agent.md / prototype.html）
```

---

## 3. AI 写代码时的常见反模式（**禁止**）

| 反模式 | 正确做法 |
|---|---|
| `domain/forest/aggregates.py` 里 `import sqlalchemy` | SQL 操作放 `infrastructure/sql/`，领域层只定义 Port |
| 让 `Node` 聚合直接持有 `CommandTemplate` 对象 | 只持 `(command_template_id, version)`，跨 BC 引用 |
| `application/commands/` 里写业务校验 | 业务规则归 `domain/`，application 只编排 |
| `api/rest/` 里直接 import `domain/` 的聚合根并序列化返回 | 用 `application/dtos/` 转换后由 `api/schemas/` 返回 |
| 在 `domain/` 抛 HTTP 状态码异常 | 抛 `DomainError`，由 `api/` 层转 HTTP |
| 跨 BC 时 `from d3a.command.domain... import` | 只能 `from d3a.graph.ports.readonly... import` |

---

## 4. 推荐 AI 协作工作流

| 任务类型 | AI 起草 | 人评审重点 |
|---|---|---|
| 加一个新聚合根 | 类骨架 + VO + 单测样板 | 不变量 / 状态机 / 并发约束 |
| 加一个 application 用例 | 编排骨架 + DTO + 测试桩 | 事务边界 / 异常路径 / 跨聚合一致性 |
| 写 SQL Adapter | ORM 映射 + 仓储实现 | 索引 / 事务隔离级别 / 批量 N+1 |
| 改 DDL | migration 脚本草稿 | 字段语义 / 索引取舍 / 不可变约束触发器 |
| 改对外 API | OpenAPI yaml + Pydantic schema | 向后兼容 / 鉴权点 / 限流 |
| 写单元测试 | 测试样板 + fixture | 边界 / 并发 / 异常场景 |

---

## 5. AI 写代码前的"自检清单"

让 AI 在动手前回答：

1. 我要改的代码属于哪一层（domain / application / infrastructure / api / simulator）？
2. 这一层允许 import 什么、不允许 import 什么？
3. 我要表达的是业务规则还是技术细节？业务规则该不该提到 `domain/`？
4. 这个改动会影响 `ports/` 的对外契约吗？影响的话下游谁受影响？
5. 是否需要新增 / 修改 DDL？需要的话写到 `migrations/graph/`，并 @ P5。
6. 是否需要新增对外 API？需要的话同步改 `openapi.yaml`，并 @ P6。

> 答不上来就**先查 spec.md / impl.md，再写代码**。

---

## 6. 给新协作者的 5 分钟上手路径

1. 读 `spec.md` 第 0、2、3、4 节 → 知道画布是干什么的、有什么不变量
2. 看 `prototype.html` → 知道用户长啥样在用
3. 扫一遍本文件第 2 节目录树 → 知道代码在哪
4. 读 `impl.md` 第 2、3 节 → 知道我跟谁握手
5. 跑 `impl.md` 第 7 节本地起服 → 看到东西转起来
