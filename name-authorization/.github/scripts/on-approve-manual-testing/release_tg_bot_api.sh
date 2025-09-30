#!/bin/bash

# ============================================
# Утилиты для работы с API
# ============================================

api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_code=$4

    local response=$(curl -s -w "\n%{http_code}" -X "$method" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    if [ "$http_code" -ne "$expected_code" ]; then
        echo "❌ API запрос завершился с ошибкой" >&2
        echo "   Метод: $method" >&2
        echo "   Endpoint: $endpoint" >&2
        echo "   Ожидался HTTP $expected_code, получен HTTP $http_code" >&2
        echo "   Ответ: $body" >&2
        return 1
    fi

    # Только тело ответа в stdout
    echo "$body"
    return 0
}

# ============================================
# Начало деплоя с обновлением статуса
# ============================================

start_deploy() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              НАЧАЛО PRODUCTION ДЕПЛОЯ                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:      $SERVICE_NAME"
    echo "🏷️  Версия:      $TAG_NAME"
    echo "🆔 Release ID:  $RELEASE_ID"
    echo "🖥️  Сервер:      $PROD_HOST"
    echo "🌐 Домен:       $PROD_DOMAIN"
    echo ""

    if [ -z "$RELEASE_ID" ]; then
        echo "❌ Release ID не установлен"
        echo "   Невозможно начать деплой"
        exit 1
    fi

    local payload=$(echo '{
        "release_id": '"$RELEASE_ID"',
        "status": "deploying",
        "github_run_id": "'"$GITHUB_RUN_ID"'",
        "github_action_link": "'"$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"'"
    }' | tr -d '\n' | sed 's/  */ /g')

    local endpoint="${PROD_DOMAIN}${NAME_RELEASE_TG_BOT_PREFIX}/release"

    echo "─────────────────────────────────────────"
    echo "Обновление статуса на 'deploying'"
    echo "─────────────────────────────────────────"
    echo -n "📡 Отправка запроса... "

    local response=$(curl -s -w "\n%{http_code}" -X PATCH \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 204 ]; then
        echo "✅"
        echo ""
        echo "✅ Статус обновлен на 'deploying'"
        echo "✅ Готовы к началу деплоя"
        echo ""
    else
        echo "❌ HTTP $http_code"
        echo ""
        echo "❌ Не удалось обновить статус релиза"
        echo "   Endpoint: $endpoint"
        echo "   Ответ: $body"
        echo ""
        echo "🚨 Критическая ошибка: невозможно начать деплой без обновления статуса"
        exit 1
    fi
}

# ============================================
# Обновление статуса релиза
# ============================================

update_release_status() {
    local new_status=$1

    echo ""
    echo "─────────────────────────────────────────"
    echo "Обновление статуса релиза"
    echo "─────────────────────────────────────────"

    if [ -z "$RELEASE_ID" ]; then
        echo "⚠️  Release ID не установлен, пропуск обновления"
        echo ""
        return 0
    fi

    echo "🆔 Release ID:   $RELEASE_ID"
    echo "📊 Новый статус: $new_status"

    local payload=$(echo '{
        "release_id": '"$RELEASE_ID"',
        "status": "'"$new_status"'"
    }' | tr -d '\n' | sed 's/  */ /g')

    local endpoint="${PROD_DOMAIN}${NAME_RELEASE_TG_BOT_PREFIX}/release"

    echo -n "📡 Отправка PATCH запроса... "

    local response=$(curl -s -w "\n%{http_code}" -X PATCH \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 204 ]; then
        echo "✅"
        echo ""
    else
        echo "⚠️  HTTP $http_code"
        echo ""
        echo "⚠️  Неожиданный код ответа"
        echo "   Endpoint: $endpoint"
        echo "   Ответ: $body"
        echo ""
        echo "ℹ️  Процесс продолжится несмотря на ошибку обновления статуса"
        echo ""
    fi
}