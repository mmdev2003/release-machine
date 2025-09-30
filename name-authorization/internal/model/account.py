from dataclasses import dataclass
from datetime import datetime


@dataclass
class Account:
    id: int

    account_id: int
    refresh_token: str

    created_at: datetime

    @classmethod
    def serialize(cls, rows):
        return [
            cls(
                id=row.id,
                account_id=row.account_id,
                refresh_token=row.refresh_token,
                created_at=row.created_at,
            ) for row in rows
        ]


@dataclass
class JWTToken:
    access_token: str
    refresh_token: str


@dataclass
class TokenPayload:
    account_id: int
    two_fa_status: bool
    role: str
    exp: int
