from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, model


class MainMenuService(interface.IMainMenuService):
    def __init__(
            self,
            tel: interface.ITelemetry,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

    async def handle_go_to_active_releases(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuService.handle_go_to_active_releases",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.ActiveReleaseStates.view_releases,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Переход к активным релизам")

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Ошибка при переходе к активным релизам", show_alert=True)
                raise err

    async def handle_go_to_successful_releases(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuService.handle_go_to_successful_releases",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.SuccessfulReleasesStates.view_releases,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Переход к успешным релизам")

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Ошибка при переходе к успешным релизам", show_alert=True)
                raise err

    async def handle_go_to_failed_releases(
            self,
            callback: CallbackQuery,
            button: Any,
            dialog_manager: DialogManager
    ) -> None:
        with self.tracer.start_as_current_span(
                "MainMenuService.handle_go_to_failed_releases",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await dialog_manager.start(
                    model.FailedReleasesStates.view_releases,
                    mode=StartMode.RESET_STACK
                )

                self.logger.info("Переход к провальным релизам")

                span.set_status(Status(StatusCode.OK))

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                await callback.answer("Ошибка при переходе к провальным релизам", show_alert=True)
                raise err