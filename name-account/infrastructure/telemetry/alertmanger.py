import asyncio
import re
from datetime import datetime

import httpx
import openai
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from infrastructure.redis_client.redis_client import RedisClient


class AlertManager:
    def __init__(
            self,
            tg_bot_token: str,
            service_name: str,
            alert_tg_chat_id: int,
            alert_tg_chat_thread_id: int,
            grafana_url: str,
            monitoring_redis_host: str,
            monitoring_redis_port: int,
            monitoring_redis_db: int,
            monitoring_redis_password: str,
            openai_api_key: str = None,
    ):
        self.bot = Bot(tg_bot_token)
        self.alert_tg_chat_id = alert_tg_chat_id
        self.alert_tg_chat_thread_id = alert_tg_chat_thread_id
        self.grafana_url = grafana_url
        self.service_name = service_name
        self.redis_client = RedisClient(
            monitoring_redis_host,
            monitoring_redis_port,
            monitoring_redis_db,
            monitoring_redis_password
        )
        if openai_api_key:
            self.openai_client = openai.AsyncOpenAI(
                api_key=openai_api_key,
                http_client=httpx.AsyncClient(proxy="http://32uLYMeQ:jLaDv4WK@193.160.72.227:62940")
            )
        else:
            self.openai_client = None

    def send_error_alert(self, trace_id: str, span_id: str, traceback: str):
        loop = asyncio.get_running_loop()
        loop.create_task(self.__send_error_alert(trace_id, span_id, traceback))

    async def __send_error_alert(self, trace_id: str, span_id: str, traceback: str):
        alert_send = await self.redis_client.get(trace_id)
        if alert_send:
            return

        await self.redis_client.set(trace_id, "1", ttl=30)
        await self.__send_error_alert_to_tg(trace_id, span_id, traceback)

    def _format_telegram_text(self, text: str) -> str:
        # Экранируем специальные символы HTML
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')

        # Возвращаем обратно наши теги форматирования
        text = text.replace('&lt;b&gt;', '<b>')
        text = text.replace('&lt;/b&gt;', '</b>')
        text = text.replace('&lt;i&gt;', '<i>')
        text = text.replace('&lt;/i&gt;', '</i>')
        text = text.replace('&lt;code&gt;', '<code>')
        text = text.replace('&lt;/code&gt;', '</code>')
        text = text.replace('&lt;pre&gt;', '<pre>')
        text = text.replace('&lt;/pre&gt;', '</pre>')

        return text
    async def __send_error_alert_to_tg(self, trace_id: str, span_id: str, traceback: str):
        log_link = f"{self.grafana_url}/explore?schemaVersion=1&panes=%7B%220pz%22:%7B%22datasource%22:%22loki%22,%22queries%22:%5B%7B%22refId%22:%22A%22,%22expr%22:%22%7Bservice_name%3D~%5C%22.%2B%5C%22%7D%20%7C%20trace_id%3D%60{trace_id}%60%20%7C%3D%20%60%60%22,%22queryType%22:%22range%22,%22datasource%22:%7B%22type%22:%22loki%22,%22uid%22:%22loki%22%7D,%22editorMode%22:%22code%22,%22direction%22:%22backward%22%7D%5D,%22range%22:%7B%22from%22:%22now-2d%22,%22to%22:%22now%22%7D%7D%7D&orgId=1"
        trace_link = f"{self.grafana_url}/explore?schemaVersion=1&panes=%7B%220pz%22:%7B%22datasource%22:%22tempo%22,%22queries%22:%5B%7B%22refId%22:%22A%22,%22datasource%22:%7B%22type%22:%22tempo%22,%22uid%22:%22tempo%22%7D,%22queryType%22:%22traceql%22,%22limit%22:20,%22tableType%22:%22traces%22,%22metricsQueryType%22:%22range%22,%22query%22:%22{trace_id}%22%7D%5D,%22range%22:%7B%22from%22:%22now-2d%22,%22to%22:%22now%22%7D%7D%7D&orgId=1"

        # Текущее время для алерта
        current_time = datetime.now().strftime("%H:%M:%S")

        # Основная информация об ошибке
        text = f"""🚨 <b>Ошибка в сервисе</b>

<b>Сервис:</b> <code>{self.service_name}</code>
<b>Время:</b> <code>{current_time}</code>
<b>TraceID:</b> <code>{trace_id}</code>
<b>SpanID:</b> <code>{span_id}</code>"""

        # Добавляем анализ LLM если доступен
        if self.openai_client is not None:
            try:
                llm_analysis = await self.generate_analysis(traceback)
                if llm_analysis:
                    text += f"\n\n{llm_analysis}"
            except Exception as e:
                print(f"Ошибка при генерации анализа LLM: {e}", flush=True)
                text += f"\n\n<i>⚠️ Анализ LLM временно недоступен</i>"

        # Форматируем текст для Telegram
        text = self._format_telegram_text(text)

        # Кнопки для навигации
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Логи", url=log_link),
                InlineKeyboardButton(text="🔍 Трейс", url=trace_link)
            ]
        ])

        try:
            await self.bot.send_message(
                self.alert_tg_chat_id,
                text,
                message_thread_id=self.alert_tg_chat_thread_id,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Ошибка при отправке сообщения в Telegram: {e}", flush=True)

            simple_text = f"🚨 Ошибка в сервисе {self.service_name}\nTraceID: {trace_id}"
            await self.bot.send_message(
                self.alert_tg_chat_id,
                simple_text,
                message_thread_id=self.alert_tg_chat_thread_id,
                reply_markup=keyboard
            )

    async def generate_analysis(self, traceback: str) -> str:
        try:
            system_prompt = """Ты опытный Python-разработчик и специалист по мониторингу.
Проанализируй stacktrace и дай краткий, но информативный анализ для команды разработки.

Формат ответа должен быть оптимизирован для Telegram (HTML разметка):
- Используй <b></b> для выделения важных частей
- Используй <code></code> для кода и названий файлов/методов
- Используй <i></i> для дополнительных пояснений
- Максимум 300-400 символов
- Структура: проблема → причина → решение

НЕ ПИШИ:
- Длинные объяснения
- Очевидные вещи
- "Данная ошибка", "В данном случае"
- Повторения информации из самого traceback

ПИШИ:
- Конкретно и по делу
- Практичные советы
- Возможные причины
- Быстрые способы исправления"""

            # Формируем сообщение пользователя с контекстом
            user_message = f"""Stacktrace:
{traceback}

Дополнительный контекст:
- Сервис: {self.service_name}
- Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            history = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=history,
                temperature=0.2,
            )

            llm_response = response.choices[0].message.content

            if llm_response:
                # Добавляем заголовок с эмодзи
                formatted_response = f"🤖 <b>Анализ ошибки:</b>\n{llm_response.strip()}"
                return formatted_response
            else:
                return ""

        except Exception as err:
            print(f"Ошибка при генерации анализа: {err}", flush=True)
            return ""