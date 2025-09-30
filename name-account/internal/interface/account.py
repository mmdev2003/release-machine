import io
from abc import abstractmethod
from typing import Protocol
from fastapi import Request

from internal import model
from internal.controller.http.handler.account.model import (
    RegisterBody, LoginBody, SetTwoFaBody, DeleteTwoFaBody,
    VerifyTwoFaBody, RecoveryPasswordBody, ChangePasswordBody
)


class IAccountController(Protocol):
    @abstractmethod
    async def register(self, body: RegisterBody): pass

    @abstractmethod
    async def register_from_tg(self, body: RegisterBody): pass

    @abstractmethod
    async def login(self, body: LoginBody): pass

    @abstractmethod
    async def generate_two_fa(self, request: Request): pass

    @abstractmethod
    async def set_two_fa(self, request: Request, body: SetTwoFaBody): pass

    @abstractmethod
    async def delete_two_fa(self, request: Request, body: DeleteTwoFaBody): pass

    @abstractmethod
    async def verify_two_fa(self, request: Request, body: VerifyTwoFaBody): pass

    @abstractmethod
    async def recovery_password(self, request: Request, body: RecoveryPasswordBody): pass

    @abstractmethod
    async def change_password(self, request: Request, body: ChangePasswordBody): pass


class IAccountService(Protocol):
    @abstractmethod
    async def register(self, login: str, password: str) -> model.AuthorizationDataDTO: pass

    @abstractmethod
    async def register_from_tg(self, login: str, password: str) -> model.AuthorizationDataDTO: pass


    @abstractmethod
    async def login(
            self,
            login: str,
            password: str,
    ) -> model.AuthorizationDataDTO | None: pass

    @abstractmethod
    async def generate_two_fa_key(self, account_id: int) -> tuple[str, io.BytesIO]: pass

    @abstractmethod
    async def set_two_fa_key(self, account_id: int, google_two_fa_key: str, google_two_fa_code: str) -> None: pass

    @abstractmethod
    async def delete_two_fa_key(self, account_id: int, google_two_fa_code: str) -> None: pass

    @abstractmethod
    async def verify_two(self, account_id: int, google_two_fa_code: str) -> bool: pass

    @abstractmethod
    async def recovery_password(self, account_id: int, new_password: str) -> None: pass

    @abstractmethod
    async def change_password(self, account_id: int, new_password: str, old_password: str) -> None: pass


class IAccountRepo(Protocol):
    @abstractmethod
    async def create_account(self, login: str, password: str) -> int: pass

    @abstractmethod
    async def account_by_id(self, account_id: int) -> list[model.Account]: pass

    @abstractmethod
    async def account_by_login(self, login: str) -> list[model.Account]: pass

    @abstractmethod
    async def set_two_fa_key(self, account_id: int, google_two_fa_key: str) -> None: pass

    @abstractmethod
    async def delete_two_fa_key(self, account_id: int) -> None: pass

    @abstractmethod
    async def update_password(self, account_id: int, new_password: str) -> None: pass