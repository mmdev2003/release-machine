import uvicorn
from aiogram import Bot, Dispatcher
import redis.asyncio as redis
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from sulguk import AiogramSulgukMiddleware

from infrastructure.pg.pg import PG
from infrastructure.telemetry.telemetry import Telemetry, AlertManager
from pkg.client.external.github.client import GitHubClient

from internal.controller.http.middlerware.middleware import HttpMiddleware
from internal.controller.tg.middleware.middleware import TgMiddleware

from internal.controller.tg.command.handler import CommandController
from internal.controller.http.webhook.handler import TelegramWebhookController
from internal.controller.http.handler.release.handler import ReleaseController

from internal.dialog.main_menu.dialog import MainMenuDialog
from internal.dialog.active_release.dialog import ActiveReleaseDialog
from internal.dialog.success_release.dialog import SuccessfulReleasesDialog
from internal.dialog.failed_release.dialog import FailedReleasesDialog

from internal.service.release.service import ReleaseService
from internal.dialog.main_menu.service import MainMenuService
from internal.dialog.active_release.service import ActiveReleaseService
from internal.dialog.success_release.service import SuccessfulReleasesService
from internal.dialog.failed_release.service import FailedReleasesService

from internal.dialog.main_menu.getter import MainMenuGetter
from internal.dialog.active_release.getter import ActiveReleaseGetter
from internal.dialog.success_release.getter import SuccessfulReleasesGetter
from internal.dialog.failed_release.getter import FailedReleasesGetter

from internal.repo.release.repo import ReleaseRepo

from internal.app.tg.app import NewTg
from internal.app.server.app import NewServer

from internal.config.config import Config

cfg = Config()

# Инициализация мониторинга
alert_manager = AlertManager(
    cfg.alert_tg_bot_token,
    cfg.service_name,
    cfg.alert_tg_chat_id,
    cfg.alert_tg_chat_thread_id,
    cfg.grafana_url,
    cfg.monitoring_redis_host,
    cfg.monitoring_redis_port,
    cfg.monitoring_redis_db,
    cfg.monitoring_redis_password
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

redis_client = redis.Redis(
    host=cfg.monitoring_redis_host,
    port=cfg.monitoring_redis_port,
    password=cfg.monitoring_redis_password,
    db=3
)
key_builder = DefaultKeyBuilder(with_destiny=True)
storage = RedisStorage(
    redis=redis_client,
    key_builder=key_builder
)
dp = Dispatcher(storage=storage)
bot = Bot(token=cfg.release_tg_bot_token)
bot.session.middleware(AiogramSulgukMiddleware())

# Инициализация клиентов
db = PG(tel, cfg.db_user, cfg.db_pass, cfg.db_host, cfg.db_port, cfg.db_name)

github_client = GitHubClient(
    tel,
    cfg.github_token
)

release_repo = ReleaseRepo(tel, db)

main_menu_getter = MainMenuGetter(
    tel
)

active_release_getter = ActiveReleaseGetter(
    tel,
    release_repo,
    cfg.required_approve_list
)

successful_releases_getter = SuccessfulReleasesGetter(
    tel,
    release_repo
)

failed_releases_getter = FailedReleasesGetter(
    tel,
    release_repo
)

# Инициализация сервисов
release_service = ReleaseService(
    tel,
    release_repo,
    cfg.prod_host,
    cfg.prod_password,
    cfg.prod_domain,
    cfg.service_port_map,
    cfg.service_prefix_map,
)
main_menu_service = MainMenuService(
    tel,
)

active_release_service = ActiveReleaseService(
    tel,
    release_service,
    github_client,
    cfg.required_approve_list
)

successful_releases_service = SuccessfulReleasesService(
    tel,
    release_service,
    cfg.admins
)

failed_releases_service = FailedReleasesService(
    tel,
    release_service,
    cfg.admins
)

main_menu_dialog = MainMenuDialog(
    tel,
    main_menu_service,
    main_menu_getter
)

active_release_dialog = ActiveReleaseDialog(
    tel,
    active_release_service,
    active_release_getter,
)

successful_releases_dialog = SuccessfulReleasesDialog(
    tel,
    successful_releases_service,
    successful_releases_getter,
)

failed_releases_dialog = FailedReleasesDialog(
    tel,
    failed_releases_service,
    failed_releases_getter,
)

command_controller = CommandController(tel)

dialog_bg_factory = NewTg(
    dp,
    command_controller,
    main_menu_dialog,
    active_release_dialog,
    successful_releases_dialog,
    failed_releases_dialog
)

# Инициализация middleware
tg_middleware = TgMiddleware(
    tel,
    bot,
)
http_middleware = HttpMiddleware(
    tel,
    cfg.prefix,
)
tg_webhook_controller = TelegramWebhookController(
    tel,
    dp,
    bot,
    cfg.prod_domain,
    cfg.prefix,
)

release_controller = ReleaseController(
    tel,
    release_service,
)

if __name__ == "__main__":
    app = NewServer(
        db,
        http_middleware,
        tg_webhook_controller,
        release_controller,
        cfg.prefix,
    )
    uvicorn.run(app, host="0.0.0.0", port=int(cfg.http_port), access_log=False)
