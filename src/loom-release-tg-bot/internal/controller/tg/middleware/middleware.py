import time
import traceback

from aiogram import Bot
from typing import Callable, Any, Awaitable
from aiogram.types import TelegramObject, Update
from aiogram.exceptions import TelegramBadRequest
from opentelemetry.trace import SpanKind, Status, StatusCode

from internal import interface, common


class TgMiddleware(interface.ITelegramMiddleware):
    def __init__(
            self,
            tel: interface.ITelemetry,
            bot: Bot,
    ):
        self.tracer = tel.tracer()
        self.meter = tel.meter()
        self.logger = tel.logger()

        self.bot = bot

        self.ok_message_counter = self.meter.create_counter(
            name=common.OK_MESSAGE_TOTAL_METRIC,
            description="Total count of 200 messages",
            unit="1"
        )

        self.error_message_counter = self.meter.create_counter(
            name=common.ERROR_MESSAGE_TOTAL_METRIC,
            description="Total count of 500 messages",
            unit="1"
        )

        self.message_duration = self.meter.create_histogram(
            name=common.REQUEST_DURATION_METRIC,
            description="Message duration in seconds",
            unit="s"
        )

        self.active_messages = self.meter.create_up_down_counter(
            name=common.ACTIVE_REQUESTS_METRIC,
            description="Number of active messages",
            unit="1"
        )

    async def trace_middleware01(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: dict[str, Any]
    ):
        message, event_type, message_text, tg_username, tg_chat_id, message_id = self.__extract_metadata(event)

        callback_query_data = event.callback_query.data if event.callback_query is not None else ""

        with self.tracer.start_as_current_span(
                "TgMiddleware.trace_middleware01",
                kind=SpanKind.INTERNAL,
                attributes={
                    common.TELEGRAM_EVENT_TYPE_KEY: event_type,
                    common.TELEGRAM_CHAT_ID_KEY: tg_chat_id,
                    common.TELEGRAM_USER_USERNAME_KEY: tg_username,
                    common.TELEGRAM_USER_MESSAGE_KEY: message_text,
                    common.TELEGRAM_MESSAGE_ID_KEY: message_id,
                    common.TELEGRAM_CALLBACK_QUERY_DATA_KEY: callback_query_data,
                }
        ) as root_span:
            span_ctx = root_span.get_span_context()
            trace_id = format(span_ctx.trace_id, '032x')
            span_id = format(span_ctx.span_id, '016x')

            data["trace_id"] = trace_id
            data["span_id"] = span_id
            try:
                await handler(event, data)

                root_span.set_status(Status(StatusCode.OK))
            except Exception as err:
                root_span.record_exception(err)
                root_span.set_status(Status(StatusCode.ERROR, str(err)))

                # При критической ошибке пытаемся восстановить пользователя
                await self._recovery_start_functionality(tg_chat_id, tg_username)
                raise err

    async def metric_middleware02(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: dict[str, Any]
    ):
        with self.tracer.start_as_current_span(
                "TgMiddleware.metric_middleware02",
                kind=SpanKind.INTERNAL
        ) as span:
            start_time = time.time()
            self.active_messages.add(1)

            message, event_type, message_text, tg_username, tg_chat_id, message_id = self.__extract_metadata(event)

            callback_query_data = event.callback_query.data if event.callback_query is not None else ""

            request_attrs: dict = {
                common.TELEGRAM_EVENT_TYPE_KEY: event_type,
                common.TELEGRAM_CHAT_ID_KEY: tg_chat_id,
                common.TELEGRAM_USER_USERNAME_KEY: tg_username,
                common.TELEGRAM_USER_MESSAGE_KEY: message_text,
                common.TELEGRAM_MESSAGE_ID_KEY: message_id,
                common.TELEGRAM_CALLBACK_QUERY_DATA_KEY: callback_query_data,
                common.TRACE_ID_KEY: data["trace_id"],
                common.SPAN_ID_KEY: data["span_id"],
            }

            try:
                await handler(event, data)

                duration_seconds = time.time() - start_time

                request_attrs[common.HTTP_REQUEST_DURATION_KEY] = duration_seconds

                self.ok_message_counter.add(1, attributes=request_attrs)
                self.message_duration.record(duration_seconds, attributes=request_attrs)
                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                duration_seconds = time.time() - start_time
                request_attrs[common.TELEGRAM_MESSAGE_DURATION_KEY] = 500
                request_attrs[common.ERROR_KEY] = str(err)

                self.error_message_counter.add(1, attributes=request_attrs)
                self.message_duration.record(duration_seconds, attributes=request_attrs)

                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))

                raise err
            finally:
                self.active_messages.add(-1)

    async def logger_middleware03(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: dict[str, Any]
    ):
        with self.tracer.start_as_current_span(
                "TgMiddleware.logger_middleware03",
                kind=SpanKind.INTERNAL
        ) as span:
            start_time = time.time()

            message, event_type, message_text, tg_username, tg_chat_id, message_id = self.__extract_metadata(event)

            callback_query_data = event.callback_query.data if event.callback_query is not None else ""

            extra_log: dict = {
                common.TELEGRAM_EVENT_TYPE_KEY: event_type,
                common.TELEGRAM_CHAT_ID_KEY: tg_chat_id,
                common.TELEGRAM_USER_USERNAME_KEY: tg_username,
                common.TELEGRAM_USER_MESSAGE_KEY: message_text,
                common.TELEGRAM_MESSAGE_ID_KEY: message_id,
                common.TELEGRAM_CALLBACK_QUERY_DATA_KEY: callback_query_data,
                common.TRACE_ID_KEY: data["trace_id"],
                common.SPAN_ID_KEY: data["span_id"],
            }
            try:
                self.logger.info(f"Начали обработку telegram {event_type}", extra_log)

                del data["trace_id"], data["span_id"]
                await handler(event, data)

                extra_log = {
                    **extra_log,
                    common.TELEGRAM_MESSAGE_DURATION_KEY: int((time.time() - start_time) * 1000),
                }
                self.logger.info(f"Закончили обработку telegram {event_type}", extra_log)

                span.set_status(Status(StatusCode.OK))
            except TelegramBadRequest as err:
                self.logger.warning(
                    "TelegramBadRequest в dialog middleware",
                    {
                        common.ERROR_KEY: str(err),
                        common.TELEGRAM_CHAT_ID_KEY: self._get_chat_id(event),
                    }
                )
                pass

            except Exception as err:
                extra_log = {
                    **extra_log,
                    common.TELEGRAM_MESSAGE_DURATION_KEY: int((time.time() - start_time) * 1000),
                    common.TRACEBACK_KEY: traceback.format_exc()
                }
                self.logger.error(f"Ошибка обработки telegram {event_type}: {str(err)}", extra_log)

                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise err

    async def _recovery_start_functionality(self, tg_chat_id: int, tg_username: str):
        with self.tracer.start_as_current_span(
                "TgMiddleware._recovery_start_functionality",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info(
                    f"Начинаем восстановление пользователя через функционал /start",
                    {common.TELEGRAM_CHAT_ID_KEY: tg_chat_id}
                )

                span.set_status(Status(StatusCode.OK))

            except Exception as recovery_err:
                self.logger.error(
                    f"Критическая ошибка при восстановлении пользователя {tg_chat_id}",
                    {
                        common.ERROR_KEY: str(recovery_err),
                        common.TRACEBACK_KEY: traceback.format_exc(),
                        common.TELEGRAM_CHAT_ID_KEY: tg_chat_id,
                    }
                )

                span.record_exception(recovery_err)
                span.set_status(Status(StatusCode.ERROR, str(recovery_err)))

                # Последняя попытка - отправить пользователю сообщение с инструкцией
                try:
                    await self.bot.send_message(
                        chat_id=tg_chat_id,
                        text="❌ Произошла критическая ошибка. Пожалуйста, отправьте команду /start для восстановления работы."
                    )
                except Exception as msg_err:
                    self.logger.error(
                        f"Не удалось отправить сообщение о восстановлении пользователю {tg_chat_id}",
                        {
                            common.ERROR_KEY: str(msg_err),
                            common.TELEGRAM_CHAT_ID_KEY: tg_chat_id,
                        }
                    )

    def __extract_metadata(self, event: Update):
        message = event.message if event.message is not None else event.callback_query.message
        event_type = "message" if event.message is not None else "callback_query"

        if event_type == "message":
            tg_username = message.from_user.username
        else:
            tg_username = event.callback_query.from_user.username

        tg_username = tg_username if tg_username is not None else ""
        tg_chat_id = message.chat.id
        if message.text is not None:
            message_text = message.text
        else:
            message_text = "Изображение"

        message_id = message.message_id
        return message, event_type, message_text, tg_username, tg_chat_id, message_id

    def _get_chat_id(self, event: Update) -> int:
        if event.message:
            return event.message.chat.id
        elif event.callback_query and event.callback_query.message:
            return event.callback_query.message.chat.id
        return 0