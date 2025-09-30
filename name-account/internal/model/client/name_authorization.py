from dataclasses import dataclass

from pydantic import BaseModel

@dataclass
class AuthorizationDataDTO:
    account_id: int
    access_token: str
    refresh_token: str


class AuthorizationData(BaseModel):
    account_id: int
    message: str
    code: int


class JWTTokens(BaseModel):
    access_token: str
    refresh_token: str
