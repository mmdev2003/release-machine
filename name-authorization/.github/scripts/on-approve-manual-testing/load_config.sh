#!/bin/bash

# ============================================
# Валидация конфигурации
# ============================================

validate_env_var() {
    local var_name=$1
    local var_value=$2
    local error_message=$3

    if [ -z "$var_value" ]; then
        echo "❌ Ошибка конфигурации: $error_message"
        echo "   Отсутствует переменная: $var_name"
        exit 1
    fi
}

export_to_github_env() {
    local var_name=$1
    local var_value=$2
    echo "$var_name=$var_value" >> $GITHUB_ENV
}

# ============================================
# Основной загрузчик конфигурации
# ============================================

load_server_config() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ЗАГРУЗКА КОНФИГУРАЦИИ                         ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    local config_file="/root/.env.runner"

    # Проверка существования файла конфигурации
    if [ ! -f "$config_file" ]; then
        echo "❌ Файл конфигурации не найден: $config_file"
        exit 1
    fi

    echo "📄 Файл: $config_file"

    # Загрузка переменных окружения из файла конфигурации
    set -a
    source "$config_file"
    set +a

    echo "✅ Переменные загружены"
    echo ""
    echo "─────────────────────────────────────────"
    echo "Валидация обязательных переменных"
    echo "─────────────────────────────────────────"

    # Валидация требуемой конфигурации для production
    validate_env_var "PROD_DOMAIN" "$PROD_DOMAIN" "PROD_DOMAIN не настроен"
    validate_env_var "PROD_HOST" "$PROD_HOST" "PROD_HOST не настроен"
    validate_env_var "PROD_PASSWORD" "$PROD_PASSWORD" "PROD_PASSWORD не настроен"
    validate_env_var "NAME_RELEASE_TG_BOT_PREFIX" "$NAME_RELEASE_TG_BOT_PREFIX" "NAME_RELEASE_TG_BOT_PREFIX не настроен"

    echo "✅ Все обязательные переменные присутствуют"

    # Извлечение и построение префикса сервиса
    SERVICE_PREFIX=$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
    SERVICE_PREFIX_VAR_NAME="${SERVICE_PREFIX}_PREFIX"
    SERVICE_PREFIX="${!SERVICE_PREFIX_VAR_NAME}"

    # Проверка что префикс сервиса найден
    if [ -z "$SERVICE_PREFIX" ]; then
        echo "⚠️  Префикс для сервиса $SERVICE_NAME не найден в конфигурации"
        echo "   Ищется переменная: $SERVICE_PREFIX_VAR_NAME"
    fi

    echo ""
    echo "─────────────────────────────────────────"
    echo "Экспорт в окружение GitHub Actions"
    echo "─────────────────────────────────────────"

    # Экспорт основной конфигурации production
    export_to_github_env "SERVICE_PREFIX" "$SERVICE_PREFIX"
    export_to_github_env "PROD_HOST" "$PROD_HOST"
    export_to_github_env "PROD_PASSWORD" "$PROD_PASSWORD"
    export_to_github_env "PROD_DOMAIN" "$PROD_DOMAIN"

    # Экспорт конфигурации API
    export_to_github_env "NAME_RELEASE_TG_BOT_PREFIX" "$NAME_RELEASE_TG_BOT_PREFIX"

    # Экспорт префиксов сервисов (для возможного использования)
    export_to_github_env "NAME_TG_BOT_PREFIX" "$NAME_TG_BOT_PREFIX"
    export_to_github_env "NAME_ACCOUNT_PREFIX" "$NAME_ACCOUNT_PREFIX"
    export_to_github_env "NAME_AUTHORIZATION_PREFIX" "$NAME_AUTHORIZATION_PREFIX"
    export_to_github_env "NAME_EMPLOYEE_PREFIX" "$NAME_EMPLOYEE_PREFIX"
    export_to_github_env "NAME_ORGANIZATION_PREFIX" "$NAME_ORGANIZATION_PREFIX"
    export_to_github_env "NAME_CONTENT_PREFIX" "$NAME_CONTENT_PREFIX"

    echo "✅ Переменные экспортированы"

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              КОНФИГУРАЦИЯ ЗАГРУЖЕНА                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:             $SERVICE_NAME"
    echo "🔧 Префикс:            $SERVICE_PREFIX"
    echo "🖥️  Production хост:    $PROD_HOST"
    echo "🌐 Production домен:   $PROD_DOMAIN"
    echo "🏷️  Версия для деплоя:  $TAG_NAME"
    echo "🆔 Release ID:         $RELEASE_ID"
    echo ""
}