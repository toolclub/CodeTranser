from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import Settings
from app.infra.db.session import create_engine, create_session_factory
from app.infra.logging import configure_logging, get_logger
from app.settings_service import SettingsService

log = get_logger(__name__)


@dataclass(slots=True)
class AppContainer:
    """应用组合根。唯一 new XxxImpl 的地方。"""

    settings: Settings
    db_engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    mongo_client: Any = None
    mongo_db: Any = None
    redis: Any = None
    settings_service: SettingsService | None = None

    # Ch03 节点模板子系统
    tool_registry: Any = None
    tool_loader: Any = None
    meta_template_service: Any = None
    tool_service_factory: Callable[[AsyncSession], Any] | None = None

    # Ch04 图森林子系统
    forest_parser: Any = None
    design_validator: Any = None
    graph_service_factory: Callable[[AsyncSession], Any] | None = None

    # 后续章节
    llm_client: Any = None
    sandbox_facade: Any = None
    event_bus: Any = None
    event_log_store: Any = None
    trace_sink: Any = None
    pipeline: Any = None
    workflow_facade: Any = None

    # K8S 分布式协调
    checkpointer: Any = None
    stop_registry: Any = None
    session_registry: Any = None
    worker_id: str = ""

    # 沙箱(复用 ChatFlow 镜像)
    sandbox_manager: Any = None
    sandbox_client: Any = None

    extras: dict[str, Any] = field(default_factory=dict)


def build_container(settings: Settings) -> AppContainer:
    configure_logging(settings)
    engine = create_engine(settings)
    sf = create_session_factory(engine)

    mongo_client = None
    mongo_db = None
    if settings.MONGO_ENABLED:
        try:
            from app.infra.mongo.client import create_mongo_client, get_mongo_db

            mongo_client = create_mongo_client(settings)
            mongo_db = get_mongo_db(mongo_client, settings)
        except Exception as e:
            log.warning("mongo_disabled", error=str(e))

    redis_client = None
    if settings.REDIS_ENABLED:
        try:
            from app.infra.redis import create_redis

            redis_client = create_redis(settings)
        except Exception as e:
            log.warning("redis_disabled", error=str(e))

    ss = SettingsService(sf, redis_client)

    # 分布式协调(K8S-first):StopRegistry / SessionRegistry / Checkpointer
    from app.infra.checkpointer import build_checkpointer
    from app.infra.run_control import SessionRegistry, StopRegistry, current_worker_id

    worker_id = settings.WORKER_ID or current_worker_id()
    stop_registry = StopRegistry(redis_client)
    session_registry = SessionRegistry(redis_client, worker_id=worker_id)
    checkpointer = build_checkpointer(settings)

    # ChatFlow-style:事件流 DB 存储 + 总线(DB-first, Redis 广播)
    from app.langgraph.events import RunEventBus
    from app.repositories.event_log_repo import SqlEventLogStore

    event_log_store = SqlEventLogStore(sf)
    event_bus = RunEventBus(redis_client, event_store=event_log_store)

    # 沙箱(复用 ChatFlow 沙箱镜像;空 list 即关闭,Phase3 不可用)
    from app.infra.sandbox import SandboxClient, SandboxManager

    sandbox_manager = SandboxManager(redis_client)
    sandbox_client = SandboxClient(sandbox_manager)

    # Ch05 LLM 客户端
    from app.llm.client import LLMClient

    try:
        llm_client: Any = LLMClient(settings)
    except Exception as e:
        log.warning("llm_client_disabled", error=str(e))
        llm_client = None

    # Ch03 装配
    from app.repositories.tool_repo import SqlToolRepo
    from app.services.meta_template_service import MetaTemplateService
    from app.services.tool_service import ToolService
    from app.tool_runtime.factory import SimulatorFactory
    from app.tool_runtime.loader import ToolLoader
    from app.tool_runtime.registry import ToolRegistry

    tool_loader = ToolLoader(sf)
    sim_factory = SimulatorFactory()
    tool_registry = ToolRegistry(tool_loader, sim_factory, redis_client)
    meta_template_service = MetaTemplateService(sf)

    container = AppContainer(
        settings=settings,
        db_engine=engine,
        session_factory=sf,
        mongo_client=mongo_client,
        mongo_db=mongo_db,
        redis=redis_client,
        settings_service=ss,
        tool_registry=tool_registry,
        tool_loader=tool_loader,
        meta_template_service=meta_template_service,
        llm_client=llm_client,
        event_bus=event_bus,
        event_log_store=event_log_store,
        checkpointer=checkpointer,
        stop_registry=stop_registry,
        session_registry=session_registry,
        worker_id=worker_id,
        sandbox_manager=sandbox_manager,
        sandbox_client=sandbox_client,
    )

    def _tool_svc(session: AsyncSession) -> ToolService:
        return ToolService(
            SqlToolRepo(session),
            tool_registry,
            container.llm_client,
            settings,
        )

    container.tool_service_factory = _tool_svc

    # Ch04 装配
    from app.repositories.graph_draft_repo import SqlGraphDraftRepo
    from app.repositories.graph_repo import SqlGraphRepo
    from app.repositories.graph_version_repo import SqlGraphVersionRepo
    from app.services.design_validator import DesignValidator
    from app.services.forest_parser import ForestParser
    from app.services.graph_service import GraphService

    forest_parser = ForestParser(tool_registry)
    design_validator = DesignValidator()
    container.forest_parser = forest_parser
    container.design_validator = design_validator

    def _graph_svc(session: AsyncSession) -> GraphService:
        return GraphService(
            graph_repo=SqlGraphRepo(session),
            gv_repo=SqlGraphVersionRepo(session),
            draft_repo=SqlGraphDraftRepo(session),
            parser=forest_parser,
            design_validator=design_validator,
        )

    container.graph_service_factory = _graph_svc

    # 分布式持久化:Run 状态与步骤必须落 DB
    from app.langgraph.run_step_store import SqlRunStepStore

    container.extras["run_step_store"] = SqlRunStepStore(sf)

    return container


def build_workflow_runtime(container: AppContainer) -> Any:
    """装配 WorkflowRuntime(Ch10 / Ch11 调用入口)。

    这里集中所有依赖的拼接,避免 router / celery worker / websocket gateway 各自重复。
    """
    from app.langgraph.pipeline import PipelineBuilder
    from app.langgraph.router import PhaseRouter
    from app.langgraph.runtime import WorkflowRuntime
    from app.langgraph.steps.factory import PipelineStepFactory, StepDeps
    from app.langgraph.trace_sink import ToolCallTraceContext, TraceSink
    from app.llm.decorators.trace import LLMTraceContext

    if container.llm_client is None:
        llm_trace_ctx = LLMTraceContext()
    else:
        llm_trace_ctx = container.llm_client.trace_ctx

    deps = StepDeps(
        event_bus=container.event_bus,
        trace_sink=TraceSink(container.mongo_db),
        tool_trace_ctx=ToolCallTraceContext(),
        llm_trace_ctx=llm_trace_ctx,
        run_step_store=container.extras["run_step_store"],
        settings=container.settings,
        llm_client=container.llm_client,
        tool_registry=container.tool_registry,
        design_validator=container.design_validator,
        forest_parser=container.forest_parser,
    )
    factory = PipelineStepFactory(deps)
    router = PhaseRouter(factory, container.settings)
    builder = PipelineBuilder(factory, router, checkpointer=container.checkpointer)
    return WorkflowRuntime(
        builder=builder,
        events=container.event_bus,
        settings=container.settings,
        session_factory=container.session_factory,
        stop_registry=container.stop_registry,
        session_registry=container.session_registry,
        worker_id=container.worker_id,
    )


async def startup(container: AppContainer) -> None:
    if container.settings_service:
        await container.settings_service.start()
    if container.tool_registry:
        await container.tool_registry.start()
    # 启动沙箱(若配置了 SANDBOX_WORKERS)
    if container.sandbox_manager and container.settings.SANDBOX_WORKERS:
        try:
            await container.sandbox_manager.init(
                container.settings.SANDBOX_WORKERS,
                timeout=float(container.settings.SANDBOX_TIMEOUT),
            )
        except Exception as e:
            log.warning("sandbox_init_failed", error=str(e))


async def shutdown(container: AppContainer) -> None:
    if container.sandbox_manager:
        try:
            await container.sandbox_manager.shutdown()
        except Exception as e:
            log.warning("sandbox_shutdown_error", error=str(e))
    if container.tool_registry:
        await container.tool_registry.stop()
    if container.settings_service:
        await container.settings_service.stop()
    try:
        await container.db_engine.dispose()
    except Exception as e:
        log.warning("db_dispose_error", error=str(e))
    if container.mongo_client is not None:
        try:
            container.mongo_client.close()
        except Exception as e:
            log.warning("mongo_close_error", error=str(e))
    if container.redis is not None:
        try:
            await container.redis.aclose()
        except Exception as e:
            log.warning("redis_close_error", error=str(e))
