# ── Stage 1: Build ────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# 优先复制依赖描述,利用 Docker 层缓存
COPY package*.json ./
RUN npm ci --prefer-offline --no-audit --no-fund

COPY . .
# 跳过 vue-tsc(已在 CI 跑过),容器构建只做 vite build
RUN npx vite build

# ── Stage 2: Nginx serve ──────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
