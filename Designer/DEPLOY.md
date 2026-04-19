# 级跳设计平台 · 启动 / 部署指南

只有 **2 套部署形态**:

| 场景 | 怎么起 |
|---|---|
| **本地单机**(开发 + 自测) | Windows: `start.bat` ⋅ Linux/macOS: `./scripts/up.sh` |
| **生产 K8S**(分布式) | `kubectl apply -f deploy/k8s/`(详见 `deploy/k8s/README.md`) |

本地单机 = 一个 `docker-compose.yml`,起 6 个容器:`mysql / mongo / redis / sandbox / backend / frontend`。**不分 dev / prod**——改代码就 rebuild 该服务。

---

## 1. 本地单机

### 1.1 一次性

**Windows**:
```cmd
start.bat
```

第一次会自动 `copy .env.example .env` + 弹 notepad。改完 `LLM_API_KEY` 保存,再跑一次 `start.bat`。

**Linux/macOS**:
```bash
cp .env.example .env       # 改 LLM_API_KEY
./scripts/up.sh
```

启动后:

- **前端**(nginx 静态 + 反代):http://localhost:8080
- **后端**(uvicorn):http://localhost:8000/healthz · http://localhost:8000/docs
- **MySQL**:127.0.0.1:3306(`cascade / cascade-dev`)
- **MongoDB**:127.0.0.1:27017
- **Redis**:127.0.0.1:6379
- **沙箱 SSH**:`ssh root@127.0.0.1 -p 2222`(密码 `sandbox123`)

数据存 `./.data/{mysql,mongo,redis}/`(已 gitignore)。

### 1.2 沙箱(默认用 `fullstack-dev:latest`)

`docker-compose.yml` 里:

```yaml
sandbox:
  image: ${SANDBOX_IMAGE:-fullstack-dev:latest}   # 默认就是 fullstack-dev
  pull_policy: never                               # 只用本地
  container_name: cascade-sandbox                  # 容器名独立
```

`fullstack-dev:latest` 自己就是完整沙箱 —— Dockerfile.base 里已经装好 `openssh-server`、创建 `/sandbox`、配好 `PermitRootLogin yes`、设好 `root:sandbox123`。上层的 chatflow-sandbox 只是重复一遍,不需要。

**最常见**:本地已经有这个镜像(ChatFlow 或别的项目 build 过) → `start.bat` 直接用上。

**新机器**:`sandbox/Dockerfile.base` 是备份,build 一次就好:

```cmd
cd sandbox
docker build -t fullstack-dev:latest -f Dockerfile.base .   :: 15-30 min
```

想换镜像名? `.env` 里写 `SANDBOX_IMAGE=xxx` 就行,compose 自动走这个 tag。

**集群模式**(3 worker):

```cmd
docker compose --profile sandbox-cluster up -d
```

启动 `cascade-sandbox / cascade-sandbox-w2 / cascade-sandbox-w3`(端口 2222 / 2223 / 2224)。`.env` 里 `SANDBOX_WORKERS` 同步改成 3 个。

**不需要沙箱?** `.env` 里 `SANDBOX_WORKERS=[]` + `docker compose up -d --scale sandbox=0`。

### 1.3 改代码后

| 改了什么 | 怎么生效 |
|---|---|
| `backend/app/*.py` | `docker compose up -d --build backend` |
| `frontend/src/*.{ts,vue}` | `docker compose up -d --build frontend` |
| `pyproject.toml` 加依赖 | 同 backend rebuild |
| `package.json` 加依赖 | 同 frontend rebuild |
| DDL 迁移(新 `config/sql/NN.ddl`) | 重启 backend 自动跑(`backend` 启动命令是 `migrate && uvicorn`) |
| `.env` 变更 | `docker compose up -d`(不需要 build) |

### 1.4 日常常用

| 操作 | Windows | Linux/macOS |
|---|---|---|
| 起 | `start.bat` | `./scripts/up.sh` |
| 停(留数据) | `stop.bat` | `./scripts/down.sh` |
| 看 backend 日志 | `logs.bat` | `./scripts/logs.sh` |
| 看其他服务日志 | `logs.bat sandbox` / `frontend` / `mysql` | 同左,`./scripts/logs.sh sandbox` |
| 跑后端测试 | `test.bat` | `./scripts/test.sh` |
| 进 backend shell | `shell.bat` | `./scripts/shell.sh` |
| 进 mysql | `docker compose exec mysql mysql -ucascade -pcascade-dev cascade` | 同 |
| 进 mongo | `docker compose exec mongo mongosh cascade` | 同 |
| 进 redis | `docker compose exec redis redis-cli` | 同 |
| 重新 migrate | `docker compose exec backend python -m app.cli migrate` | 同 |
| 彻底清空 | `rmdir /s /q .data .logs` | `rm -rf .data .logs` |

---

## 2. 生产 K8S

详见 [`deploy/k8s/README.md`](./deploy/k8s/README.md)。要点:

- **后端 3 副本起步,HPA 到 10**;`HOSTNAME` 通过 K8S Downward API 注入 → 自动作为 `worker_id`
- **数据层**:示例用 StatefulSet + PVC;生产建议换托管 RDS / MongoDB Atlas / ElastiCache
- **沙箱**:也用 StatefulSet(SSH 需要稳定 hostname),Cascade backend 通过 K8S Service DNS(`SANDBOX_WORKERS=[{...host:cascade-sandbox.cascade.svc...}]`)
- **必须**在 ConfigMap 设 `CHECKPOINTER_KIND=redis`,否则 pod 重启 Run state 全丢
- **Migration**:Job 每次 deploy 跑一次,幂等(`t_migration_applied` checksum 守护)
- 配 SealedSecret / ExternalSecret 替代明文 Secret
- Ingress 注解关 SSE buffering、开 WS upgrade、长 timeout

---

## 3. 启动诊断

| 症状 | 诊断 |
|---|---|
| `start.bat` 卡在 backend 不健康 | `logs.bat` 看 migrate / uvicorn 报什么;通常是 MySQL 还没 ready,等 1-2 min |
| `chatflow-sandbox:latest not found` | 看 § 1.2;ChatFlow 那边 build 过就有,新机器手 build |
| `DependencyError: LLM_UNAVAILABLE` | `.env` 里 `LLM_API_KEY` 没设 / 错 |
| `ModuleNotFoundError: langgraph_checkpoint_redis` | 仅当 `CHECKPOINTER_KIND=redis` 才需要;`pip install` 后 rebuild backend |
| 端口冲突 | 改 `.env` 里 `BACKEND_PORT / FRONTEND_PORT / MYSQL_PORT / SANDBOX_SSH_PORT` |
| Run 卡 status=running 不动 | `docker compose exec mysql mysql -ucascade -pcascade-dev cascade -e "SELECT id, worker_id, heartbeat_at FROM t_workflow_run WHERE status='running'"`;>60s 没心跳 → `POST /api/runs/<id>/stop` |

---

## 4. 文件总览

```
Designer/
├── ARCHITECTURE.md              架构 + 代码解读 + 节点扩展 SOP
├── DEPLOY.md                    本文
├── docker-compose.yml           ★ 唯一一份(单机部署,改代码 rebuild)
├── .env.example                 配置模板
├── start.bat / stop.bat         ★ Windows 一键启停
├── logs.bat / test.bat / shell.bat   Windows 工具
├── scripts/
│   └── up.sh / down.sh / logs.sh / test.sh / shell.sh   Linux/macOS
├── deploy/k8s/                  ★ 生产 K8S manifests + README
├── sandbox/                     ChatFlow 沙箱 Dockerfile 备份(本地无镜像时手 build)
├── backend/
│   ├── Dockerfile               多阶段 build
│   ├── pyproject.toml
│   ├── app/                     业务代码
│   ├── config/sql/              DDL
│   └── tests/                   153 单测
├── frontend/
│   ├── Dockerfile               多阶段(node build → nginx serve)
│   ├── nginx.conf               SSE/WS 友好的反代
│   └── src/                     Vue 3 + Pinia + X6
├── impl-docs/                   设计文档 00-07
└── impl-docs-frontend/          前端高保真原型
```
