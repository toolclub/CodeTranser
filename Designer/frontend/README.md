# Cascade Frontend

Vue 3 + TypeScript + Vite + Pinia + Vue Router + antv X6。骨架阶段,11 个页面均为路由占位,接入后端 API 后按 `../impl-docs-frontend/` 原型逐页实装。

## 快速开始

```bash
cd frontend
npm install
npm run dev
# → http://127.0.0.1:5173
# /api 已代理至 http://127.0.0.1:8000,/ws 同理
```

## 结构

```
src/
├── main.ts
├── App.vue              顶部布局 + 侧边导航
├── router/              11 路由
├── stores/              Pinia
├── api/client.ts        axios 封装 · 401/403 跳 /no-permission
├── pages/               与 impl-docs-frontend 原型一一对应
├── styles/main.css
└── types/
```

## 约定

- 前端不做鉴权;后端 `@require_admin / @require_user` 装饰器负责。
- 画布使用 `@antv/x6`(不用 VueFlow,参见 memory.md §10)。
- 所有 REST 经 `@/api/client.ts`,便于统一拦截。
