from fastapi import FastAPI

from internal import model, interface


def NewServer(
        db: interface.IDB,
        http_middleware: interface.IHttpMiddleware,
        tg_webhook_controller: interface.ITelegramWebhookController,
        release_controller: interface.IReleaseController,
        prefix: str
):
    app = FastAPI(
        openapi_url=prefix + "/openapi.json",
        docs_url=prefix + "/docs",
        redoc_url=prefix + "/redoc",
    )
    include_http_middleware(app, http_middleware)

    include_db_handler(app, db, prefix)
    include_tg_webhook(app, tg_webhook_controller, prefix)
    include_release_handlers(app, release_controller, prefix)

    return app


def include_http_middleware(
        app: FastAPI,
        http_middleware: interface.IHttpMiddleware
):
    http_middleware.logger_middleware03(app)
    http_middleware.metrics_middleware02(app)
    http_middleware.trace_middleware01(app)


def include_tg_webhook(
        app: FastAPI,
        tg_webhook_controller: interface.ITelegramWebhookController,
        prefix: str
):
    app.add_api_route(
        prefix + "/update",
        tg_webhook_controller.bot_webhook,
        methods=["POST"]
    )
    app.add_api_route(
        prefix + "/webhook/set",
        tg_webhook_controller.bot_set_webhook,
        methods=["POST"]
    )


def include_release_handlers(
        app: FastAPI,
        release_controller: interface.IReleaseController,
        prefix: str
):
    app.add_api_route(
        prefix + "/release",
        release_controller.create_release,
        methods=["POST"],
        summary="Создать новый релиз",
        description="Создает новый релиз для указанного сервиса"
    )

    # Обновление статуса релиза
    app.add_api_route(
        prefix + "/release",
        release_controller.update_release,
        methods=["PATCH"],
        summary="Обновить статус релиза",
        description="Обновляет статус существующего релиза"
    )


def include_db_handler(app: FastAPI, db: interface.IDB, prefix):
    app.add_api_route(prefix + "/table/create", create_table_handler(db), methods=["GET"])
    app.add_api_route(prefix + "/table/drop", drop_table_handler(db), methods=["GET"])
    app.add_api_route(prefix + "/health", heath_check_handler(), methods=["GET"])


def create_table_handler(db: interface.IDB):
    async def create_table():
        try:
            await db.multi_query(model.create_queries)
        except Exception as err:
            raise err

    return create_table


def heath_check_handler():
    async def heath_check():
        return "ok"

    return heath_check


def drop_table_handler(db: interface.IDB):
    async def delete_table():
        try:
            await db.multi_query(model.drop_queries)
        except Exception as err:
            raise err

    return delete_table
