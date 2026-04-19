#!/usr/bin/env bash
# 停所有容器(数据保留)
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose down
echo "[down] 容器已停;数据保留在 .data/(下次启动自动 mount)"
echo "彻底清空:rm -rf .data .logs"
