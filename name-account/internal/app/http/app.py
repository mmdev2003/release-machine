from fastapi import FastAPI

from starlette.responses import StreamingResponse

from internal import model, interface
from internal.controller.http.handler.account.model import *


def NewHTTP(
        db: interface.IDB,
        account_controller: interface.IAccountController,
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

    include_account_handlers(app, account_controller, prefix)

    return app


def include_middleware(
        app: FastAPI,
        http_middleware: interface.IHttpMiddleware,
):
    http_middleware.authorization_middleware04(app)
    http_middleware.logger_middleware03(app)
    http_middleware.metrics_middleware02(app)
    http_middleware.trace_middleware01(app)


def include_account_handlers(
        app: FastAPI,
        account_controller: interface.IAccountController,
        prefix: str
):
    # Регистрация пользователя
    app.add_api_route(
        prefix + "/register",
        account_controller.register,
        methods=["POST"],
        tags=["Account"],
        response_model=RegisterResponse,
    )

    app.add_api_route(
        prefix + "/register/tg",
        account_controller.register,
        methods=["POST"],
        tags=["Account"],
        response_model=RegisterResponse,
    )

    # Вход пользователя
    app.add_api_route(
        prefix + "/login",
        account_controller.login,
        methods=["POST"],
        tags=["Account"],
        response_model=LoginResponse,
    )

    # Генерация 2FA QR кода
    app.add_api_route(
        prefix + "/2fa/generate",
        account_controller.generate_two_fa,
        methods=["GET"],
        tags=["Account"],
        response_class=StreamingResponse,
    )

    # Установка 2FA
    app.add_api_route(
        prefix + "/2fa/set",
        account_controller.set_two_fa,
        methods=["POST"],
        tags=["Account"],
        response_model=TwoFaResponse,
    )

    # Удаление 2FA
    app.add_api_route(
        prefix + "/2fa/delete",
        account_controller.delete_two_fa,
        methods=["DELETE"],
        tags=["Account"],
        response_model=TwoFaResponse,
    )

    # Верификация 2FA
    app.add_api_route(
        prefix + "/2fa/verify",
        account_controller.verify_two_fa,
        methods=["POST"],
        tags=["Account"],
        response_model=VerifyTwoFaResponse,
    )

    # Восстановление пароля
    app.add_api_route(
        prefix + "/password/recovery",
        account_controller.recovery_password,
        methods=["POST"],
        tags=["Account"],
        response_model=PasswordResponse,
    )

    # Изменение пароля
    app.add_api_route(
        prefix + "/password/change",
        account_controller.change_password,
        methods=["PUT"],
        tags=["Account"],
        response_model=PasswordResponse,
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
            await db.multi_query(model.create_tables_queries)
        except Exception as err:
            raise err

    return create_table


def drop_table_handler(db: interface.IDB):
    async def drop_table():
        try:
            await db.multi_query(model.drop_tables_queries)
        except Exception as err:
            raise err

    return drop_table
