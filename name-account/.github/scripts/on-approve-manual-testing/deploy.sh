#!/bin/bash

# ============================================
# Основная функция развертывания
# ============================================

deploy_to_server() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║            НАЧАЛО РАЗВЕРТЫВАНИЯ НА PRODUCTION              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $PROD_HOST"
    echo "🌐 Домен:      $PROD_DOMAIN"
    echo "🆔 Release ID: $RELEASE_ID"
    echo ""

    # Выполняем SSH команду и выводим результат в реальном времени
    sshpass -p "$PROD_PASSWORD" ssh -o StrictHostKeyChecking=no root@$PROD_HOST -p 22 \
        SERVICE_NAME="$SERVICE_NAME" \
        TAG_NAME="$TAG_NAME" \
        SYSTEM_REPO="$SYSTEM_REPO" \
        SERVICE_PREFIX="$SERVICE_PREFIX" \
        PROD_DOMAIN="$PROD_DOMAIN" \
        RELEASE_ID="$RELEASE_ID" \
        NAME_RELEASE_TG_BOT_PREFIX="$NAME_RELEASE_TG_BOT_PREFIX" \
        bash << 'EOFMAIN'
set -e

# ============================================
# Настройка логирования на удаленном сервере
# ============================================

LOG_DIR="/var/log/deployments/production/$SERVICE_NAME"
LOG_FILE="$LOG_DIR/$TAG_NAME.log"

init_logging() {
    mkdir -p "$LOG_DIR"
    {
        echo "========================================"
        echo "PRODUCTION РАЗВЕРТЫВАНИЕ НАЧАТО"
        echo "========================================"
        echo "Дата:       $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Сервис:     $SERVICE_NAME"
        echo "Версия:     $TAG_NAME"
        echo "Префикс:    $SERVICE_PREFIX"
        echo "Домен:      $PROD_DOMAIN"
        echo "Release ID: $RELEASE_ID"
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
# Обновление статуса релиза
# ============================================

update_release_status_internal() {
    local new_status=$1

    if [ -z "$RELEASE_ID" ]; then
        log WARN "Release ID не передан, пропуск обновления статуса"
        return 0
    fi

    log INFO "Обновление статуса релиза: $new_status"

    local payload=$(echo '{
        "release_id": '"$RELEASE_ID"',
        "status": "'"$new_status"'"
    }' | tr -d '\n' | sed 's/  */ /g')

    local endpoint="${PROD_DOMAIN}${NAME_RELEASE_TG_BOT_PREFIX}/release"

    local response=$(curl -s -w "\n%{http_code}" -X PATCH \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$endpoint")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 204 ]; then
        log SUCCESS "Статус обновлен: $new_status"
    else
        log WARN "Ошибка обновления статуса [HTTP $http_code]: $body"
    fi
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
            python internal/migration/run.py prod --command up
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
    local url="$PROD_DOMAIN$SERVICE_PREFIX/health"
    local http_code=$(curl -f -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    [ "$http_code" = "200" ]
}

wait_for_health() {
    echo ""
    log INFO "Проверка работоспособности сервиса"
    log INFO "Ожидание 15 секунд перед проверкой..."
    sleep 15

    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log INFO "Попытка $attempt/$max_attempts"

        if check_health; then
            log SUCCESS "Сервис работает корректно (HTTP 200)"
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log WARN "Сервис не готов, ожидание 20 сек..."
            sleep 20
        fi

        ((attempt++))
    done

    log ERROR "Сервис не прошел проверку после $max_attempts попыток"
    echo ""
    echo "Логи контейнера (последние 50 строк):"
    docker logs --tail 50 $SERVICE_NAME 2>&1 | tee -a "$LOG_FILE"
    return 1
}

# ============================================
# Откат при ошибке
# ============================================

rollback_to_previous() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           АВТОМАТИЧЕСКИЙ ОТКАТ                             ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    local previous_tag=$(cat /tmp/${SERVICE_NAME}_previous_tag.txt 2>/dev/null || echo "")

    if [ -z "$previous_tag" ]; then
        log ERROR "Предыдущий тег не найден"
        log ERROR "Откат невозможен - требуется ручное вмешательство"
        return 1
    fi

    log INFO "Откат на версию: $previous_tag"

    # Откат миграций
    echo ""
    log INFO "Откат миграций к версии $previous_tag"
    cd name/$SERVICE_NAME

    local migration_output=$(mktemp)

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        -e PREVIOUS_TAG="$previous_tag" \
        --env-file ../$SYSTEM_REPO/env/.env.app \
        --env-file ../$SYSTEM_REPO/env/.env.db \
        --env-file ../$SYSTEM_REPO/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            pip install -q -r .github/requirements.txt
            python internal/migration/run.py prod --command down --version $PREVIOUS_TAG
        ' > "$migration_output" 2>&1

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        grep -E "(Rolling back|Rolled back|Reverting|Downgrade)" "$migration_output" || echo "Откат миграций выполнен"
        log SUCCESS "Миграции откачены успешно"
    else
        cat "$migration_output"
        log WARN "Ошибка отката миграций, продолжаем..."
    fi

    cat "$migration_output" >> "$LOG_FILE"
    rm -f "$migration_output"

    # Переключение на предыдущий тег
    echo ""
    log INFO "Переключение на версию $previous_tag"

    if git checkout $previous_tag >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Переключено на $previous_tag"
    else
        log ERROR "Не удалось переключиться на $previous_tag"
        return 1
    fi

    # Пересборка контейнера
    echo ""
    log INFO "Пересборка контейнера с версией $previous_tag"
    cd ../$SYSTEM_REPO

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    local docker_output=$(mktemp)

    docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME > "$docker_output" 2>&1
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        grep -E "(Building|Built|Creating|Created|Starting|Started|Recreating)" "$docker_output" || echo "Контейнер пересобран"
        log SUCCESS "Контейнер пересобран с версией $previous_tag"
    else
        cat "$docker_output"
        log ERROR "Ошибка пересборки контейнера"
        rm -f "$docker_output"
        return 1
    fi

    cat "$docker_output" >> "$LOG_FILE"
    rm -f "$docker_output"

    # Проверка работоспособности после отката
    echo ""
    log INFO "Проверка работоспособности после отката"
    log INFO "Ожидание 15 секунд..."
    sleep 15

    local rollback_attempts=3
    local rollback_attempt=1

    while [ $rollback_attempt -le $rollback_attempts ]; do
        log INFO "Проверка $rollback_attempt/$rollback_attempts"

        if check_health; then
            log SUCCESS "Откат выполнен успешно, сервис работает"
            return 0
        fi

        if [ $rollback_attempt -lt $rollback_attempts ]; then
            log WARN "Ожидание 10 секунд..."
            sleep 10
        fi

        ((rollback_attempt++))
    done

    log ERROR "Откат выполнен, но health check не прошел"
    log ERROR "Требуется ручное вмешательство"

    echo ""
    echo "Логи контейнера после отката (последние 50 строк):"
    docker logs --tail 50 $SERVICE_NAME 2>&1 | tee -a "$LOG_FILE"

    return 1
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

    if wait_for_health; then
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
            echo "PRODUCTION РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО"
            echo "========================================"
            echo "Время:   $(date '+%Y-%m-%d %H:%M:%S')"
            echo "Статус:  УСПЕШНО"
            echo "Версия:  $TAG_NAME"
            echo "========================================"
        } >> "$LOG_FILE"

        echo ""
        log INFO "📁 Полный лог сохранен: $LOG_FILE"

    else
        log ERROR "Health check не прошел - начинается откат"
        update_release_status_internal "production_rollback"

        if rollback_to_previous; then
            echo ""
            echo "╔════════════════════════════════════════════════════════════╗"
            echo "║           ОТКАТ ВЫПОЛНЕН УСПЕШНО                           ║"
            echo "╚════════════════════════════════════════════════════════════╝"
            echo ""

            log SUCCESS "Автоматический откат выполнен"
            log WARN "Деплой версии $TAG_NAME отменен"

            update_release_status_internal "rollback_done"

            {
                echo ""
                echo "========================================"
                echo "ОТКАТ ВЫПОЛНЕН"
                echo "========================================"
                echo "Время:      $(date '+%Y-%m-%d %H:%M:%S')"
                echo "Статус:     ОТКАЧЕНО"
                echo "Попытка:    $TAG_NAME"
                echo "Откат на:   $(cat /tmp/${SERVICE_NAME}_previous_tag.txt)"
                echo "========================================"
            } >> "$LOG_FILE"

            echo ""
            log INFO "📁 Полный лог сохранен: $LOG_FILE"
            exit 1

        else
            echo ""
            echo "╔════════════════════════════════════════════════════════════╗"
            echo "║           КРИТИЧЕСКАЯ ОШИБКА ОТКАТА                       ║"
            echo "╚════════════════════════════════════════════════════════════╝"
            echo ""

            log ERROR "Автоматический откат не удался"
            log ERROR "ТРЕБУЕТСЯ СРОЧНОЕ РУЧНОЕ ВМЕШАТЕЛЬСТВО"

            update_release_status_internal "rollback_failed"

            {
                echo ""
                echo "========================================"
                echo "КРИТИЧЕСКАЯ ОШИБКА"
                echo "========================================"
                echo "Время:   $(date '+%Y-%m-%d %H:%M:%S')"
                echo "Статус:  ОШИБКА ОТКАТА"
                echo "Версия:  $TAG_NAME"
                echo "========================================"
            } >> "$LOG_FILE"

            echo ""
            log INFO "📁 Полный лог сохранен: $LOG_FILE"
            exit 1
        fi
    fi
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

    echo "✅ Развертывание на $PROD_HOST успешно завершено"
    echo ""
}

# ============================================
# Обработчики после развертывания
# ============================================

verify_deployment_success() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ИТОГИ PRODUCTION РАЗВЕРТЫВАНИЯ                ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✅ Статус:     Успешно завершено"
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $PROD_HOST"
    echo "📁 Логи:       /var/log/deployments/production/$SERVICE_NAME/$TAG_NAME.log"
    echo ""
    echo "🎊 Сервис работает на production!"
    echo ""
}

handle_deployment_failure() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ОШИБКА PRODUCTION РАЗВЕРТЫВАНИЯ               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "❌ Статус:     Завершено с ошибкой"
    echo "📦 Сервис:     $SERVICE_NAME"
    echo "🏷️  Версия:     $TAG_NAME"
    echo "🖥️  Сервер:     $PROD_HOST"
    echo "📁 Логи:       /var/log/deployments/production/$SERVICE_NAME/$TAG_NAME.log"
    echo ""
    echo "🔄 Проверьте, был ли выполнен автоматический откат"
    echo "🔍 Проверьте логи выше для получения подробностей"
    echo ""
}