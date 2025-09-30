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
# Загрузчик конфигурации dev сервера
# ============================================

load_dev_server_config() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         ЗАГРУЗКА КОНФИГУРАЦИИ DEV СЕРВЕРА                  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    local config_file="/root/.env.runner"

    # Проверка существования файла конфигурации
    if [ ! -f "$config_file" ]; then
        echo "❌ Файл конфигурации не найден: $config_file"
        exit 1
    fi

    echo "📄 Файл: $config_file"

    # Загрузка переменных окружения
    set -a
    source "$config_file"
    set +a

    echo "✅ Переменные загружены"
    echo ""
    echo "─────────────────────────────────────────"
    echo "Валидация базовых переменных"
    echo "─────────────────────────────────────────"

    # Валидация API конфигурации
    validate_env_var "STAGE_DOMAIN" "$STAGE_DOMAIN" "STAGE_DOMAIN не настроен"
    validate_env_var "PROD_DOMAIN" "$PROD_DOMAIN" "PROD_DOMAIN не настроен"
    validate_env_var "STAGE_HOST" "$STAGE_HOST" "STAGE_HOST не настроен"
    validate_env_var "STAGE_PASSWORD" "$STAGE_PASSWORD" "STAGE_PASSWORD не настроен"

    echo "✅ Базовые переменные присутствуют"

    # Получение префикса сервиса
    SERVICE_PREFIX=$(echo "$SERVICE_NAME" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
    SERVICE_PREFIX_VAR_NAME="${SERVICE_PREFIX}_PREFIX"
    SERVICE_PREFIX="${!SERVICE_PREFIX_VAR_NAME}"

    echo ""
    echo "─────────────────────────────────────────"
    echo "Поиск конфигурации для $AUTHOR_NAME"
    echo "─────────────────────────────────────────"

    # Формируем имена переменных для текущего автора
    DEV_HOST_VAR="${AUTHOR_NAME}_HOST"
    DEV_PASSWORD_VAR="${AUTHOR_NAME}_PASSWORD"
    DEV_DOMAIN_VAR="${AUTHOR_NAME}_DOMAIN"

    # Получаем значения переменных
    DEV_HOST="${!DEV_HOST_VAR}"
    DEV_PASSWORD="${!DEV_PASSWORD_VAR}"
    DEV_DOMAIN="${!DEV_DOMAIN_VAR}"

    # Валидация конфигурации разработчика
    if [ -z "$DEV_HOST" ] || [ -z "$DEV_PASSWORD" ]; then
        echo "❌ Конфигурация для $AUTHOR_NAME не найдена"
        echo "   Требуются переменные:"
        echo "   • ${DEV_HOST_VAR}"
        echo "   • ${DEV_PASSWORD_VAR}"
        echo "   • ${DEV_DOMAIN_VAR} (опционально)"
        exit 1
    fi

    echo "✅ Найдена конфигурация для $AUTHOR_NAME"
    echo "   Сервер: $DEV_HOST"

    # Экспорт переменных в окружение GitHub
    export_to_github_env "SERVICE_PREFIX" "$SERVICE_PREFIX"
    export_to_github_env "DEV_HOST" "$DEV_HOST"
    export_to_github_env "DEV_PASSWORD" "$DEV_PASSWORD"
    export_to_github_env "DEV_DOMAIN" "$DEV_DOMAIN"
    export_to_github_env "STAGE_DOMAIN" "$STAGE_DOMAIN"
    export_to_github_env "PROD_DOMAIN" "$PROD_DOMAIN"

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         КОНФИГУРАЦИЯ DEV СЕРВЕРА ЗАГРУЖЕНА                 ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "👤 Разработчик:  $AUTHOR_NAME"
    echo "🖥️  Dev сервер:   $DEV_HOST"
    echo "🌐 Dev домен:    $DEV_DOMAIN"
    echo "📦 Сервис:       $SERVICE_NAME"
    echo "🔧 Префикс:      $SERVICE_PREFIX"
    echo ""
}