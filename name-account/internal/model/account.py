from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


@dataclass
class Account:
    id: int

    login: str
    password: str
    google_two_fa_key: str

    created_at: datetime

    @classmethod
    def serialize(cls, rows) -> List['Account']:
        return [
            cls(
                id=row.id,
                login=row.login,
                password=row.password,
                google_two_fa_key=row.google_two_fa_key,
                created_at=row.created_at
            )
            for row in rows
        ]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "login": self.login,
            "password": self.password,
            "google_two_fa_key": self.google_two_fa_key,
            "created_at": self.created_at.isoformat()
        }