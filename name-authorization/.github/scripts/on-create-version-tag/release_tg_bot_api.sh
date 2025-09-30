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
# Управление записями релизов
# ============================================

create_release_record() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║            СОЗДАНИЕ ЗАПИСИ О РЕЛИЗЕ                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:   $SERVICE_NAME"
    echo "🏷️  Версия:   $TAG_NAME"
    echo "👤 Кто:      $GITHUB_ACTOR"
    echo "🔗 Run ID:   $GITHUB_RUN_ID"
    echo ""

    local payload=$(echo '{
        "service_name": "'"$SERVICE_NAME"'",
        "release_tag": "'"$TAG_NAME"'",
        "status": "initiated",
        "initiated_by": "'"$GITHUB_ACTOR"'",
        "github_run_id": "'"$GITHUB_RUN_ID"'",
        "github_action_link": "'"$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"'",
        "github_ref": "'"$GITHUB_REF"'"
    }' | tr -d '\n' | sed 's/  */ /g')

    local endpoint="${PROD_DOMAIN}${NAME_RELEASE_TG_BOT_PREFIX}/release"

    echo -n "📡 Отправка запроса... "
    local response=$(api_request "POST" "$endpoint" "$payload" 201)
    local api_result=$?

    if [ $api_result -ne 0 ]; then
        echo "❌"
        echo ""
        echo "❌ Не удалось создать запись о релизе"
        echo "   Невозможно продолжить без Release ID"
        exit 1
    fi

    echo "✅"

    # Извлечение ID релиза из ответа
    local release_id=$(echo "$response" | grep -o '"release_id":[0-9]*' | sed 's/"release_id"://')

    if [ -z "$release_id" ]; then
        echo ""
        echo "❌ Не удалось извлечь Release ID из ответа"
        echo "   Ответ API: $response"
        exit 1
    fi

    # Экспорт ID релиза в окружение GitHub
    echo "RELEASE_ID=$release_id" >> $GITHUB_ENV

    echo ""
    echo "✅ Release ID: $release_id"
    echo "✅ Начальный статус: initiated"
    echo ""
}

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

    echo "🆔 Release ID: $RELEASE_ID"
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
        echo "ℹ️  Релиз продолжится несмотря на ошибку обновления статуса"
        echo ""
    fi
}