import io
from abc import abstractmethod
from typing import Protocol, Sequence, Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from opentelemetry.metrics import Meter
from opentelemetry.trace import Tracer
from starlette.responses import StreamingResponse

from internal import model


class IOtelLogger(Protocol):
    @abstractmethod
    def debug(self, message: str, fields: dict = None) -> None:
        pass

    @abstractmethod
    def info(self, message: str, fields: dict = None) -> None:
        pass

    @abstractmethod
    def warning(self, message: str, fields: dict = None) -> None:
        pass

    @abstractmethod
    def error(self, message: str, fields: dict = None) -> None:
        pass


class ITelemetry(Protocol):
    @abstractmethod
    def tracer(self) -> Tracer:
        pass

    @abstractmethod
    def meter(self) -> Meter:
        pass

    @abstractmethod
    def logger(self) -> IOtelLogger:
        pass


class IHttpMiddleware(Protocol):
    @abstractmethod
    def trace_middleware01(self, app: FastAPI): pass

    @abstractmethod
    def metrics_middleware02(self, app: FastAPI): pass

    @abstractmethod
    def logger_middleware03(self, app: FastAPI): pass

    @abstractmethod
    def authorization_middleware04(self, app: FastAPI): pass


class IRedis(Protocol):
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool: pass

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any: pass


class IDB(Protocol):

    @abstractmethod
    async def insert(self, query: str, query_params: dict) -> int: pass

    @abstractmethod
    async def delete(self, query: str, query_params: dict) -> None: pass

    @abstractmethod
    async def update(self, query: str, query_params: dict) -> None: pass

    @abstractmethod
    async def select(self, query: str, query_params: dict) -> Sequence[Any]: pass

    @abstractmethod
    async def multi_query(self, queries: list[str]) -> None: pass
