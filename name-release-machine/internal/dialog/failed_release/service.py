from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class FailedReleasesService(interface.IFailedReleasesService):
    def __init__(
            self,
            tel: interface.ITelemetry,
            release_service: interface.IReleaseService,
            admins: list[str],
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()
        self.release_service = release_service
        self.admins = admins

    async def handle_navigate_release(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка навигации между релизами"""
        with self.tracer.start_as_current_span(
                "FailedReleasesService.handle_navigate_release",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                current_index = dialog_manager.dialog_data.get("current_index", 0)
                releases_list = dialog_manager.dialog_data.get("releases_list", [])

                # Определяем направление навигации
                if button.widget_id == "prev_release":
                    new_index = max(0, current_index - 1)
                else:  # next_release
                    new_index = min(len(releases_list) - 1, current_index + 1)

                if new_index == current_index:
                    await callback.answer()
                    return

                # Обновляем индекс
                dialog_manager.dialog_data["current_index"] = new_index

                self.logger.info("Навигация по провальным релизам")

                await callback.answer()
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка навигации", show_alert=True)
                raise err

    async def handle_refresh(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка обновления списка релизов"""
        with self.tracer.start_as_current_span(
                "FailedReleasesService.handle_refresh",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Сбрасываем индекс к первому релизу
                dialog_manager.dialog_data["current_index"] = 0

                # Очищаем кешированные данные
                dialog_manager.dialog_data.pop("releases_list", None)

                await callback.answer("✅ Данные обновлены")

                self.logger.info("Обновление списка провальных релизов")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка при обновлении", show_alert=True)
                raise err

    async def handle_back_to_menu(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        """Обработка возврата в главное меню"""
        with self.tracer.start_as_current_span(
                "FailedReleasesService.handle_back_to_menu",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                dialog_manager.show_mode = ShowMode.EDIT

                # Очищаем данные диалога
                dialog_manager.dialog_data.clear()

                await dialog_manager.start(model.MainMenuStates.main_menu)

                self.logger.info("Возврат в главное меню из провальных релизов")
                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("❌ Ошибка", show_alert=True)
                raise err