import os


class Config:
    def __init__(self):
        # Service configuration
        self.environment = os.getenv("ENVIRONMENT", "dev")
        self.service_name = os.getenv("NAME_RELEASE_TG_BOT_CONTAINER_NAME", "name-tg-bot")
        self.http_port = os.getenv("NAME_RELEASE_TG_BOT_PORT", "8000")
        self.service_version = os.getenv("SERVICE_VERSION", "1.0.0")
        self.root_path = os.getenv("ROOT_PATH", "/")
        self.prefix = os.getenv("NAME_RELEASE_TG_BOT_PREFIX", "/api/tg-bot")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.release_tg_bot_token: str = os.environ.get('NAME_RELEASE_TG_BOT_TOKEN')
        self.github_token: str = os.environ.get("NAME_GITHUB_TOKEN")
        self.prod_host: str = os.environ.get("PROD_HOST")
        self.prod_password: str = os.environ.get("PROD_PASSWORD")
        self.prod_domain: str = os.environ.get("PROD_DOMAIN")

        self.required_approve_list = ["gommgo"]
        self.admins = ["gommgo"]

        self.service_port_map = {
            os.getenv("NAME_TG_BOT_CONTAINER_NAME"): int(os.getenv("NAME_TG_BOT_PORT")),
            os.getenv("NAME_ACCOUNT_CONTAINER_NAME"): int(os.getenv("NAME_ACCOUNT_PORT")),
            os.getenv("NAME_AUTHORIZATION_CONTAINER_NAME"): int(os.getenv("NAME_AUTHORIZATION_PORT")),
            os.getenv("NAME_EMPLOYEE_CONTAINER_NAME"): int(os.getenv("NAME_EMPLOYEE_PORT")),
            os.getenv("NAME_ORGANIZATION_CONTAINER_NAME"): int(os.getenv("NAME_ORGANIZATION_PORT")),
            os.getenv("NAME_CONTENT_CONTAINER_NAME"): int(os.getenv("NAME_CONTENT_PORT")),
        }

        self.service_prefix_map = {
            os.getenv("NAME_TG_BOT_CONTAINER_NAME"): os.getenv("NAME_TG_BOT_PREFIX"),
            os.getenv("NAME_ACCOUNT_CONTAINER_NAME"): os.getenv("NAME_ACCOUNT_PREFIX"),
            os.getenv("NAME_AUTHORIZATION_CONTAINER_NAME"): os.getenv("NAME_AUTHORIZATION_PREFIX"),
            os.getenv("NAME_EMPLOYEE_CONTAINER_NAME"): os.getenv("NAME_EMPLOYEE_PREFIX"),
            os.getenv("NAME_ORGANIZATION_CONTAINER_NAME"): os.getenv("NAME_ORGANIZATION_PREFIX"),
            os.getenv("NAME_CONTENT_CONTAINER_NAME"): os.getenv("NAME_CONTENT_PREFIX"),
            os.getenv("NAME_RELEASE_TG_BOT_CONTAINER_NAME"): os.getenv("NAME_RELEASE_TG_BOT_PREFIX"),
        }

        self.interserver_secret_key = os.getenv("NAME_INTERSERVER_SECRET_KEY")

        # PostgreSQL configuration
        self.db_host = os.getenv("NAME_RELEASE_TG_BOT_POSTGRES_CONTAINER_NAME", "localhost")
        self.db_port = "5432"
        self.db_name = os.getenv("NAME_RELEASE_TG_BOT_POSTGRES_DB_NAME", "hr_interview")
        self.db_user = os.getenv("NAME_RELEASE_TG_BOT_POSTGRES_USER", "postgres")
        self.db_pass = os.getenv("NAME_RELEASE_TG_BOT_POSTGRES_PASSWORD", "password")

        # Настройки телеметрии
        self.alert_tg_bot_token = os.getenv("NAME_ALERT_TG_BOT_TOKEN", "")
        self.alert_tg_chat_id = 56674614127611
        self.alert_tg_chat_thread_id = 0
        self.grafana_url = os.getenv("NAME_GRAFANA_URL", "")

        self.monitoring_redis_host = os.getenv("NAME_MONITORING_REDIS_CONTAINER_NAME", "localhost")
        self.monitoring_redis_port = int(os.getenv("NAME_MONITORING_REDIS_PORT", "6379"))
        self.monitoring_redis_db = int(os.getenv("NAME_MONITORING_DEDUPLICATE_ERROR_ALERT_REDIS_DB", "0"))
        self.monitoring_redis_password = os.getenv("NAME_MONITORING_REDIS_PASSWORD", "")

        # Настройки OpenTelemetry
        self.otlp_host = os.getenv("NAME_OTEL_COLLECTOR_CONTAINER_NAME", "name-otel-collector")
        self.otlp_port = int(os.getenv("NAME_OTEL_COLLECTOR_GRPC_PORT", "4317"))