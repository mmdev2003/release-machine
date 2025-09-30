import uvicorn

from infrastructure.pg.pg import PG
from infrastructure.telemetry.telemetry import Telemetry, AlertManager

from internal.controller.http.middlerware.middleware import HttpMiddleware
from internal.controller.http.handler.account.handler import AuthorizationController

from internal.service.account.service import AuthorizationService

from internal.repo.account.repo import AccountRepo

from internal.app.http.app import NewHTTP

from internal.config.config import Config

# Загрузка конфигурации
cfg = Config()

# Инициализация системы мониторинга
alert_manager = AlertManager(
    cfg.alert_tg_bot_token,
    cfg.service_name,
    cfg.alert_tg_chat_id,
    cfg.alert_tg_chat_thread_id,
    cfg.grafana_url,
    cfg.monitoring_redis_host,
    cfg.monitoring_redis_port,
    cfg.monitoring_redis_db,
    cfg.monitoring_redis_password,
    cfg.openai_api_key
)

tel = Telemetry(
    cfg.log_level,
    cfg.root_path,
    cfg.environment,
    cfg.service_name,
    cfg.service_version,
    cfg.otlp_host,
    cfg.otlp_port,
    alert_manager
)

# Инициализация инфраструктуры
db = PG(tel, cfg.db_user, cfg.db_pass, cfg.db_host, cfg.db_port, cfg.db_name)

# Инициализация репозиториев
authorization_repo = AccountRepo(tel, db)

# Инициализация сервисов
authorization_service = AuthorizationService(
    tel,
    authorization_repo,
    cfg.jwt_secret_key,
)

# Инициализация контроллеров
authorization_controller = AuthorizationController(
    tel,
    authorization_service,
    cfg.domain
)

# Инициализация middleware (без клиента Name Authorization для этого сервиса)
http_middleware = HttpMiddleware(
    tel,
    cfg.prefix,
)

if __name__ == "__main__":
    app = NewHTTP(
        db,
        authorization_controller,
        http_middleware,
        cfg.prefix,
    )
    uvicorn.run(app, host="0.0.0.0", port=int(cfg.http_port), access_log=False)