from opentelemetry.trace import SpanKind, Status, StatusCode

from .sql_query import *
from internal import model
from internal import interface


class AccountRepo(interface.IAuthorizationRepo):
    def __init__(self, tel: interface.ITelemetry, db: interface.IDB):
        self.db = db
        self.tracer = tel.tracer()

    async def create_account(self, account_id: int) -> None:
        with self.tracer.start_as_current_span(
                "AccountRepo.create_account",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                }
        ) as span:
            try:
                args = {
                    'account_id': account_id,
                }
                await self.db.insert(create_account, args)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def account_by_id(self, account_id: int) -> list[model.Account]:
        with self.tracer.start_as_current_span(
                "AccountRepo.account_by_id",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                }
        ) as span:
            try:
                args = {'account_id': account_id}
                rows = await self.db.select(account_by_id, args)
                accounts = model.Account.serialize(rows) if rows else []

                span.set_status(Status(StatusCode.OK))
                return accounts
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def account_by_refresh_token(self, refresh_token: str) -> list[model.Account]:
        with self.tracer.start_as_current_span(
                "AccountRepo.account_by_refresh_token",
                kind=SpanKind.INTERNAL,
                attributes={
                    "refresh_token_length": len(refresh_token) if refresh_token else 0,
                }
        ) as span:
            try:
                args = {'refresh_token': refresh_token}
                rows = await self.db.select(account_by_refresh_token, args)
                accounts = model.Account.serialize(rows) if rows else []

                span.set_status(Status(StatusCode.OK))
                return accounts
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def update_refresh_token(self, account_id: int, refresh_token: str) -> None:
        with self.tracer.start_as_current_span(
                "AccountRepo.update_refresh_token",
                kind=SpanKind.INTERNAL,
                attributes={
                    "account_id": account_id,
                    "refresh_token_length": len(refresh_token) if refresh_token else 0,
                }
        ) as span:
            try:
                args = {
                    'account_id': account_id,
                    'refresh_token': refresh_token,
                }
                await self.db.update(update_refresh_token, args)

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err