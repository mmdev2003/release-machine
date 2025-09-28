from abc import abstractmethod
from typing import Protocol

from fastapi.responses import JSONResponse

from internal.controller.http.handler.release.model import *


class IReleaseController(Protocol):
    @abstractmethod
    async def create_release(self, body: CreateReleaseBody) -> JSONResponse:
        pass

    @abstractmethod
    async def update_release(self, body: UpdateReleaseBody) -> JSONResponse:
        pass


class IReleaseService(Protocol):
    @abstractmethod
    async def create_release(
            self,
            service_name: str,
            release_tag: str,
            initiated_by: str,
            github_run_id: str,
            github_action_link: str,
            github_ref: str
    ) -> int:
        pass

    @abstractmethod
    async def update_release(
            self,
            release_id: int,
            status: model.ReleaseStatus = None,
            github_run_id: str = None,
            github_action_link: str = None,
            rollback_to_tag: str = None,
    ) -> None:
        pass

    @abstractmethod
    async def get_active_release(self) -> list[model.Release]: pass

    @abstractmethod
    async def get_successful_releases(self) -> list[model.Release]: pass

    @abstractmethod
    async def get_failed_releases(self) -> list[model.Release]: pass

    @abstractmethod
    async def rollback_to_tag(
            self,
            release_id: int,
            service_name: str,
            target_tag: str,
    ): pass


class IReleaseRepo(Protocol):
    @abstractmethod
    async def create_release(
            self,
            service_name: str,
            release_tag: str,
            status: model.ReleaseStatus,
            initiated_by: str,
            github_run_id: str,
            github_action_link: str,
            github_ref: str
    ) -> int:
        pass

    @abstractmethod
    async def update_release(
            self,
            release_id: int,
            status: model.ReleaseStatus = None,
            github_run_id: str = None,
            github_action_link: str = None,
            rollback_to_tag: str = None,
    ) -> None:
        pass

    @abstractmethod
    async def get_active_release(self) -> list[model.Release]: pass

    @abstractmethod
    async def get_successful_releases(self) -> list[model.Release]: pass

    @abstractmethod
    async def get_failed_releases(self) -> list[model.Release]: pass