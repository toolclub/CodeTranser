# 沙箱

**Cascade 直接复用 ChatFlow 的 `chatflow-sandbox:latest` 镜像。**容器名独立(`cascade-sandbox`),不和 ChatFlow 的容器冲突。

本目录的 `Dockerfile` 和 `Dockerfile.base` 是从 ChatFlow `llm-chat/sandbox/` 复制过来的**备份**——本地没有镜像时可以从这里 build,build 出来的镜像和 ChatFlow build 的等价。

## 镜像清单

| 镜像 | 来源 | Cascade 是否需要 build |
|---|---|---|
| `fullstack-dev:latest` | `Dockerfile.base`(Ubuntu 24.04 + Python/Java/Node/Rust) | 本地有就不用 |
| `chatflow-sandbox:latest` | `Dockerfile`(基于上面的 base + SSH server) | 本地有就不用 |

## 检查本地是否已有镜像

```cmd
docker image inspect chatflow-sandbox:latest
docker image inspect fullstack-dev:latest
```

返回 JSON 即存在;`No such image` 即缺。

## 如果缺镜像怎么办

**最常见:已经在 ChatFlow 项目里 build 过**——什么都不用做,Cascade 直接 `docker compose up` 就用上。

**新机器,完全没 build 过**:

```cmd
:: Linux/macOS/Windows 一样
cd sandbox
:: 1) 先 build base(15-30 分钟)
docker build -t fullstack-dev:latest -f Dockerfile.base .
:: 2) 再 build sandbox(1 分钟)
docker build -t chatflow-sandbox:latest .
```

之后 `docker compose up` 自动起 `cascade-sandbox` 容器(image 引用 `chatflow-sandbox:latest`)。

## docker compose 行为

`docker-compose.yml` 里:

```yaml
sandbox:
  image: chatflow-sandbox:latest    # 引用,不 build
  pull_policy: never                # 不去 registry 拉,只用本地
  container_name: cascade-sandbox   # 容器名独立
```

镜像没找到 → docker compose 启动报 `image not found`。这时按上面"缺镜像怎么办"操作。

## 单独跑一个沙箱(不起 Cascade 主栈)

```bash
docker run -d --name cascade-sandbox -p 2222:22 chatflow-sandbox:latest
ssh root@127.0.0.1 -p 2222   # 密码 sandbox123
```

## Cascade 后端怎么连

`.env`:

```env
SANDBOX_WORKERS=[{"id":"w1","host":"sandbox","port":22,"user":"root","password":"sandbox123"}]
```

容器内 backend 通过 docker network service 名 `sandbox:22` SSH 直连。K8S 部署只需把 `host` 改成 K8S Service DNS。

## 集群模式

```bash
docker compose --profile sandbox-cluster up -d
```

启动 `cascade-sandbox / cascade-sandbox-w2 / cascade-sandbox-w3`,端口 2222 / 2223 / 2224。`.env` 改成:

```env
SANDBOX_WORKERS=[{"id":"w1","host":"sandbox","port":22,"user":"root","password":"sandbox123"},{"id":"w2","host":"sandbox-w2","port":22,"user":"root","password":"sandbox123"},{"id":"w3","host":"sandbox-w3","port":22,"user":"root","password":"sandbox123"}]
```

`SandboxManager` 自动健康检查 + run_id 亲和。

## 安全

- root 密码默认 `sandbox123`,**仅内网/dev 用**
- 生产 K8S:SSH key + Secret 注入,改 `Dockerfile`(去掉 password 行,挂 key 到 `/root/.ssh/authorized_keys`)
- `Dockerfile` 有 `ARG SANDBOX_ROOT_PASSWORD`:`docker build --build-arg SANDBOX_ROOT_PASSWORD=xxx ...`
