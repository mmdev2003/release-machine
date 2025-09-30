from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery


class IActiveReleaseDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_view_releases_window(self) -> Window:
        pass

    @abstractmethod
    def get_confirm_dialog_window(self) -> Window:
        pass

    @abstractmethod
    def get_reject_dialog_window(self) -> Window:
        pass


class IActiveReleaseService(Protocol):
    @abstractmethod
    async def handle_refresh(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    async def handle_navigate_release(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    async def handle_back_to_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None: pass

    @abstractmethod
    async def handle_confirm_yes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_reject_yes(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class IActiveReleaseGetter(Protocol):
    @abstractmethod
    async def get_releases_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_confirm_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_reject_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass
