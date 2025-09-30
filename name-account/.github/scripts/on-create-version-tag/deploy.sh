#!/bin/bash

# ============================================
# Основная функция развертывания
# ============================================

deploy_to_server() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║            НАЧАЛО РАЗВЕРТЫВАНИЯ НА STAGE                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $STAGE_HOST"
    echo "🌐 Домен:      $STAGE_DOMAIN"
    echo ""

    # Выполняем SSH команду и выводим результат в реальном времени
    sshpass -p "$STAGE_PASSWORD" ssh -o StrictHostKeyChecking=no root@$STAGE_HOST -p 22 \
        SERVICE_NAME="$SERVICE_NAME" \
        TAG_NAME="$TAG_NAME" \
        SYSTEM_REPO="$SYSTEM_REPO" \
        SERVICE_PREFIX="$SERVICE_PREFIX" \
        STAGE_DOMAIN="$STAGE_DOMAIN" \
        bash << 'EOFMAIN'
set -e

# ============================================
# Настройка логирования на удаленном сервере
# ============================================

LOG_DIR="/var/log/deployments/$SERVICE_NAME"
LOG_FILE="$LOG_DIR/$TAG_NAME.log"

init_logging() {
    mkdir -p "$LOG_DIR"
    {
        echo "========================================"
        echo "РАЗВЕРТЫВАНИЕ НАЧАТО"
        echo "========================================"
        echo "Дата:    $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Сервис:  $SERVICE_NAME"
        echo "Версия:  $TAG_NAME"
        echo "Префикс: $SERVICE_PREFIX"
        echo "Домен:   $STAGE_DOMAIN"
        echo "========================================"
        echo ""
    } > "$LOG_FILE"
}

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%H:%M:%S')

    case $level in
        INFO)    local icon="ℹ️ " ;;
        SUCCESS) local icon="✅" ;;
        ERROR)   local icon="❌" ;;
        WARN)    local icon="⚠️ " ;;
        *)       local icon="  " ;;
    esac

    # Выводим в консоль (будет отображаться в GitHub)
    echo "${icon} ${message}"
    # Записываем в файл
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# ============================================
# Операции с Git
# ============================================

save_previous_tag() {
    echo ""
    log INFO "Сохранение текущей версии для отката"
    cd name/$SERVICE_NAME

    local previous_tag=$(git describe --tags --exact-match 2>/dev/null || echo "")

    if [ -n "$previous_tag" ]; then
        echo "$previous_tag" > /tmp/${SERVICE_NAME}_previous_tag.txt
        log SUCCESS "Сохранен тег для отката: $previous_tag"
    else
        echo "" > /tmp/${SERVICE_NAME}_previous_tag.txt
        log WARN "Предыдущий тег не найден (первый деплой)"
    fi

    cd
}

update_repository() {
    echo ""
    log INFO "Обновление репозитория"
    cd name/$SERVICE_NAME

    local current_ref=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log INFO "Текущее состояние: $current_ref"

    # Удаление локального тега
    if git tag -l | grep -q "^$TAG_NAME$"; then
        log INFO "Удаление локального тега $TAG_NAME"
        git tag -d $TAG_NAME >> "$LOG_FILE" 2>&1
    fi

    # Получение обновлений (без вывода в консоль)
    log INFO "Получение обновлений из origin..."
    git fetch origin >> "$LOG_FILE" 2>&1
    git fetch origin --tags --force >> "$LOG_FILE" 2>&1

    # Проверка доступности тега
    if ! git tag -l | grep -q "^$TAG_NAME$"; then
        log ERROR "Тег $TAG_NAME не найден после получения"
        echo ""
        echo "Доступные теги (последние 10):"
        git tag -l | tail -10
        exit 1
    fi

    log SUCCESS "Тег $TAG_NAME получен успешно"
    cd
}

checkout_tag() {
    echo ""
    log INFO "Переключение на версию $TAG_NAME"
    cd name/$SERVICE_NAME

    if git checkout $TAG_NAME >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Переключено на $TAG_NAME"
    else
        log ERROR "Не удалось переключиться на $TAG_NAME"
        exit 1
    fi

    cd
}

cleanup_branches() {
    echo ""
    log INFO "Очистка старых веток"
    cd name/$SERVICE_NAME

    local branches_deleted=$(git for-each-ref --format='%(refname:short)' refs/heads | \
        grep -v -E "^(main|master)$" | wc -l)

    if [ $branches_deleted -gt 0 ]; then
        git for-each-ref --format='%(refname:short)' refs/heads | \
            grep -v -E "^(main|master)$" | \
            xargs -r git branch -D >> "$LOG_FILE" 2>&1
        log SUCCESS "Удалено веток: $branches_deleted"
    else
        log INFO "Нет веток для удаления"
    fi

    git remote prune origin >> "$LOG_FILE" 2>&1
    cd
}

# ============================================
# Миграции базы данных
# ============================================

run_migrations() {
    echo ""
    log INFO "Запуск миграций базы данных"
    cd name/$SERVICE_NAME

    # Создаем временный файл для вывода миграций
    local migration_output=$(mktemp)

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        --env-file ../$SYSTEM_REPO/env/.env.app \
        --env-file ../$SYSTEM_REPO/env/.env.db \
        --env-file ../$SYSTEM_REPO/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            pip install -q -r .github/requirements.txt
            python internal/migration/run.py stage
        ' > "$migration_output" 2>&1

    local exit_code=$?

    # Показываем только важные строки из вывода миграций
    if [ $exit_code -eq 0 ]; then
        # Фильтруем вывод: показываем только строки с миграциями
        grep -E "(Running migration|Applied|Skipping|No migrations)" "$migration_output" || echo "Миграции выполнены"
        log SUCCESS "Миграции выполнены успешно"
    else
        # При ошибке показываем полный вывод
        cat "$migration_output"
        log ERROR "Миграции завершились с ошибкой"
        rm -f "$migration_output"
        exit 1
    fi

    # Сохраняем полный вывод в лог-файл
    cat "$migration_output" >> "$LOG_FILE"
    rm -f "$migration_output"

    cd
}

# ============================================
# Операции с Docker контейнерами
# ============================================

build_container() {
    echo ""
    log INFO "Сборка и запуск Docker контейнера"
    cd name/$SYSTEM_REPO

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    # Создаем временный файл для вывода docker compose
    local docker_output=$(mktemp)

    docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME > "$docker_output" 2>&1
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        # Показываем только важные строки
        grep -E "(Building|Built|Creating|Created|Starting|Started|Recreating)" "$docker_output" || echo "Контейнер запущен"
        log SUCCESS "Контейнер $SERVICE_NAME собран и запущен"
    else
        # При ошибке показываем полный вывод
        cat "$docker_output"
        log ERROR "Ошибка сборки контейнера $SERVICE_NAME"
        rm -f "$docker_output"
        exit 1
    fi

    # Сохраняем полный вывод в лог-файл
    cat "$docker_output" >> "$LOG_FILE"
    rm -f "$docker_output"

    cd
}

check_health() {
    local url="$STAGE_DOMAIN$SERVICE_PREFIX/health"
    local http_code=$(curl -f -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    [ "$http_code" = "200" ]
}

wait_for_health() {
    echo ""
    log INFO "Проверка работоспособности сервиса"
    log INFO "Ожидание 10 секунд перед проверкой..."
    sleep 10

    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log INFO "Попытка $attempt/$max_attempts"

        if check_health; then
            log SUCCESS "Сервис работает корректно (HTTP 200)"
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log WARN "Сервис не готов, ожидание 15 сек..."
            sleep 15
        fi

        ((attempt++))
    done

    log ERROR "Сервис не прошел проверку после $max_attempts попыток"
    echo ""
    echo "Логи контейнера (последние 30 строк):"
    docker logs --tail 30 $SERVICE_NAME 2>&1 | tee -a "$LOG_FILE"
    exit 1
}

# ============================================
# Основной процесс развертывания
# ============================================

main() {
    init_logging

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║            ПРОЦЕСС РАЗВЕРТЫВАНИЯ                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    save_previous_tag
    update_repository
    checkout_tag
    cleanup_branches
    run_migrations
    build_container
    wait_for_health

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО УСПЕШНО! 🎉               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    if [ -f "/tmp/${SERVICE_NAME}_previous_tag.txt" ]; then
        local saved_tag=$(cat /tmp/${SERVICE_NAME}_previous_tag.txt)
        if [ -n "$saved_tag" ]; then
            log INFO "Для отката доступен тег: $saved_tag"
        fi
    fi

    {
        echo ""
        echo "========================================"
        echo "РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО"
        echo "========================================"
        echo "Время:   $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Статус:  УСПЕШНО"
        echo "Версия:  $TAG_NAME"
        echo "========================================"
    } >> "$LOG_FILE"

    echo ""
    log INFO "📁 Полный лог сохранен: $LOG_FILE"
}

main
EOFMAIN

    local ssh_exit_code=$?

    echo ""
    if [ $ssh_exit_code -ne 0 ]; then
        echo "❌ Развертывание завершилось с ошибкой (код: $ssh_exit_code)"
        echo ""
        exit 1
    fi

    echo "✅ Развертывание на $STAGE_HOST успешно завершено"
    echo ""
}

# ============================================
# Обработчики после развертывания
# ============================================

verify_deployment_success() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ИТОГИ РАЗВЕРТЫВАНИЯ                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✅ Статус:     Успешно завершено"
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $STAGE_HOST"
    echo "📁 Логи:       /var/log/deployments/$SERVICE_NAME/$TAG_NAME.log"
    echo ""
    echo "👉 Следующий шаг: Ручное тестирование"
    echo ""
}

handle_deployment_failure() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ОШИБКА РАЗВЕРТЫВАНИЯ                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "❌ Статус:     Завершено с ошибкой"
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $STAGE_HOST"
    echo "📁 Логи:       /var/log/deployments/$SERVICE_NAME/$TAG_NAME.log"
    echo ""
    echo "🔍 Проверьте логи выше для получения подробностей"
    echo ""
}