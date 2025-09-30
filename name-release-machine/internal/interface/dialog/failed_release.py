from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery


class IFailedReleasesDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_view_failed_releases_window(self) -> Window:
        pass


class IFailedReleasesService(Protocol):
    @abstractmethod
    async def handle_refresh(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_navigate_release(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_back_to_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IFailedReleasesGetter(Protocol):
    @abstractmethod
    async def get_releases_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

