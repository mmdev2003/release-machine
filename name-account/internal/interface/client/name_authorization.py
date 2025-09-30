from abc import abstractmethod
from typing import Protocol

from internal import model


class INameAuthorizationClient(Protocol):
    @abstractmethod
    async def authorization(
            self,
            account_id: int,
            two_fa_status: bool,
            role: str
    ) -> model.JWTTokens: pass

    @abstractmethod
    async def authorization_tg(
            self,
            account_id: int,
            two_fa_status: bool,
            role: str
    ) -> model.JWTTokens: pass

    @abstractmethod
    async def check_authorization(self, access_token: str) -> model.AuthorizationData: pass