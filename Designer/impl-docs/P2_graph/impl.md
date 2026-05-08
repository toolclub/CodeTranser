# Graph 画布 实施计划 (P2 impl)

> 此文档面向：**开发同学（含 AI 辅助）**。`spec.md` 给业务对齐，`impl.md` 给工程落地。
>
> 顶层关联：`../D3A顶层模块级设计文档.md` §2.1 行 5.1–5.13、§4 状态机、§5 DDL、§7 跨 BC 协议。

---

## 1. 我的范围（与 spec 对应）

| 我做 | 我不做（谁做） |
|---|---|
| `src/d3a/graph/` 全部（领域 + 应用 + 适配器 + 模拟器 + API） | 命令模板（P1） |
| 本 BC 的 DDL 草案（交 P5 收口编号） | 平台底座 / 横切组件（P5） |
| 本 BC 的 OpenAPI / WS 协议 | 前端组件实现（P6） |
| 单元测试 + 集成测试 | 全链路 e2e（QA Lead） |

---

## 2. 暴露给下游的契约（M1 必须冻结）

> 下游（P3 / P4 / P6）拿这些 mock 跑代码，不等我落地。

### 2.1 Port（被下游 import）

| Port | 给谁 | 用途 |
|---|---|---|
| `ForestRepositoryPort` | P3 Execution | 写场景：执行起点拿森林快照 |
| `ForestReadOnlyPort` | P3 / P4 Phase1 | 只读：拿冻结森林版本喂给 Phase1 |
| `SimulatorEventPort` | P6 前端 | WebSocket 推送模拟轨迹 |

### 2.2 对外 API

| 接口 | 方式 | 调用方 |
|---|---|---|
| `POST /api/graph/forests` 等 CRUD | REST | P6 前端 |
| `WS /api/graph/forests/{id}/collab` | WebSocket | P6 前端（协同 + 模拟器推送） |

→ 详细 schema 维护在 `src/d3a/graph/api/schemas/`，并产出 `openapi.yaml` 供前端联调。

---

## 3. 上游依赖

| 依赖 | 谁提供 | 兜底 |
|---|---|---|
| `CommandSnapshotReadPort`（读命令模板冻结快照） | P1 | P1 未交付前用 in-memory mock |
| MySQL / Redis / 事件总线基础设施 | P5 | 用 docker-compose 本地起 |
| alembic 编号 | P5 统一收口 | 临时用 `local_NNN_xxx.py` 占位 |
| 鉴权 / 审计 | P5 横切 | 临时用 noop adapter |

---

## 4. 开发顺序（M1 → M6）

| 里程碑 | 内容 | 验收 |
|---|---|---|
| M1 | spec.md / impl.md / agent.md 评审稿；冻结 Port 与 OpenAPI mock | 架构 + P1/P3/P6 会签 |
| M2 | DDL 草案 + alembic migration（local 编号）；in-memory adapter 跑通最小用例 | DBA + P5 |
| M3 | Forest / Tree / Node / Edge 聚合根 + VO + 领域服务 + 单测 | Code Review |
| M4 | SQL Adapter + Redis 缓存 Adapter + 事件订阅；接 P1 真实 Port 联调 | P1 联调 |
| M5 | Cascade / Bundle / Simulator 子系统；REST + WS 接入；与 P6 编辑器联调 | P6 联调 |
| M6 | 集成测试 + 性能基线 + 自验收 Demo | QA |

---

## 5. DDL（草案，交 P5 收口）

7 张主表（字段细节略，详见 `migrations/graph/`）：

| 表 | 主键 | 关键约束 |
|---|---|---|
| `graph_forest` | id | name 唯一索引 / status 状态机 |
| `graph_tree` | id | forest_id 外键 / 复合索引 |
| `graph_node` | id | tree_id 外键 / `(command_template_id, version)` 联合冻结 |
| `graph_edge` | id | from_node / to_node 外键 / type CHECK（MySQL 5.7 用触发器） |
| `graph_cascade` | id | scope JSON / 触发节点外键 |
| `graph_bundle` | id | contained_node_ids JSON / 暴露口 schema |
| `graph_simulator_run` | id | trace JSON / forest 版本锁 |

> 已发布森林相关表通过触发器禁止 UPDATE，强制不可变快照。

---

## 6. 配置项

| key | 默认 | 说明 |
|---|---|---|
| `graph.simulator.max_steps` | 10000 | 单次模拟轨迹上限 |
| `graph.collaboration.ws_max_clients` | 10 | 单森林同时在线 |
| `graph.cache.forest_ttl_seconds` | 300 | 热森林缓存 TTL |
| `graph.dag.max_nodes` | 500 | 单森林节点上限（spec §7） |
| `graph.dag.max_edges` | 2000 | 单森林边上限 |

---

## 7. 本地起服 / 调试

```bash
# 起依赖
docker-compose -f docker-compose.dev.yml up -d mysql redis

# 跑迁移
alembic -c migrations/graph/alembic.ini upgrade head

# 起 API
python -m d3a.graph.api.rest.main --reload

# 起模拟器 worker（独立进程）
python -m d3a.graph.simulator.worker
```

调试用：`d3a-cli graph dump-forest <id>` 导出森林为 JSON。

---

## 8. 测试策略

| 层 | 工具 | 覆盖率目标 |
|---|---|---|
| 单元（domain/） | pytest，纯内存 | ≥ 90% |
| 单元（application/） | pytest + in-memory adapter | ≥ 80% |
| 集成（infrastructure/） | pytest + testcontainers（真实 MySQL/Redis） | 关键路径全覆盖 |
| 模拟器场景 | pytest + 录制黄金轨迹 | 5 个典型用例 |
| 协同 WS | pytest-asyncio + 多 client 并发 | 3 个冲突场景 |

---

## 9. 与下游的联调点

| 联调对方 | 联调内容 | 时机 |
|---|---|---|
| P1 | `CommandSnapshotReadPort` 真实接通 | M4 |
| P3 | Execution 拉取森林快照 → 跑 Run | M5 |
| P4 | Phase1 输入森林 JSON 格式 | M5 |
| P6 | REST + WS 全链路（建森林 → 模拟） | M5 |

---

## 10. 自验收清单（M6 提测前过一遍）

- [ ] spec.md 全部功能可演示
- [ ] 单元测试覆盖率达标
- [ ] 7 张表 DDL 已交 P5 收口编号
- [ ] OpenAPI / WS 协议已发给前端
- [ ] 性能：500 节点森林打开 ≤ 1s，模拟器单步 ≤ 100ms
- [ ] 故障演练：DB 断开后 30s 内恢复
- [ ] 文档：spec / impl / agent / prototype 四件套齐全

---

## 11. 风险与回退

| 风险 | 触发条件 | 回退策略 |
|---|---|---|
| Cascade 规则与模拟器交互复杂 | M5 联调发现死锁 | Cascade 先简化为单层触发，下版迭代 |
| WS 协同冲突解决 | 多人压测发现丢更新 | 退回乐观锁版本号方案 |
| 性能不达标 | 500 节点 > 1s | 节点列表分页 + 虚拟滚动（前端） |
