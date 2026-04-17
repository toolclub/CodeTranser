# 级跳设计平台 · 前端高保真原型

## 如何查看

直接用浏览器打开 `index.html` 即可。页面导航从入口进。

- 画布编辑器页 (`pages/canvas-editor.html`) 通过 unpkg CDN 加载 antv X6,可以拖拽、连线、缩放,第一次加载需要联网。
- 其他页面是纯静态 HTML/CSS/SVG,离线可看。

## 页面清单

| 文件 | 对应后端 API |
| --- | --- |
| `index.html` | — (导航) |
| `pages/graph-list.html` | `GET /api/graphs` |
| `pages/canvas-editor.html` | `PUT /api/graphs/:id/draft`, `POST /api/graphs/:id/versions` |
| `pages/template-library.html` | `GET /api/node-templates` (前端简投影 NodeTemplateCardDTO) |
| `pages/template-editor.html` | `POST /api/node-templates` 或 `POST /api/admin/node-templates` |
| `pages/scenarios.html` | `POST /api/runs { scenarios, variant }` |
| `pages/run-list.html` | `GET /api/runs` + WS |
| `pages/run-detail.html` | `GET /api/runs/:id` + WS |
| `pages/code-diff.html` | `GET /api/runs/:id/code-snapshot/diff` |
| `pages/review.html` | `GET/POST /api/reviews/:id` |
| `pages/no-permission.html` | 统一 403 / 401 / 500 兜底 |

## 鉴权约定

前端不做权限判断。后端所有需要鉴权的接口都由 `@require_admin` / `@require_user` 装饰器把关,前端只需要:
1. 收到 `401` 跳登录。
2. 收到 `403` 跳 `no-permission.html`,展示 `code / message / trace_id`。
