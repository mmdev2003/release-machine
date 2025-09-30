import jwt
import time

from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import interface
from internal import common
from internal import model


class AuthorizationService(interface.IAuthorizationService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            authorization_repo: interface.IAuthorizationRepo,
            jwt_secret_key: str,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.authorization_repo = authorization_repo
        self.jwt_secret_key = jwt_secret_key

    async def create_tokens(
            self,
            account_id: int,
            two_fa_status: bool,
            role: str,
    ) -> model.JWTToken:
        with self.tracer.start_as_current_span(
                "AuthorizationService.create_tokens",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                    "two_fa_status": two_fa_status,
                }
        ) as span:
            try:
                account = await self.authorization_repo.account_by_id(account_id)
                if not account:
                    await self.authorization_repo.create_account(account_id)
                    self.logger.info("Создали новый аккаунт")

                    account = await self.authorization_repo.account_by_id(account_id)
                account = account[0]

                access_token_payload = {
                    "account_id": account_id,
                    "two_fa_status": two_fa_status,
                    "role": role,
                    "exp": int(time.time()) + 15 * 60,
                }
                access_token = jwt.encode(access_token_payload, self.jwt_secret_key, algorithm="HS256")

                refresh_token_payload = {
                    "account_id": account_id,
                    "two_fa_status": two_fa_status,
                    "role": role,
                    "exp": int(time.time()) + 15 * 60,
                }
                refresh_token = jwt.encode(refresh_token_payload, self.jwt_secret_key, algorithm="HS256")

                await self.authorization_repo.update_refresh_token(account.id, refresh_token)
                self.logger.debug("Обновили refresh токен в БД")

                span.set_status(Status(StatusCode.OK))
                return model.JWTToken(access_token, refresh_token)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def create_tokens_tg(
            self,
            account_id: int,
            two_fa_status: bool,
            role: str,
    ) -> model.JWTToken:
        with self.tracer.start_as_current_span(
                "AuthorizationService.create_tokens_tg",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                    "two_fa_status": two_fa_status,
                }
        ) as span:
            try:
                account = await self.authorization_repo.account_by_id(account_id)
                if not account:
                    await self.authorization_repo.create_account(account_id)
                    self.logger.info("Создали новый аккаунт")

                    account = await self.authorization_repo.account_by_id(account_id)
                account = account[0]

                access_token_payload = {
                    "account_id": account_id,
                    "two_fa_status": two_fa_status,
                    "role": role,
                    "exp": int(time.time()) + 15 * 60,
                }
                access_token = jwt.encode(access_token_payload, self.jwt_secret_key, algorithm="HS256")

                refresh_token_payload = {
                    "account_id": account_id,
                    "two_fa_status": two_fa_status,
                    "role": role,
                    "exp": int(time.time()) + 24 * 365 * 10 * 60,
                }
                refresh_token = jwt.encode(refresh_token_payload, self.jwt_secret_key, algorithm="HS256")

                await self.authorization_repo.update_refresh_token(account.id, refresh_token)
                self.logger.debug("Обновили refresh токен в БД")

                span.set_status(Status(StatusCode.OK))
                return model.JWTToken(access_token, refresh_token)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def check_token(self, token: str) -> model.TokenPayload:
        with self.tracer.start_as_current_span(
                "AuthorizationService.check_token",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                payload = jwt.decode(
                    jwt=token,
                    key=self.jwt_secret_key,
                    algorithms=["HS256"]
                )
                self.logger.debug("Расшифровали access токен")

                span.set_status(Status(StatusCode.OK))
                return model.TokenPayload(
                    account_id=int(payload["account_id"]),
                    two_fa_status=bool(payload["two_fa_status"]),
                    role=payload["role"],
                    exp=int(payload["exp"]),
                )
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def refresh_token(self, refresh_token: str) -> model.JWTToken:
        with self.tracer.start_as_current_span(
                "AuthorizationService.refresh_token",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                account = await self.authorization_repo.account_by_refresh_token(refresh_token)
                if not account:
                    raise common.ErrAccountNotFound()

                token_payload = await self.check_token(refresh_token)
                jwt_token = await self.create_tokens(
                    token_payload.account_id,
                    token_payload.two_fa_status,
                    token_payload.role
                )

                span.set_status(Status(StatusCode.OK))
                return jwt_token
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def refresh_token_tg(self, refresh_token: str) -> model.JWTToken:
        with self.tracer.start_as_current_span(
                "AuthorizationService.refresh_token_tg",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                account = await self.authorization_repo.account_by_refresh_token(refresh_token)
                if not account:
                    raise common.ErrAccountNotFound()

                token_payload = await self.check_token(refresh_token)
                jwt_token = await self.create_tokens_tg(
                    token_payload.account_id,
                    token_payload.two_fa_status,
                    token_payload.role
                )

                span.set_status(Status(StatusCode.OK))
                return jwt_token
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
