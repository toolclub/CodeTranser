# Cascade · K8S 部署 manifests

最小可用骨架。生产请按需替换托管 DB / Redis 服务、加 SealedSecret、配 Network Policy。

## 一次性部署

```bash
# 1. 命名空间
kubectl apply -f 00-namespace.yaml

# 2. Secret(从 example 改完后部署;生产请用 SealedSecret/Vault)
cp 10-secrets.yaml.example 10-secrets.yaml
$EDITOR 10-secrets.yaml
kubectl apply -f 10-secrets.yaml

# 3. ConfigMap
kubectl apply -f 20-configmap.yaml

# 4. 数据层(生产建议改用托管 RDS/MongoAtlas/ElastiCache)
kubectl apply -f 30-mysql.yaml -f 31-mongo.yaml -f 32-redis.yaml

# 5. 等数据层 ready
kubectl -n cascade wait --for=condition=ready pod -l app=cascade-mysql --timeout=300s
kubectl -n cascade wait --for=condition=ready pod -l app=cascade-mongo --timeout=120s
kubectl -n cascade wait --for=condition=ready pod -l app=cascade-redis --timeout=60s

# 6. 后端(包含一次性 migrate Job)
kubectl apply -f 40-backend.yaml

# 7. 前端 + Ingress
kubectl apply -f 50-frontend.yaml
```

## 升级(rolling update)

```bash
# CI 出新镜像 cascade-backend:<sha>
kubectl -n cascade set image deploy/cascade-backend backend=cascade-backend:<sha>
kubectl -n cascade rollout status deploy/cascade-backend
```

`Deployment.strategy.rollingUpdate` 设了 `maxSurge=1, maxUnavailable=0`,新 pod 起来才下旧 pod;`terminationGracePeriodSeconds=60` 给老 Run 跑完时间。

## 分布式行为校验(部署完跑一遍)

```bash
# 1. 运维查 Run 在哪个 pod
kubectl -n cascade exec deploy/cascade-mysql -- mysql -uroot -p"$PWD" -e \
  "SELECT id, worker_id, heartbeat_at FROM cascade.t_workflow_run WHERE status='running'"

# 2. 任意 pod 触发 stop(由 LB 随机路由),实际跑 Run 的 pod 最多 20s 内 cancel
curl -X POST https://cascade.example.com/api/runs/r_xxx/stop

# 3. 前端断线重连补齐事件
curl https://cascade.example.com/api/runs/r_xxx/events?after_id=42
```

## 必看的 ConfigMap 字段

| key | 必须 |
|---|---|
| `CHECKPOINTER_KIND=redis` | ★ 不设就是 MemorySaver,pod 重启 Run state 全丢 |
| `AUTH_ENABLED=true` | 别上线时还是 false |
| `RATE_LIMIT_ENABLED=true` | 同上 |
| `CORS_ORIGINS` | 改成你的实际前端域名 |

## CHECKPOINTER_KIND=redis 的额外依赖

后端镜像构建时需追加:

```dockerfile
RUN pip install langgraph-checkpoint-redis
```

或在 `pyproject.toml` 把 `langgraph-checkpoint-redis` 加到 dependencies。
