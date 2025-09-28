import os


class Config:
    def __init__(self):
        # Service configuration
        self.environment = os.getenv("ENVIRONMENT", "dev")
        self.service_name = os.getenv("LOOM_RELEASE_TG_BOT_CONTAINER_NAME", "loom-tg-bot")
        self.http_port = os.getenv("LOOM_RELEASE_TG_BOT_PORT", "8000")
        self.service_version = os.getenv("SERVICE_VERSION", "1.0.0")
        self.root_path = os.getenv("ROOT_PATH", "/")
        self.prefix = os.getenv("LOOM_RELEASE_TG_BOT_PREFIX", "/api/tg-bot")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.release_tg_bot_token: str = os.environ.get('LOOM_RELEASE_TG_BOT_TOKEN')
        self.domain: str = os.environ.get("LOOM_DOMAIN")
        self.github_token: str = os.environ.get("LOOM_GITHUB_TOKEN")
        self.prod_host: str = os.environ.get("PROD_HOST")
        self.prod_password: str = os.environ.get("PROD_PASSWORD")
        self.loom_release_tg_bot_api_url: str = os.environ.get("LOOM_RELEASE_TG_BOT_API_URL")

        self.service_port_map = {
            os.getenv("LOOM_TG_BOT_CONTAINER_NAME"): int(os.getenv("LOOM_TG_BOT_PORT")),
            os.getenv("LOOM_ACCOUNT_CONTAINER_NAME"): int(os.getenv("LOOM_ACCOUNT_PORT")),
            os.getenv("LOOM_AUTHORIZATION_CONTAINER_NAME"): int(os.getenv("LOOM_AUTHORIZATION_PORT")),
            os.getenv("LOOM_EMPLOYEE_CONTAINER_NAME"): int(os.getenv("LOOM_EMPLOYEE_PORT")),
            os.getenv("LOOM_ORGANIZATION_CONTAINER_NAME"): int(os.getenv("LOOM_ORGANIZATION_PORT")),
            os.getenv("LOOM_CONTENT_CONTAINER_NAME"): int(os.getenv("LOOM_CONTENT_PORT")),
        }

        self.interserver_secret_key = os.getenv("LOOM_INTERSERVER_SECRET_KEY")

        # PostgreSQL configuration
        self.db_host = os.getenv("LOOM_RELEASE_TG_BOT_POSTGRES_CONTAINER_NAME", "localhost")
        self.db_port = "5432"
        self.db_name = os.getenv("LOOM_RELEASE_TG_BOT_POSTGRES_DB_NAME", "hr_interview")
        self.db_user = os.getenv("LOOM_RELEASE_TG_BOT_POSTGRES_USER", "postgres")
        self.db_pass = os.getenv("LOOM_RELEASE_TG_BOT_POSTGRES_PASSWORD", "password")

        # Настройки телеметрии
        self.alert_tg_bot_token = os.getenv("LOOM_ALERT_TG_BOT_TOKEN", "")
        self.alert_tg_chat_id = 5667467611
        self.alert_tg_chat_thread_id = 0
        self.grafana_url = os.getenv("LOOM_GRAFANA_URL", "")

        self.monitoring_redis_host = os.getenv("LOOM_MONITORING_REDIS_CONTAINER_NAME", "localhost")
        self.monitoring_redis_port = int(os.getenv("LOOM_MONITORING_REDIS_PORT", "6379"))
        self.monitoring_redis_db = int(os.getenv("LOOM_MONITORING_DEDUPLICATE_ERROR_ALERT_REDIS_DB", "0"))
        self.monitoring_redis_password = os.getenv("LOOM_MONITORING_REDIS_PASSWORD", "")

        # Настройки OpenTelemetry
        self.otlp_host = os.getenv("LOOM_OTEL_COLLECTOR_CONTAINER_NAME", "loom-otel-collector")
        self.otlp_port = int(os.getenv("LOOM_OTEL_COLLECTOR_GRPC_PORT", "4317"))