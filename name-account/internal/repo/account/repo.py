from opentelemetry.trace import Status, StatusCode, SpanKind

from .sql_query import *
from internal import interface, model, common


class AccountRepo(interface.IAccountRepo):
    def __init__(
            self,
            tel: interface.ITelemetry,
            db: interface.IDB,
    ):
        self.tracer = tel.tracer()
        self.db = db

    async def create_account(self, login: str, password: str) -> int:
        with self.tracer.start_as_current_span(
                "AccountRepo.create_account",
                kind=SpanKind.INTERNAL,
                attributes={
                    "login": login
                }
        ) as span:
            try:
                # Проверяем, существует ли уже аккаунт с таким логином
                existing_accounts = await self.account_by_login(login)
                if existing_accounts:
                    raise common.ErrAccountCreate()

                args = {
                    'login': login,
                    'password': password,
                }

                account_id = await self.db.insert(create_account, args)

                span.set_status(Status(StatusCode.OK))
                return account_id
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def account_by_id(self, account_id: int) -> list[model.Account]:
        with self.tracer.start_as_current_span(
                "AccountRepo.account_by_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                args = {'account_id': account_id}
                rows = await self.db.select(get_account_by_id, args)
                accounts = model.Account.serialize(rows) if rows else []

                span.set_status(Status(StatusCode.OK))
                return accounts
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def account_by_login(self, login: str) -> list[model.Account]:
        with self.tracer.start_as_current_span(
                "AccountRepo.account_by_login",
                kind=SpanKind.INTERNAL,
                attributes={
                    "login": login
                }
        ) as span:
            try:
                args = {'login': login}
                rows = await self.db.select(get_account_by_login, args)
                accounts = model.Account.serialize(rows) if rows else []

                span.set_status(Status(StatusCode.OK))
                return accounts
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def set_two_fa_key(self, account_id: int, google_two_fa_key: str) -> None:
        with self.tracer.start_as_current_span(
                "AccountRepo.set_two_fa_key",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                args = {
                    'account_id': account_id,
                    'google_two_fa_key': google_two_fa_key,
                }
                await self.db.update(set_two_fa_key, args)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def delete_two_fa_key(self, account_id: int) -> None:
        with self.tracer.start_as_current_span(
                "AccountRepo.delete_two_fa_key",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                args = {'account_id': account_id}
                await self.db.update(delete_two_fa_key, args)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def update_password(self, account_id: int, new_password: str) -> None:
        with self.tracer.start_as_current_span(
                "AccountRepo.update_password",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id
                }
        ) as span:
            try:
                args = {
                    'account_id': account_id,
                    'new_password': new_password,
                }
                await self.db.update(update_password, args)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err