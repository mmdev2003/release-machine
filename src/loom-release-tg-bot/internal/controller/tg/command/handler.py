import traceback

from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from opentelemetry.trace import SpanKind, StatusCode

from internal import model, interface


class CommandController(interface.ICommandController):

    def __init__(
            self,
            tel: interface.ITelemetry,
    ):
        self.logger = tel.logger()
        self.tracer = tel.tracer()

    async def start_handler(
            self,
            message: Message,
            dialog_manager: DialogManager
    ):
        with (self.tracer.start_as_current_span(
                "CommandController.start_handler",
                kind=SpanKind.INTERNAL
        ) as span):
            try:
                await dialog_manager.reset_stack()

                await dialog_manager.start(model.MainMenuStates.main_menu)

                span.set_status(StatusCode.OK)
            except Exception as err:
                span.record_exception(err)
                span.set_status(StatusCode.ERROR, str(err))
                raise err