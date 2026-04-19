from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_ENV: str = "dev"
    APP_NAME: str = "cascade-backend"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "mysql+asyncmy://root:root@127.0.0.1:3306/cascade"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    MONGODB_URL: str = "mongodb://127.0.0.1:27017"
    MONGODB_DB: str = "cascade"

    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Auth
    AUTH_ENABLED: bool = False
    ADMIN_EXTERNAL_IDS: list[str] = []
    SSO_JWKS_URL: str | None = None
    SSO_ISSUER: str | None = None
    SSO_AUDIENCE: str | None = None

    # Rate limit
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_RUN_PER_MIN: int = 10
    RATE_LIMIT_WRITE_PER_MIN: int = 60

    # LLM
    LLM_PROVIDER: str = "claude"
    LLM_API_KEY: str = Field(default="", repr=False)
    LLM_MODEL_DEFAULT: str = "claude-sonnet-4-6"
    LLM_BASE_URL: str | None = None       # OpenAI 兼容协议自定义 endpoint(MiniMax / DeepSeek / Ollama 等)
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_MAX_CONCURRENCY: int = 20
    LLM_TEMPERATURE: float = 0.0

    # Sandbox(复用 ChatFlow 镜像,通过 SSH 连接,不做镜像维护)
    # 例:[{"id":"w1","host":"host.docker.internal","port":2222,"user":"root","password":"sandbox123"}]
    # 多 worker:列出多个;空数组 → 沙箱关闭(Phase3 不可用,不影响其他章节)
    SANDBOX_WORKERS: list[dict[str, str | int]] = []
    SANDBOX_TIMEOUT: int = 30
    SANDBOX_COMPILE_TIMEOUT: int = 120
    SANDBOX_CLEANUP_HOURS: int = 12

    # Workflow
    INNER_SDD_MAX: int = 3
    INNER_TDD_MAX: int = 5
    OUTER_FIX_MAX: int = 3
    WORKFLOW_GLOBAL_TIMEOUT: int = 900

    # Tool
    TOOL_DESCRIPTION_MAX_LENGTH: int = 15000
    TOOL_INJECTION_BLOCKLIST: list[str] = []

    # Mongo TTL / Archive
    MONGO_TRACE_TTL_DAYS: int = 90
    ARCHIVE_BUCKET: str | None = None
    ARCHIVE_ENABLED: bool = False

    # HTTP
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # 依赖启用开关(开发期降级)
    METRICS_ENABLED: bool = True
    MONGO_ENABLED: bool = True
    REDIS_ENABLED: bool = True

    # 分布式协调(K8S 部署必设)
    WORKER_ID: str = ""                   # 空 → 用 hostname(K8S Downward API 注入 POD 名)
    CHECKPOINTER_KIND: str = "memory"     # memory | redis | postgres | none;prod 必须 redis
    CHECKPOINTER_PG_URL: str | None = None

    @property
    def effective_celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
