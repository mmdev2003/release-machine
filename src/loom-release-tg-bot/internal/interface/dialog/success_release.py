from abc import abstractmethod
from typing import Protocol, Any
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram.types import CallbackQuery


class ISuccessfulReleasesDialog(Protocol):
    @abstractmethod
    def get_dialog(self) -> Dialog:
        pass

    @abstractmethod
    def get_view_successful_releases_window(self) -> Window:
        pass

    @abstractmethod
    def get_select_rollback_tag_window(self) -> Window:
        pass

    @abstractmethod
    def get_confirm_rollback_window(self) -> Window:
        pass


class ISuccessfulReleasesService(Protocol):
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

    @abstractmethod
    async def handle_rollback_click(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass

    @abstractmethod
    async def handle_tag_selected(
            self,
            callback: CallbackQuery,
            widget: Any,
            dialog_manager: DialogManager,
            item_id: str
    ) -> None:
        pass

    @abstractmethod
    async def handle_confirm_rollback(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        pass


class ISuccessfulReleasesGetter(Protocol):
    @abstractmethod
    async def get_releases_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_rollback_tags_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass

    @abstractmethod
    async def get_rollback_confirm_data(
            self,
            dialog_manager: DialogManager,
    ) -> dict:
        pass