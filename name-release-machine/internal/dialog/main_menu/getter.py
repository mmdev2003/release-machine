from aiogram_dialog import DialogManager
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface


class MainMenuGetter(interface.IMainMenuGetter):
    def __init__(
            self,
            tel: interface.ITelemetry,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

    async def get_main_menu_data(
            self,
            dialog_manager: DialogManager,
            **kwargs
    ) -> dict:
        with self.tracer.start_as_current_span(
                "MainMenuGetter.get_main_menu_data",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                user = dialog_manager.event.from_user

                data = {
                    "name": user.first_name or "Пользователь",
                }

                span.set_status(Status(StatusCode.OK))
                return data

            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err