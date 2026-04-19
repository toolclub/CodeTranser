#!/usr/bin/env bash
# 启动 Cascade(单机 docker compose)
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "[init] 复制 .env.example → .env;请先填 LLM_API_KEY 再重跑"
  cp .env.example .env
  exit 1
fi

# 沙箱镜像探测;默认用 fullstack-dev:latest(已内置 sshd + /sandbox + root:sandbox123)
# 想换镜像名?.env 里设 SANDBOX_IMAGE=xxx
SANDBOX_IMG="${SANDBOX_IMAGE:-fullstack-dev:latest}"
SANDBOX_FLAG=()
if docker image inspect "$SANDBOX_IMG" > /dev/null 2>&1; then
  echo "[sandbox] $SANDBOX_IMG present, will enable sandbox profile"
  SANDBOX_FLAG=(--profile sandbox)
else
  echo "[sandbox] $SANDBOX_IMG 未找到,本次启动跳过沙箱"
  echo "          Phase3 沙箱功能将不可用。要启用(一次性 15-30 min):"
  echo "            cd sandbox"
  echo "            docker build -t fullstack-dev:latest -f Dockerfile.base ."
  echo "            docker compose --profile sandbox up -d"
fi

echo "[up] docker compose ${SANDBOX_FLAG[*]} up -d --build ..."
docker compose "${SANDBOX_FLAG[@]}" up -d --build

echo
echo "[wait] 等 backend 健康(首次 2-3 分钟)..."
for _ in $(seq 1 120); do
  status=$(docker inspect -f '{{.State.Health.Status}}' cascade-backend 2>/dev/null || echo unknown)
  if [[ "$status" == "healthy" ]]; then
    echo "  ✓ backend healthy"
    break
  fi
  sleep 3
done

echo
echo "[done] 全部就绪:"
echo "  前端:    http://localhost:${FRONTEND_PORT:-8080}"
echo "  后端:    http://localhost:${BACKEND_PORT:-8000}/healthz"
echo "  改代码:  docker compose up -d --build backend  (or frontend)"
echo "  日志:    ./scripts/logs.sh"
echo "  停:      ./scripts/down.sh"
