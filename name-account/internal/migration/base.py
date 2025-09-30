from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MigrationInfo:
    version: str
    name: str
    depends_on: str = None


class Migration(ABC):
    def __init__(self):
        self.info = self.get_info()

    @abstractmethod
    def get_info(self) -> MigrationInfo:
        pass

    @abstractmethod
    async def up(self, db) -> None:
        pass

    @abstractmethod
    async def down(self, db) -> None:
        pass