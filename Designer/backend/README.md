# Cascade Backend (v1)

级跳设计平台后端骨架。完整实现按 `../impl-docs/` 01–12 章节迭代,本仓库目前只含 00/02 章的最小骨架(FastAPI 入口 + 日志 + trace_id + 健康检查)。

## 快速开始

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
# → http://127.0.0.1:8000/healthz
```

## 目录速览

- `app/main.py` — FastAPI 入口
- `app/config.py` — Settings(pydantic-settings)
- `app/bootstrap.py` — DI 组合根(AppContainer)
- `app/infra/` — 日志 / trace_id / (后续:db/mongo/redis)
- `app/middlewares/` — trace_id / 错误处理
- `app/api/` — 路由(仅 healthz,按 10 章扩展)
- `app/domain/` `app/schemas/` `app/repositories/` `app/services/` — 按 01+ 章填充
- `app/tool_runtime/` `app/llm/` `app/langgraph/` — 按 03/05/06 章填充
- `config/sql/NN.ddl` — DDL 迁移(按 01 章写入)
- `tests/` — 单测

## 测试

```bash
pytest
```

## 后续章节

- 01:`config/sql/01.ddl` + models/mysql + schemas + domain 值对象
- 02:DB/Mongo/Redis 客户端 + 迁移 runner
- 03–07:Tool 子系统 / 图森林 / LLM / LangGraph / Phase1
