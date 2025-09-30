from opentelemetry.trace import Status, StatusCode, SpanKind
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from internal import interface
from internal.controller.http.handler.account.model import (
    RegisterBody, LoginBody, SetTwoFaBody, DeleteTwoFaBody,
    VerifyTwoFaBody, RecoveryPasswordBody, ChangePasswordBody
)


class AccountController(interface.IAccountController):
    def __init__(
            self,
            tel: interface.ITelemetry,
            account_service: interface.IAccountService,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.account_service = account_service

    async def register(self, body: RegisterBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "AccountController.register",
                kind=SpanKind.INTERNAL,
                attributes={"login": body.login}
        ) as span:
            try:
                self.logger.info("Registration request", {"login": body.login})

                authorization_data = await self.account_service.register(
                    login=body.login,
                    password=body.password
                )

                self.logger.info("Registration successful", {
                    "login": body.login,
                    "account_id": authorization_data.account_id
                })

                span.set_status(Status(StatusCode.OK))
                response = JSONResponse(
                    status_code=201,
                    content={
                        "message": "Account created successfully",
                        "account_id": authorization_data.account_id
                    }
                )

                # Устанавливаем токены в cookies
                response.set_cookie(
                    key="Access-Token",
                    value=authorization_data.access_token,
                    httponly=True,
                    secure=True,
                    samesite="strict"
                )
                response.set_cookie(
                    key="Refresh-Token",
                    value=authorization_data.refresh_token,
                    httponly=True,
                    secure=True,
                    samesite="strict"
                )

                return response

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def register_from_tg(self, body: RegisterBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "AccountController.register_from_tg",
                kind=SpanKind.INTERNAL,
                attributes={"login": body.login}
        ) as span:
            try:
                self.logger.info("Registration request", {"login": body.login})

                authorization_data = await self.account_service.register_from_tg(
                    login=body.login,
                    password=body.password
                )

                self.logger.info("Registration successful", {
                    "login": body.login,
                    "account_id": authorization_data.account_id
                })

                span.set_status(Status(StatusCode.OK))
                response = JSONResponse(
                    status_code=201,
                    content={
                        "message": "Account created successfully",
                        "account_id": authorization_data.account_id
                    }
                )

                # Устанавливаем токены в cookies
                response.set_cookie(
                    key="Access-Token",
                    value=authorization_data.access_token,
                    httponly=True,
                    secure=True,
                    samesite="strict"
                )
                response.set_cookie(
                    key="Refresh-Token",
                    value=authorization_data.refresh_token,
                    httponly=True,
                    secure=True,
                    samesite="strict"
                )

                return response

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def login(self, body: LoginBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "AccountController.login",
                kind=SpanKind.INTERNAL,
                attributes={"login": body.login}
        ) as span:
            try:
                self.logger.info("Login request", {"login": body.login})

                authorization_data = await self.account_service.login(
                    login=body.login,
                    password=body.password
                )

                self.logger.info("Login successful", {
                    "login": body.login,
                    "account_id": authorization_data.account_id
                })

                span.set_status(Status(StatusCode.OK))
                response = JSONResponse(
                    status_code=200,
                    content={
                        "message": "Login successful",
                        "account_id": authorization_data.account_id
                    }
                )

                # Устанавливаем токены в cookies
                response.set_cookie(
                    key="Access-Token",
                    value=authorization_data.access_token,
                    httponly=True,
                    secure=True,
                    samesite="strict"
                )
                response.set_cookie(
                    key="Refresh-Token",
                    value=authorization_data.refresh_token,
                    httponly=True,
                    secure=True,
                    samesite="strict"
                )

                return response

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                raise err

    async def generate_two_fa(self, request: Request) -> StreamingResponse:
        with self.tracer.start_as_current_span(
                "AccountController.generate_two_fa",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                authorization_data = request.state.authorization_data
                account_id = authorization_data.account_id

                if account_id == 0:
                    raise HTTPException(status_code=401, detail="Unauthorized")

                self.logger.info("Generate 2FA request", {"account_id": account_id})

                two_fa_key, qr_image = await self.account_service.generate_two_fa_key(account_id)

                self.logger.info("2FA generated successfully", {"account_id": account_id})

                def iterfile():
                    try:
                        while True:
                            chunk = qr_image.read(8192)
                            if not chunk:
                                break
                            yield chunk
                    finally:
                        qr_image.close()

                span.set_status(Status(StatusCode.OK))
                response = StreamingResponse(
                    iterfile(),
                    media_type="image/png",
                    headers={
                        "X-TwoFA-Key": two_fa_key,
                        "Content-Disposition": "inline; filename=qr_code.png"
                    }
                )

                return response

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def set_two_fa(self, request: Request, body: SetTwoFaBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "AccountController.set_two_fa",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем account_id из middleware авторизации
                authorization_data = request.state.authorization_data
                account_id = authorization_data.account_id

                if account_id == 0:
                    raise HTTPException(status_code=401, detail="Unauthorized")

                self.logger.info("Set 2FA request", {"account_id": account_id})

                await self.account_service.set_two_fa_key(
                    account_id=account_id,
                    google_two_fa_key=body.google_two_fa_key,
                    google_two_fa_code=body.google_two_fa_code
                )

                self.logger.info("2FA set successfully", {"account_id": account_id})

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content={"message": "Two-factor authentication enabled successfully"}
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                self.logger.error("Set 2FA failed", {
                    "account_id": getattr(request.state.authorization_data, 'account_id', 0),
                    "error": str(err)
                })
                raise err

    async def delete_two_fa(self, request: Request, body: DeleteTwoFaBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "AccountController.delete_two_fa",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем account_id из middleware авторизации
                authorization_data = request.state.authorization_data
                account_id = authorization_data.account_id

                if account_id == 0:
                    raise HTTPException(status_code=401, detail="Unauthorized")

                self.logger.info("Delete 2FA request", {"account_id": account_id})

                await self.account_service.delete_two_fa_key(
                    account_id=account_id,
                    google_two_fa_code=body.google_two_fa_code
                )

                self.logger.info("2FA deleted successfully", {"account_id": account_id})

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content={"message": "Two-factor authentication disabled successfully"}
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                raise err

    async def verify_two_fa(self, request: Request, body: VerifyTwoFaBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "AccountController.verify_two_fa",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем account_id из middleware авторизации
                authorization_data = request.state.authorization_data
                account_id = authorization_data.account_id

                if account_id == 0:
                    raise HTTPException(status_code=401, detail="Unauthorized")

                self.logger.info("Verify 2FA request", {"account_id": account_id})

                is_valid = await self.account_service.verify_two(
                    account_id=account_id,
                    google_two_fa_code=body.google_two_fa_code
                )

                self.logger.info("2FA verification completed", {
                    "account_id": account_id,
                    "is_valid": is_valid
                })

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "Two-factor authentication verified",
                        "is_valid": is_valid
                    }
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def recovery_password(self, request: Request, body: RecoveryPasswordBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "AccountController.recovery_password",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем account_id из middleware авторизации
                authorization_data = request.state.authorization_data
                account_id = authorization_data.account_id

                if account_id == 0:
                    raise HTTPException(status_code=401, detail="Unauthorized")

                self.logger.info("Password recovery request", {"account_id": account_id})

                await self.account_service.recovery_password(
                    account_id=account_id,
                    new_password=body.new_password
                )

                self.logger.info("Password recovery successful", {"account_id": account_id})

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content={"message": "Password recovered successfully"}
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def change_password(self, request: Request, body: ChangePasswordBody) -> JSONResponse:
        with self.tracer.start_as_current_span(
                "AccountController.change_password",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Получаем account_id из middleware авторизации
                authorization_data = request.state.authorization_data
                account_id = authorization_data.account_id

                if account_id == 0:
                    raise HTTPException(status_code=401, detail="Unauthorized")

                self.logger.info("Change password request", {"account_id": account_id})

                await self.account_service.change_password(
                    account_id=account_id,
                    new_password=body.new_password,
                    old_password=body.old_password
                )

                self.logger.info("Password changed successfully", {"account_id": account_id})

                span.set_status(Status(StatusCode.OK))
                return JSONResponse(
                    status_code=200,
                    content={"message": "Password changed successfully"}
                )

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err