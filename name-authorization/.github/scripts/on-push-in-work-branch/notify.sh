#!/bin/bash

# ============================================
# Отправка уведомлений в Telegram
# ============================================

send_telegram_notification() {
    local message=$1

    # Проверяем наличие скрипта уведомлений
    if [ ! -f "script/tg_bot_alert.py" ]; then
        echo "⚠️  Скрипт уведомлений не найден: script/tg_bot_alert.py"
        echo "   Пропуск отправки уведомления"
        return 0
    fi

    # Отправляем уведомление
    if python3 script/tg_bot_alert.py "$message" 2>/dev/null; then
        echo "✅ Уведомление отправлено в Telegram"
    else
        echo "⚠️  Не удалось отправить уведомление в Telegram"
    fi
}

# ============================================
# Уведомление об успешном обновлении
# ============================================

send_success_notification() {
    echo ""
    echo "─────────────────────────────────────────"
    echo "Отправка уведомления об успехе"
    echo "─────────────────────────────────────────"

    local message="✅ Ветка обновлена на dev сервере

📦 Сервис: $SERVICE_NAME
🌿 Ветка: $BRANCH_NAME
👤 Автор: $AUTHOR_NAME
🖥️  Сервер: $DEV_HOST
🌐 Домен: $DEV_DOMAIN

Приложение работает корректно!"

    send_telegram_notification "$message"
    echo ""
}

# ============================================
# Уведомление об ошибке
# ============================================

send_failure_notification() {
    echo ""
    echo "─────────────────────────────────────────"
    echo "Отправка уведомления об ошибке"
    echo "─────────────────────────────────────────"

    local action_url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"

    local message="❌ Ошибка обновления ветки на dev сервере

📦 Сервис: $SERVICE_NAME
🌿 Ветка: $BRANCH_NAME
👤 Автор: $AUTHOR_NAME
🖥️  Сервер: $DEV_HOST

🔍 Подробности:
$action_url"

    send_telegram_notification "$message"
    echo ""
}
