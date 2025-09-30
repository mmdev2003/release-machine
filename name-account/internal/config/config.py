import os


class Config:
    def __init__(self):
        # Основные настройки приложения
        self.environment = os.getenv("ENVIRONMENT", "dev")
        self.service_name = os.getenv("NAME_ACCOUNT_CONTAINER_NAME", "name-account")
        self.http_port = os.getenv("NAME_ACCOUNT_PORT", "8000")
        self.service_version = os.getenv("SERVICE_VERSION", "1.0.0")
        self.root_path = os.getenv("ROOT_PATH", "/")
        self.prefix = os.getenv("NAME_ACCOUNT_PREFIX", "/api/account")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Настройки базы данных
        self.db_host = os.getenv("NAME_ACCOUNT_POSTGRES_CONTAINER_NAME", "localhost")
        self.db_port = "5432"
        self.db_name = os.getenv("NAME_ACCOUNT_POSTGRES_DB_NAME", "hr_interview")
        self.db_user = os.getenv("NAME_ACCOUNT_POSTGRES_USER", "postgres")
        self.db_pass = os.getenv("NAME_ACCOUNT_POSTGRES_PASSWORD", "password")

        # Настройки мониторинга и алертов
        self.alert_tg_bot_token = os.getenv("NAME_ALERT_TG_BOT_TOKEN", "")
        self.alert_tg_chat_id = int(os.getenv("NAME_ALERT_TG_CHAT_ID", "0"))
        self.alert_tg_chat_thread_id = int(os.getenv("NAME_ALERT_TG_CHAT_THREAD_ID", "0"))
        self.grafana_url = os.getenv("NAME_GRAFANA_URL", "")

        self.monitoring_redis_host = os.getenv("NAME_MONITORING_REDIS_CONTAINER_NAME", "localhost")
        self.monitoring_redis_port = int(os.getenv("NAME_MONITORING_REDIS_PORT", "6379"))
        self.monitoring_redis_db = int(os.getenv("NAME_MONITORING_DEDUPLICATE_ERROR_ALERT_REDIS_DB", "0"))
        self.monitoring_redis_password = os.getenv("NAME_MONITORING_REDIS_PASSWORD", "")

        # Настройки OpenTelemetry
        self.otlp_host = os.getenv("NAME_OTEL_COLLECTOR_CONTAINER_NAME", "name-otel-collector")
        self.otlp_port = int(os.getenv("NAME_OTEL_COLLECTOR_GRPC_PORT", "4317"))

        # Настройки авторизации
        self.name_authorization_host = os.getenv("NAME_AUTHORIZATION_CONTAINER_NAME", "name-authorization-postgres")
        self.name_authorization_port = os.getenv("NAME_AUTHORIZATION_PORT", "8001")
        self.password_secret_key = os.getenv("NAME_PASSWORD_SECRET_KEY", "default-secret-key-change-me")

        self.openai_api_key = os.getenv("OPENAI_API_KEY", None)