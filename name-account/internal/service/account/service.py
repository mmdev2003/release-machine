import bcrypt
import pyotp
import qrcode
import io

from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import interface
from internal import model
from internal import common


class AccountService(interface.IAccountService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            account_repo: interface.IAccountRepo,
            name_authorization_client: interface.INameAuthorizationClient,
            password_secret_key: str
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.account_repo = account_repo
        self.name_authorization_client = name_authorization_client
        self.password_secret_key = password_secret_key

    async def register(self, login: str, password: str) -> model.AuthorizationDataDTO:
        with self.tracer.start_as_current_span(
                "AccountService.register",
                kind=SpanKind.INTERNAL,
                attributes={
                    "login": login
                }
        ) as span:
            try:
                hashed_password = self.__hash_password(password)

                account_id = await self.account_repo.create_account(login, hashed_password)

                jwt_token = await self.name_authorization_client.authorization(
                    account_id,
                    False,
                    "employee"
                )

                span.set_status(StatusCode.OK)
                return model.AuthorizationDataDTO(
                    account_id=account_id,
                    access_token=jwt_token.access_token,
                    refresh_token=jwt_token.refresh_token,
                )

            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise

    async def register_from_tg(self, login: str, password: str) -> model.AuthorizationDataDTO:
        with self.tracer.start_as_current_span(
                "AccountService.register_from_tg",
                kind=SpanKind.INTERNAL,
                attributes={
                    "login": login
                }
        ) as span:
            try:
                hashed_password = self.__hash_password(password)

                account_id = await self.account_repo.create_account(login, hashed_password)

                jwt_token = await self.name_authorization_client.authorization_tg(
                    account_id,
                    False,
                    "employee"
                )

                span.set_status(StatusCode.OK)
                return model.AuthorizationDataDTO(
                    account_id=account_id,
                    access_token=jwt_token.access_token,
                    refresh_token=jwt_token.refresh_token,
                )

            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR, str(e))
                raise

    async def login(self, login: str, password: str) -> model.AuthorizationDataDTO | None:
        with self.tracer.start_as_current_span(
                "AccountService.login",
                kind=SpanKind.INTERNAL,
                attributes={
                    "login": login
                }
        ) as span:
            try:
                account = await self.account_repo.account_by_login(login)
                if not account:
                    raise common.ErrAccountNotFound()
                account = account[0]

                if not self.__verify_password(account.password, password):
                    raise common.ErrInvalidPassword()

                jwt_token = await self.name_authorization_client.authorization(
                    account.id,
                    True if account.google_two_fa_key else False,
                    "employee"
                )

                span.set_status(Status(StatusCode.OK))
                return model.AuthorizationDataDTO(
                    account_id=account.id,
                    access_token=jwt_token.access_token,
                    refresh_token=jwt_token.refresh_token,
                )
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def generate_two_fa_key(self, account_id: int) -> tuple[str, io.BytesIO]:
        with self.tracer.start_as_current_span(
                "AccountService.generate_two_fa_key",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                two_fa_key = pyotp.random_base32()
                totp_auth = pyotp.totp.TOTP(two_fa_key).provisioning_uri(
                    name=f"account_id-{account_id}",
                    issuer_name="crmessenger"
                )

                qr_image = io.BytesIO()
                qrcode.make(totp_auth).save(qr_image)
                qr_image.seek(0)

                span.set_status(Status(StatusCode.OK))
                return two_fa_key, qr_image
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def set_two_fa_key(self, account_id: int, google_two_fa_key: str, google_two_fa_code: str) -> None:
        with self.tracer.start_as_current_span(
                "AccountService.set_two_fa_key",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                account = (await self.account_repo.account_by_id(account_id))[0]

                if account.google_two_fa_key:
                    raise common.ErrTwoFaAlreadyEnabled()

                is_two_fa_verified = self.__verify_two_fa(google_two_fa_code, google_two_fa_key)
                if not is_two_fa_verified:
                    raise common.ErrTwoFaCodeInvalid()

                await self.account_repo.set_two_fa_key(account_id, google_two_fa_key)

                span.set_status(Status(StatusCode.OK))
                return None
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def delete_two_fa_key(self, account_id: int, google_two_fa_code: str) -> None:
        with self.tracer.start_as_current_span(
                "AccountService.delete_two_fa_key",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                account = (await self.account_repo.account_by_id(account_id))[0]
                if not account.google_two_fa_key:
                    raise common.ErrTwoFaNotEnabled()

                is_two_fa_verified = self.__verify_two_fa(google_two_fa_code, account.google_two_fa_key)
                if not is_two_fa_verified:
                    raise common.ErrTwoFaCodeInvalid()

                await self.account_repo.delete_two_fa_key(account_id)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def verify_two(self, account_id: int, google_two_fa_code: str) -> bool:
        with self.tracer.start_as_current_span(
                "AccountService.verify_two",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                account = (await self.account_repo.account_by_id(account_id))[0]
                if not account.google_two_fa_key:
                    raise common.ErrTwoFaNotEnabled()

                is_two_fa_verified = self.__verify_two_fa(google_two_fa_code, account.google_two_fa_key)

                span.set_status(Status(StatusCode.OK))
                return is_two_fa_verified
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


    async def recovery_password(self, account_id: int, new_password: str) -> None:
        with self.tracer.start_as_current_span(
                "AccountService.recovery_password",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                new_hashed_password = self.__hash_password(new_password)
                await self.account_repo.update_password(account_id, new_hashed_password)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    async def change_password(self, account_id: int, new_password: str, old_password: str) -> None:
        with self.tracer.start_as_current_span(
                "AccountService.change_password",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                account = (await self.account_repo.account_by_id(account_id))[0]

                if not self.__verify_password(account.password, old_password):
                    raise common.ErrInvalidPassword()

                new_hashed_password = self.__hash_password(new_password)
                await self.account_repo.update_password(account_id, new_hashed_password)

                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    def __verify_password(self, hashed_password: str, password: str) -> bool:
        with self.tracer.start_as_current_span(
                "AccountService.__verify_password",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                peppered_password = self.password_secret_key + password

                span.set_status(Status(StatusCode.OK))
                return bcrypt.checkpw(peppered_password.encode('utf-8'), hashed_password.encode('utf-8'))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    def __verify_two_fa(self, two_fa_code: str, two_fa_key: str) -> bool:
        with self.tracer.start_as_current_span(
                "AccountService.__verify_two_fa",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                totp = pyotp.TOTP(two_fa_key)

                span.set_status(Status(StatusCode.OK))
                return totp.verify(two_fa_code)
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    def __hash_password(self, password: str) -> str:
        with self.tracer.start_as_current_span(
                "AccountService.__hash_password",
                kind=SpanKind.INTERNAL,
        ) as span:
            try:
                peppered_password = self.password_secret_key + password
                hashed_password = bcrypt.hashpw(peppered_password.encode('utf-8'), bcrypt.gensalt())

                span.set_status(Status(StatusCode.OK))
                return hashed_password.decode('utf-8')
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise