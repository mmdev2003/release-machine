from fastapi import FastAPI

from internal import interface, model
from internal.controller.http.handler.account.model import *


def NewHTTP(
        db: interface.IDB,
        authorization_controller: interface.IAuthorizationController,
        http_middleware: interface.IHttpMiddleware,
        prefix: str
):
    app = FastAPI(
        openapi_url=prefix + "/openapi.json",
        docs_url=prefix + "/docs",
        redoc_url=prefix + "/redoc",
    )

    include_middleware(app, http_middleware)
    include_db_handler(app, db, prefix)
    include_authorization_handlers(app, authorization_controller, prefix)

    return app


def include_middleware(
        app: FastAPI,
        http_middleware: interface.IHttpMiddleware
):
    http_middleware.logger_middleware03(app)
    http_middleware.metrics_middleware02(app)
    http_middleware.trace_middleware01(app)


def include_authorization_handlers(
        app: FastAPI,
        authorization_controller: interface.IAuthorizationController,
        prefix: str
):
    # Авторизация (создание токенов)
    app.add_api_route(
        prefix,
        authorization_controller.authorization,
        tags=["Authorization"],
        methods=["POST"],
        response_model=AuthorizationResponse,
    )

    # Авторизация (создание токенов)
    app.add_api_route(
        prefix + "/tg",
        authorization_controller.authorization_tg,
        tags=["Authorization"],
        methods=["POST"],
        response_model=AuthorizationResponse,
    )

    # Проверка токена
    app.add_api_route(
        prefix + "/check",
        authorization_controller.check_authorization,
        tags=["Authorization"],
        methods=["GET"],
        response_model=CheckAuthorizationResponse,
    )

    # Обновление токенов
    app.add_api_route(
        prefix + "/refresh",
        authorization_controller.refresh_token,
        tags=["Authorization"],
        methods=["POST"],
    )


def include_db_handler(app: FastAPI, db: interface.IDB, prefix: str):
    app.add_api_route(prefix + "/table/create", create_table_handler(db), methods=["GET"])
    app.add_api_route(prefix + "/table/drop", drop_table_handler(db), methods=["GET"])
    app.add_api_route(prefix + "/health", heath_check_handler(), methods=["GET"])

def heath_check_handler():
    async def heath_check():
        return "ok"

    return heath_check

def create_table_handler(db: interface.IDB):
    async def create_table():
        try:
            await db.multi_query(model.create_queries)
        except Exception as err:
            raise err

    return create_table


def drop_table_handler(db: interface.IDB):
    async def drop_table():
        try:
            await db.multi_query(model.drop_queries)
        except Exception as err:
            raise err

    return drop_table
