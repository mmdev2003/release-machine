#!/usr/bin/env python3
import os
import sys
import requests
import json


def send_telegram_message(text):
    bot_token = os.getenv('NAME_ALERT_TG_BOT_TOKEN')
    tg_chat_id = os.getenv('NAME_ALERT_TG_CHAT_ID')

    # Проверяем наличие необходимых переменных
    if not bot_token:
        print("Ошибка: не найден TELEGRAM_BOT_TOKEN в переменных окружения")
        return False

    if not tg_chat_id:
        print("Ошибка: не найден TELEGRAM_USER_ID в переменных окружения")
        return False

    # URL для отправки сообщения
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Данные для отправки
    data = {
        'chat_id': tg_chat_id,
        'text': text,
        'parse_mode': 'HTML'  # Можно использовать HTML разметку
    }

    try:
        # Отправляем запрос
        response = requests.post(url, json=data)
        response.raise_for_status()

        result = response.json()

        if result.get('ok'):
            print(f"Сообщение успешно отправлено!")
            return True
        else:
            print(f"Ошибка API: {result.get('description', 'Неизвестная ошибка')}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Использование: python telegram_sender.py 'Текст сообщения'")
        print("\nПеред использованием установите переменные окружения:")
        sys.exit(1)

    message_text = sys.argv[1]

    if send_telegram_message(message_text):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()