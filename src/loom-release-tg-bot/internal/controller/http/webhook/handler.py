import traceback
from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import Header
from opentelemetry.trace import Status, StatusCode, SpanKind

from internal import interface, common


class TelegramWebhookController(interface.ITelegramWebhookController):
    def __init__(
            self,
            tel: interface.ITelemetry,
            dp: Dispatcher,
            bot: Bot,
            domain: str,
            prefix: str,
    ):
        self.tracer = tel.tracer()
        self.logger = tel.logger()

        self.dp = dp
        self.bot = bot

        self.domain = domain
        self.prefix = prefix

    async def bot_webhook(
            self,
            update: dict,
            x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None
    ):
        with self.tracer.start_as_current_span(
                "TelegramWebhookController.bot_webhook",
                kind=SpanKind.INTERNAL
        ) as span:
            if x_telegram_bot_api_secret_token != "secret":
                return {"status": "error", "message": "Wrong secret token !"}

            telegram_update = Update(**update)
            try:
                await self.dp.feed_webhook_update(
                    bot=self.bot,
                    update=telegram_update)

                span.set_status(Status(StatusCode.OK))
                return None
            except Exception as err:
                try:
                    self.logger.error("Ошибка", {"traceback": traceback.format_exc()})
                    chat_id = self._get_chat_id(telegram_update)

                    if telegram_update.message:
                        tg_username = telegram_update.message.from_user.username
                    elif telegram_update.callback_query and telegram_update.callback_query.message:
                        tg_username = telegram_update.callback_query.message.from_user.username

                    await self._recovery_start_functionality(chat_id, tg_username)
                except Exception as err:
                    raise err

    async def bot_set_webhook(self):
        with self.tracer.start_as_current_span(
                "TelegramWebhookController.bot_set_webhook",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                await self.bot.set_webhook(
                    f'https://{self.domain}{self.prefix}/update',
                    secret_token='secret',
                    allowed_updates=["message", "callback_query"],
                )
                webhook_info = await self.bot.get_webhook_info()

                span.set_status(Status(StatusCode.OK))
            except Exception as err:
                span.record_exception(err)
                span.set_status(Status(StatusCode.ERROR, str(err)))
                raise

    async def _recovery_start_functionality(self, tg_chat_id: int, tg_username: str):
        with self.tracer.start_as_current_span(
                "TelegramWebhookController._recovery_start_functionality",
                kind=SpanKind.INTERNAL
        ) as span:
            try:
                self.logger.info(
                    f"Начинаем восстановление пользователя через функционал /start",
                    {common.TELEGRAM_CHAT_ID_KEY: tg_chat_id}
                )

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
                    raise msg_err

    def _get_chat_id(self, event: Update) -> int:
        if event.message:
            return event.message.chat.id
        elif event.callback_query and event.callback_query.message:
            return event.callback_query.message.chat.id
        return 0