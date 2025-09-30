from abc import abstractmethod
from typing import Protocol
from fastapi import Request

from internal.controller.http.handler.account.model import *

from internal import model


class IAuthorizationController(Protocol):
    @abstractmethod
    async def authorization(self, body: AuthorizationBody): pass

    @abstractmethod
    async def authorization_tg(self, body: AuthorizationBody): pass

    @abstractmethod
    async def check_authorization(self, request: Request): pass

    @abstractmethod
    async def refresh_token(self, request: Request): pass

    @abstractmethod
    async def refresh_token_tg(self, request: Request): pass


class IAuthorizationService(Protocol):
    @abstractmethod
    async def create_tokens(
            self,
            account_id: int,
            two_fa_status: bool,
            role: str,
    ) -> model.JWTToken: pass

    @abstractmethod
    async def create_tokens_tg(
            self,
            account_id: int,
            two_fa_status: bool,
            role: str,
    ) -> model.JWTToken: pass

    @abstractmethod
    async def check_token(self, token: str) -> model.TokenPayload: pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> model.JWTToken: pass

    @abstractmethod
    async def refresh_token_tg(self, refresh_token: str) -> model.JWTToken: pass


class IAuthorizationRepo(Protocol):
    @abstractmethod
    async def create_account(self, account_id: int) -> None: pass

    @abstractmethod
    async def account_by_id(self, account_id: int) -> list[model.Account]: pass

    @abstractmethod
    async def account_by_refresh_token(self, refresh_token: str) -> list[model.Account]: pass

    @abstractmethod
    async def update_refresh_token(self, account_id: int, refresh_token: str) -> None: pass
