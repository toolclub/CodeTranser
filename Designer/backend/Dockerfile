# ── Stage 1: Build wheel(优化镜像层缓存)─────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 仅复制依赖描述,优先利用 Docker 缓存层
COPY pyproject.toml ./

RUN pip install --upgrade pip \
    && pip wheel --wheel-dir=/wheels .

# ── Stage 2: 运行镜像 ────────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=prod

WORKDIR /app

# 安装 curl 给 healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 装 wheel(包含 pyproject 解出的依赖)
COPY --from=builder /wheels /wheels
COPY pyproject.toml ./
RUN pip install --no-index --find-links=/wheels cascade-backend \
    && rm -rf /wheels

# 应用代码
COPY app ./app
COPY config ./config

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fs http://localhost:8000/healthz || exit 1

# 默认 1 worker;K8S 多副本水平扩,单 pod 单 worker 更易观测
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
