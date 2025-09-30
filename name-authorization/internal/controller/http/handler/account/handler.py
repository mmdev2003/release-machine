import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import interface
from internal import model
from internal import common

from .model import *


class AuthorizationController(interface.IAuthorizationController):
    def __init__(
            self,
            tel: interface.ITelemetry,
            authorization_service: interface.IAuthorizationService,
            domain: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.authorization_service = authorization_service
        self.domain = domain

    async def authorization(self, body: AuthorizationBody):
        account_id = body.account_id
        two_fa_status = body.two_fa_status
        role = body.role

        with self.tracer.start_as_current_span(
                "AuthorizationController.authorization",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                    "two_fa_status": two_fa_status
                }
        ) as span:
            try:
                jwt_token: model.JWTToken = await self.authorization_service.create_tokens(
                    account_id,
                    two_fa_status,
                    role
                )

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content=AuthorizationResponse(
                        access_token=jwt_token.access_token,
                        refresh_token=jwt_token.refresh_token
                    ).model_dump(),
                )
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise e

    async def authorization_tg(self, body: AuthorizationBody):
        account_id = body.account_id
        two_fa_status = body.two_fa_status
        role = body.role

        with self.tracer.start_as_current_span(
                "AuthorizationController.authorization_tg",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                    "two_fa_status": two_fa_status
                }
        ) as span:
            try:
                jwt_token: model.JWTToken = await self.authorization_service.create_tokens_tg(
                    account_id,
                    two_fa_status,
                    role
                )

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content=AuthorizationResponse(
                        access_token=jwt_token.access_token,
                        refresh_token=jwt_token.refresh_token
                    ).model_dump(),
                )
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise e

    async def check_authorization(self, request: Request):
        with self.tracer.start_as_current_span(
                "AuthorizationController.check_authorization",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                access_token = request.cookies.get("Access-Token")
                token_payload = await self.authorization_service.check_token(
                    access_token,
                )

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content=CheckAuthorizationResponse(
                        account_id=token_payload.account_id,
                        two_fa_status=token_payload.two_fa_status,
                        role=token_payload.role,
                        message="Access-Token verified"
                    ).model_dump(),
                )
            except jwt.ExpiredSignatureError as e:
                self.logger.warning("Токен истек")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                return JSONResponse(
                    status_code=403,
                    content={"message": "token expired"}
                )
            except jwt.InvalidTokenError as e:
                self.logger.warning("Токен не валиден")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                return JSONResponse(
                    status_code=403,
                    content={"message": "token invalid"}
                )
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise e

    async def refresh_token(self, request: Request):
        with self.tracer.start_as_current_span(
                "AuthorizationController.refresh_token",
                kind=SpanKind.INTERNAL
        ) as span:

            try:
                refresh_token = request.cookies.get("Refresh-Token")
                jwt_token = await self.authorization_service.refresh_token(
                    refresh_token,
                )

                response = JSONResponse(status_code=200, content={"message": "ok"})
                response.set_cookie(
                    key="Access-Token",
                    value=jwt_token.access_token,
                    expires=datetime.now() + timedelta(minutes=15),
                    httponly=True,
                    path="/",
                    domain=self.domain
                )
                response.set_cookie(
                    key="Refresh-Token",
                    value=jwt_token.refresh_token,
                    expires=datetime.now() + timedelta(hours=1),
                    httponly=True,
                    path="/",
                    domain=self.domain
                )

                span.set_status(Status(StatusCode.OK))
                return response
            except common.ErrAccountNotFound as e:
                self.logger.warning("Не найден аккаунт")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                return JSONResponse(
                    status_code=400,
                    content={"message": "account not found"}
                )
            except jwt.ExpiredSignatureError as e:
                self.logger.warning("Токен истек")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                return JSONResponse(
                    status_code=403,
                    content={"message": "token expired"}
                )
            except jwt.InvalidTokenError as e:
                self.logger.warning("Токен не валиден")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                return JSONResponse(
                    status_code=403,
                    content={"message": "token invalid"}
                )
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise e


    async def refresh_token_tg(self, request: Request):
        with self.tracer.start_as_current_span(
                "AuthorizationController.refresh_token_tg",
                kind=SpanKind.INTERNAL
        ) as span:

            try:
                refresh_token = request.cookies.get("Refresh-Token")
                jwt_token = await self.authorization_service.refresh_token_tg(
                    refresh_token,
                )

                response = JSONResponse(status_code=200, content={"message": "ok"})
                response.set_cookie(
                    key="Access-Token",
                    value=jwt_token.access_token,
                    expires=datetime.now() + timedelta(minutes=15),
                    httponly=True,
                    path="/",
                    domain=self.domain
                )
                response.set_cookie(
                    key="Refresh-Token",
                    value=jwt_token.refresh_token,
                    expires=datetime.now() + timedelta(hours=1),
                    httponly=True,
                    path="/",
                    domain=self.domain
                )

                span.set_status(Status(StatusCode.OK))
                return response
            except common.ErrAccountNotFound as e:
                self.logger.warning("Не найден аккаунт")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                return JSONResponse(
                    status_code=400,
                    content={"message": "account not found"}
                )
            except jwt.ExpiredSignatureError as e:
                self.logger.warning("Токен истек")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                return JSONResponse(
                    status_code=403,
                    content={"message": "token expired"}
                )
            except jwt.InvalidTokenError as e:
                self.logger.warning("Токен не валиден")
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                return JSONResponse(
                    status_code=403,
                    content={"message": "token invalid"}
                )
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise e