# Graph 画布 业务规格 (P2 spec)

> 此文档面向：**业务方 / 客户 / 产品 / 评审会**。给"非工程师"看，用于澄清边界、对齐预期、签字确认范围。
>
> 配套文档：`impl.md`（开发实施）、`agent.md`（AI 辅助参考）、`prototype.html`（低保真原型）。
>
> 顶层关联：`../D3A顶层模块级设计文档.md` §2.1 行 5.1–5.13、§10.5 业务模型。

---

## 0. 一句话定位

画布（Graph）= D3A 用户用来"画"业务流程的核心交互区。把零散的命令模板（P1 已建好的可复用积木）拼装成一张**有执行顺序、有数据流、有触发条件**的森林，供下游 Phase1/2/3 推理使用。

---

## 1. 目标用户与典型场景

| 角色 | 在画布上做什么 |
|---|---|
| 业务专家 | 拖拽节点、连边，把脑子里的流程画出来 |
| 算法 / 开发 | 复用别人画好的森林做 Phase1 输入，或对森林做断点单步 |
| 审核 / Reviewer | 看到一张森林就能读懂业务流程，不用看代码 |

**主路径**：登录 → 打开/新建森林 → 拖拽节点 → 绑命令模板 → 连边 → 模拟跑通 → 提交评审 → 进 Phase1。

---

## 2. 核心概念（与客户对齐用语）

| 概念 | 含义 | 业务方语言 |
|---|---|---|
| 森林 CascadeForest | 一个完整业务包的最大单位（**扁平容器**：所有节点 / 边 / Bundle / Cascade 都直接挂在森林上） | "一个项目" |
| 节点 NodeInstance | 业务最小可执行单元，绑一个命令模板快照 | "一个步骤" |
| 边 Edge | 节点之间的依赖与触发关系 | "箭头" |
| 节点束 Bundle | 把一组节点打包成可复用、可暴露端口的子流程（**逻辑分组**，不是节点容器） | "子流程 / 模块" |
| 级联 Cascade | 上游变化自动触发下游重算的声明式规则 | "联动" |
| DAG 视图 DagView | 后端从森林**派生**出的图视图（一棵 DAG = 一个连通子图，按 root 切分），不持久化 | "流程拓扑图" |
| 模拟器 Simulator | 不真实执行，沿 DAG 走一遍 | "预演 / 试跑" |

> **没有"树 Tree"这一层**：森林是平铺的；当业务方说"一个流程 / 一棵树"时，技术上对应的是 DagView 或 Bundle。

> 所有概念都对应顶层文档 §10.5 的 D3A 业务对象，不要自创新词。

---

## 3. 功能清单（按用户旅程）

### 3.1 森林管理
- [ ] 新建森林（空白 / 从模板）
- [ ] 复制 / 重命名 / 归档森林
- [ ] 森林版本快照（发布即冻结）
- [ ] 森林概览（统计 / 健康度 / 最近修改）

### 3.2 节点编辑
- [ ] 增 / 删 / 移动 / 重命名节点
- [ ] 绑定 / 解绑 / 替换命令模板（**必锁定快照版本**）
- [ ] 节点参数填写（按命令模板的输入 schema 渲染表单）
- [ ] 节点搜索 / 跳转 / 批量框选

### 3.3 边与图结构
- [ ] 连边 / 删边 / 改边类型（顺序边 seq / 数据流边 data / 条件边 cond）
- [ ] 自动布局 / 手动布局 / 缩略图导航
- [ ] DagView 自动重算（编辑后实时计算多个连通子图、拓扑序、环检测）

### 3.4 级联与束
- [ ] 设置级联规则（A 改了，B 自动重算）
- [ ] 框选打包成 Bundle，暴露输入输出口
- [ ] Bundle 库（复用别人发布的 Bundle）

### 3.5 模拟器
- [ ] 选起点节点启动模拟
- [ ] 单步 / 断点 / 跳过 / 回放
- [ ] 模拟轨迹可视化（节点高亮 + 数据流热力）
- [ ] 影响面分析（改这个节点会冲击谁）

### 3.6 协同
- [ ] 多人同森林编辑（光标 + 选区广播）
- [ ] 改动实时合并（最后写入获胜，冲突高亮）
- [ ] 评论 / @人 / 待办

### 3.7 治理
- [ ] 锁森林（评审中只读）
- [ ] 操作审计（谁在什么时候改了什么）
- [ ] 权限（编辑 / 只读 / 仅评论）

---

## 4. 业务规则（不变量，必须保证）

1. 森林整体不允许成环（DAG 约束；保存前由 dag-compute 校验）
2. 节点必须绑命令模板**快照版本**，不允许引"最新"浮动版本
3. 删除被引用节点必须先解除引用（包括边、Bundle 暴露口、Cascade 触发/动作）
4. Bundle 内部节点不允许引用 Bundle 外部节点（黑盒，由 Bundle 暴露口转发）
5. 已发布森林（GraphVersion）只读，再编辑须新建版本（fork）
6. 同一森林同一时刻最多一名"编辑权"用户，其余只能浏览/评论

---

## 5. 数据结构（**重点：JSON 实体一一展开**）

> 这是 spec 最重要的一节。前后端、画布、Phase1 输入、模拟器、跨 BC 调用全部以下面的 JSON 形态流通。
> 字段语义不达成一致，整个项目不能开工。
>
> 标记说明：✱ 必填 / ◯ 可选 / 🔒 不可变（一旦保存版本即冻结）。
>
> **核心原则**：森林是**扁平容器**。所有节点、边、Bundle、Cascade 都直接挂在 `CascadeForest` 下。
> 没有"Tree"层级；多个不连通的子图由后端用 `dag-compute` 派生为多个 `DagView`（见 5.6）。

---

### 5.1 CascadeForest 森林（顶级聚合根）

森林是顶级对象，对应"一个完整的业务包"。一份森林 = 一个 GraphVersion 的 snapshot 内容。

```json
{
  "id": "fst_01HXABC123",
  "name": "订单结算业务包",
  "description": "下单 → 扣减库存 → 支付 → 结算的端到端流程",
  "owner_id": "u_001",
  "version": 3,
  "status": "draft",
  "schema_version": 1,
  "metadata": {
    "tags": ["finance", "p0"],
    "policy": {
      "max_nodes": 500,
      "max_edges": 2000
    }
  },
  "node_instances": [ /* 见 5.2 */ ],
  "edges":          [ /* 见 5.3 */ ],
  "bundles":        [ /* 见 5.5 */ ],
  "cascades":       [ /* 见 5.4 */ ],
  "created_at": "2026-05-01T10:00:00Z",
  "updated_at": "2026-05-08T14:30:00Z",
  "published_at": null
}
```

| 字段 | 类型 | 必填 | 业务含义 / 约束 |
|---|---|---|---|
| `id` | string ULID | ✱ 🔒 | 系统生成，前缀 `fst_` |
| `name` | string ≤64 | ✱ | 同 owner 下唯一 |
| `description` | string ≤500 | ◯ | 给评审看的说明 |
| `owner_id` | string | ✱ 🔒 | 创建者，决定权限默认范围 |
| `version` | int ≥1 | ✱ | 当前 GraphVersion 版本号；保存即递增（顶层文档 §3.2.2） |
| `status` | enum | ✱ | `draft` / `published` / `archived` |
| `schema_version` | int | ✱ | 数据结构 schema 版本，用于演进 |
| `metadata.tags` | string[] | ◯ | 检索用 |
| `metadata.policy.max_nodes` / `max_edges` | int | ◯ | 容量上限（默认见 §7） |
| `node_instances` | NodeInstance[] | ✱ | **平铺**所有节点，无嵌套结构（详见 5.2） |
| `edges` | Edge[] | ✱ | **平铺**所有边（详见 5.3） |
| `bundles` | Bundle[] | ◯ | 节点束：逻辑分组与对外封装（详见 5.5）；不是节点容器，仅引用 instance_id |
| `cascades` | Cascade[] | ◯ | 级联规则集合（详见 5.4） |
| `created_at` / `updated_at` | ISO8601 | ✱ | 服务端写入 |
| `published_at` | ISO8601 / null | ◯ 🔒 | 进入 `published` 时写入，永不变 |

> 对应顶层文档 `forest-structure` 的 `CascadeForest`（§3.2.1）；保存到 `t_graph_version.snapshot` JSON 列。

---

### 5.2 NodeInstance 节点实例

业务最小可执行单元，绑定一个命令模板的**冻结快照**。

```json
{
  "instance_id": "node_stock",
  "name": "扣减库存",
  "command_template_id": "cmd_stock_deduct",
  "command_template_version": 5,
  "command_template_snapshot": { "/* 冻结时拷贝的完整命令模板内容 */": "..." },
  "params": {
    "warehouse": "WH01",
    "strict_mode": true,
    "retry_times": 3
  },
  "io_binding": {
    "inputs": [
      {"port": "sku", "source": "node_create_order.outputs.sku"},
      {"port": "qty", "source": "node_create_order.outputs.amount"}
    ],
    "outputs": [
      {"port": "stock_after", "expose_as": "stock_after"}
    ]
  },
  "bundle_id": null,
  "position": {"x": 320, "y": 180},
  "status": "bound",
  "annotations": {"comment": "促销期 strict=true"}
}
```

| 字段 | 类型 | 必填 | 业务含义 / 约束 |
|---|---|---|---|
| `instance_id` | string | ✱ 🔒 | 前缀 `node_`，森林内唯一 |
| `name` | string ≤64 | ✱ | 画布显示用，森林内唯一 |
| `command_template_id` | string | ✱ | P1 命令模板 id |
| `command_template_version` | int | ✱ 🔒 | **必须显式指定版本，不允许 latest**（§4 规则 2） |
| `command_template_snapshot` | object | ✱ 🔒 | 保存时由 `freeze_template_snapshots` 写入；后续命令模板升级不影响本实例 |
| `params` | object | ✱ | 形状由 `command_template_snapshot.input_schema` 决定 |
| `io_binding.inputs[].port` | string | ✱ | 命令模板输入端口名 |
| `io_binding.inputs[].source` | string | ◯ | 上游产出引用 `<instance_id>.outputs.<port>`；空 = 运行时填 |
| `io_binding.outputs[].port` | string | ✱ | 命令模板输出端口名 |
| `io_binding.outputs[].expose_as` | string | ◯ | 暴露给下游的别名 |
| `bundle_id` | string / null | ◯ | 节点所属 Bundle，可空（不在任何 Bundle 内） |
| `position.x` / `position.y` | float | ✱ | 画布坐标，单位像素 |
| `status` | enum | ✱ | `configuring` / `bound` / `locked` |
| `annotations` | object | ◯ | 注释、审核备注等 |

---

### 5.3 Edge 边

节点之间的**依赖与触发**关系。三种类型决定颜色与执行语义。

```json
{
  "edge_id": "edge_2",
  "from": {"instance_id": "node_stock",   "port": "stock_after"},
  "to":   {"instance_id": "node_notify",  "port": "trigger_in"},
  "type": "cond",
  "condition_expr": "stock_after >= 0",
  "label": "库存充足时通知"
}
```

| 字段 | 类型 | 必填 | 业务含义 / 约束 |
|---|---|---|---|
| `edge_id` | string | ✱ 🔒 | 前缀 `edge_` |
| `from.instance_id` / `to.instance_id` | string | ✱ | 不允许自环 (`from == to`)；必须命中 `forest.node_instances` 内 |
| `from.port` / `to.port` | string | data / cond 必填 | 必须命中对应节点 `command_template_snapshot` 的 IO 端口名 |
| `type` | enum | ✱ | `seq` 顺序边（黑）/ `data` 数据流（蓝）/ `cond` 条件边（紫） |
| `condition_expr` | string DSL | cond 必填 | 表达式语言：变量来自上游 outputs；沙箱内执行（顶层文档 §10.10） |
| `label` | string ≤32 | ◯ | 画布上显示在边中段 |

---

### 5.4 Cascade 级联

上游节点一变，下游节点自动联动的规则。**跨节点的"业务连锁"声明**。

```json
{
  "cascade_id": "csd_01",
  "name": "库存变化连锁",
  "trigger": {
    "instance_id": "node_stock",
    "event": "params_changed",
    "fields": ["warehouse"]
  },
  "actions": [
    {"instance_id": "node_notify", "strategy": "recompute"},
    {"instance_id": "node_audit",  "strategy": "invalidate"}
  ],
  "scope": "forest",
  "enabled": true,
  "priority": 100
}
```

| 字段 | 类型 | 必填 | 业务含义 / 约束 |
|---|---|---|---|
| `cascade_id` | string | ✱ 🔒 | 前缀 `csd_` |
| `trigger.instance_id` | string | ✱ | 触发源节点 |
| `trigger.event` | enum | ✱ | `params_changed` / `command_version_changed` / `inputs_changed` |
| `trigger.fields` | string[] | ◯ | 仅监听特定字段，缺省=任意字段变化 |
| `actions[].instance_id` | string | ✱ | 受影响节点 |
| `actions[].strategy` | enum | ✱ | `recompute` 重算 / `invalidate` 标脏 / `notify` 仅通知 |
| `scope` | string | ✱ | `forest` 全森林 / `bundle:<bundle_id>` / `dag:<root_instance_id>` |
| `priority` | int | ◯ | 多个 cascade 触发同一节点时的执行序 |

---

### 5.5 Bundle 节点束

把一组节点打包成可复用、可对外暴露端口的"子流程"。

```json
{
  "bundle_id": "bdl_pay_v1",
  "name": "支付子流程",
  "version": 1,
  "owner_id": "u_001",
  "is_public": false,
  "contained_instance_ids": ["node_pay_init", "node_pay_call", "node_pay_check"],
  "internal_edge_ids": ["edge_p1", "edge_p2"],
  "exposed_inputs": [
    {"port_name": "amount", "internal": "node_pay_init.params.amount", "type": "decimal"}
  ],
  "exposed_outputs": [
    {"port_name": "pay_status", "internal": "node_pay_check.outputs.status", "type": "string"}
  ],
  "tags": ["payment"]
}
```

| 字段 | 类型 | 必填 | 业务含义 / 约束 |
|---|---|---|---|
| `bundle_id` | string | ✱ 🔒 | 前缀 `bdl_` |
| `version` | int | ✱ | 同 name 多版本，引用方锁版本号 |
| `is_public` | bool | ✱ | 是否进 Bundle 库供他人复用 |
| `contained_instance_ids` | string[] | ✱ | 内部节点 instance_id；与 NodeInstance.bundle_id 双向一致 |
| `internal_edge_ids` | string[] | ✱ | Bundle 内部边集合；用于校验封闭性 |
| `exposed_inputs[].internal` | string | ✱ | 内部节点的具体引用路径 |
| `exposed_outputs[].internal` | string | ✱ | 同上；外部边只能连到 exposed 端口（§4 规则 4） |

> **Bundle 不是节点容器**——节点实际存储在 `forest.node_instances` 平铺数组中，Bundle 只持有它们的 `instance_id`。

---

### 5.6 DagView 视图（**派生数据**，不持久化）

> DagView 是后端用 `dag-compute`（顶层文档 §3.2.3）从 `CascadeForest` 实时计算出的视图，
> 给模拟器、影响面分析、Phase1 输入、代码生成顺序使用。
>
> **一个森林 → 多个 DagView**：每个连通子图（每个 root，即 `in_degree=0` 节点）对应一个 view。

```json
{
  "forest_id": "fst_01HXABC123",
  "forest_version": 3,
  "computed_at": "2026-05-08T14:31:00Z",
  "views": [
    {
      "dag_index": 0,
      "root": "node_create_order",
      "node_ids": ["node_create_order", "node_stock", "node_notify"],
      "edge_ids": ["edge_1", "edge_2"],
      "topo_order": ["node_create_order", "node_stock", "node_notify"],
      "spans_bundles": [],
      "depth": 3,
      "in_degree": {"node_create_order": 0, "node_stock": 1, "node_notify": 1},
      "fanout_stats": {"max": 1, "avg": 0.67}
    }
  ],
  "cycle_check": {"passed": true, "cycles": []},
  "isolated_node_ids": []
}
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `views[]` | DagView[] | 每个连通子图一项，按 root 切分 |
| `views[].root` | string | 该 DAG 的根节点 instance_id（in_degree=0） |
| `views[].node_ids` / `edge_ids` | string[] | 该 DAG 包含的节点与边 |
| `views[].topo_order` | string[] | 预计算拓扑序；模拟器与代码生成按此走 |
| `views[].spans_bundles` | string[] | 该 DAG 跨越的 Bundle 集合 |
| `views[].depth` | int | 最长路径长度 |
| `views[].in_degree` | map<id, int> | 该 DAG 内部节点入度表 |
| `views[].fanout_stats` | object | 给画布做布局参考 |
| `cycle_check.passed` | bool | 必为 true 才允许保存（§4 规则 1） |
| `cycle_check.cycles` | string[][] | 出环时给出环路用于前端高亮 |
| `isolated_node_ids` | string[] | 入度+出度=0 的孤儿节点（前端给警告） |

> 计算结果可按 `(forest_id, version, snapshot_hash)` 缓存到 Redis；任一节点 / 边 / Bundle 编辑后失效。

---

### 5.7 SimulatorRun 模拟器运行

一次模拟器跑动的过程对象。运行结束后转为只读。

```json
{
  "id": "sim_01HXSIM",
  "forest_id": "fst_01HXABC123",
  "forest_version": 3,
  "dag_index": 0,
  "started_by": "u_001",
  "started_at": "2026-05-08T14:32:00Z",
  "ended_at": null,
  "status": "running",
  "entry_instance_id": "node_create_order",
  "breakpoints": ["node_notify"],
  "current_step": 2,
  "trace": [
    {
      "step": 1,
      "instance_id": "node_create_order",
      "ts": "2026-05-08T14:32:01Z",
      "inputs": {},
      "outputs": {"order_id": "ord_001", "amount": 100, "sku": "S01"},
      "duration_ms": 12,
      "status": "ok"
    },
    {
      "step": 2,
      "instance_id": "node_stock",
      "ts": "2026-05-08T14:32:02Z",
      "inputs": {"sku": "S01", "qty": 100},
      "outputs": {"stock_after": 50},
      "duration_ms": 18,
      "status": "ok"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 业务含义 / 约束 |
|---|---|---|---|
| `forest_version` | int | ✱ 🔒 | 锁定运行时的森林版本，森林后续修改不影响此 run |
| `dag_index` | int | ✱ 🔒 | 选定要跑的 DagView 索引（一个森林可能有多 DAG） |
| `status` | enum | ✱ | `pending` / `running` / `paused` / `done` / `aborted` |
| `entry_instance_id` | string | ✱ | 模拟入口（默认 = `views[dag_index].root`，可由用户改写） |
| `breakpoints` | string[] | ◯ | 命中即暂停 |
| `current_step` | int | ✱ | 已完成步数 |
| `trace[]` | object[] | ✱ | 每节点一项，单步执行的输入输出快照与耗时；轨迹长度 ≤ §7 上限 |
| `trace[].instance_id` | string | ✱ | 当前步对应节点 |
| `trace[].status` | enum | ✱ | `ok` / `skipped` / `error` |

---

### 5.8 各对象之间的引用关系（汇总）

```
CascadeForest（聚合根，扁平容器）
   │
   ├── node_instances[]   (NodeInstance)
   │       └── 引用 CommandTemplate(id + version + snapshot)   [跨 BC，只读快照]
   │
   ├── edges[]            (Edge)
   │       └── 连接 NodeInstance × NodeInstance（只持 instance_id）
   │
   ├── bundles[]          (Bundle)
   │       └── 引用 instance_id 与 edge_id（不持节点对象）
   │
   └── cascades[]         (Cascade)
           └── 引用 instance_id

派生（不持久化，按需重算）：
   DagView[]   ←──   dag-compute(forest)        # 一森林 N DagView，按 root 切分

固化（独立持久化）：
   SimulatorRun   ──→   Forest@version + dag_index + trace
```

跨 BC 的引用统统**只持 id + 版本号**，绝不持对象（详见 `agent.md` §3）。

---

## 6. 状态机

```
CascadeForest:  草稿 ──发布──→ 已发布 ──归档──→ 归档
                    ↑                  │
                    └──── 复制为新草稿 ┘

NodeInstance:   配置中 ──绑模板快照──→ 已绑定 ──森林发布──→ 已锁定
                    ↑                       │
                    └────── 解绑 ───────────┘

SimulatorRun:   待启动 ──→ 运行中 ──→ 暂停 / 完成 / 中断
```

> 顶层文档 §3.2.2 的 GraphVersion 状态（DRAFT / SAVED / PHASE1_PASSED / FULLY_VALIDATED / ARCHIVED）是 `CascadeForest` 落库后由 review/execution 域驱动的二级状态，本 BC 仅负责前三个状态。

---

## 7. 性能 / 容量假设

| 维度 | 上限 |
|---|---|
| 单森林节点数 | ≤ 500 |
| 单森林边数 | ≤ 2000 |
| 单森林同时在线编辑者 | ≤ 10 |
| 模拟器单次轨迹长度 | ≤ 10000 步 |
| 画布交互响应 | 单操作 ≤ 200ms |

---

## 8. 非目标（Non-goals，不在本 BC 范围）

- ❌ 真实代码执行（这是 Execution + Phase3 的事）
- ❌ 调 LLM 推理（这是 Phase1/2 的事）
- ❌ 命令模板的创建与维护（这是 P1 的事）
- ❌ 版本回滚到任意历史（先靠"复制为新草稿"代替）
- ❌ 节点参数的强 schema 校验（依赖 P1 命令模板提供的 schema）

---

## 9. 关键 UX 决策（与原型对齐）

- 画布主区采用**无限平移 + 缩放**，左侧抽屉是命令模板库，右侧抽屉是当前节点参数面板
- 节点形状统一矩形，边类型靠颜色区分（黑=顺序，蓝=数据，紫=条件）
- 模拟器以**右侧底部时间线**呈现，单步播放器形态
- 详见 `prototype.html`

---

## 10. 待澄清 / 风险

| # | 议题 | 影响 | 待谁拍板 |
|---|---|---|---|
| Q1 | 跨 Bundle 的边是否需要 Bundle owner 审批 | 影响协同流程 | 业务方 |
| Q2 | Bundle 是否允许嵌套 Bundle（节点同时归属多 Bundle） | 影响数据结构与 UI | 架构 |
| Q3 | 模拟器轨迹是否持久化 | 影响 DB schema | 业务方 + DBA |
| Q4 | DagView 派生结果是否对前端长期缓存（vs 每次重算） | 影响响应时延 | 架构 |

---

## 附：评审签字栏

| 角色 | 姓名 | 签字 | 日期 |
|---|---|---|---|
| 产品 | | | |
| 业务方 | | | |
| 架构师 | | | |
| P2 owner | | | |
