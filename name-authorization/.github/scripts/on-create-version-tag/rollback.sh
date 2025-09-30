#!/bin/bash

# ============================================
# Основная функция отката
# ============================================

execute_rollback() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║               ТЕСТ ОТКАТА НА STAGE                         ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📦 Сервис:         $SERVICE_NAME"
    echo "🔄 Откат на:       $PREVIOUS_TAG"
    echo "🖥️  Сервер:         $STAGE_HOST"
    echo ""

    # Выполняем SSH команду и выводим результат в реальном времени
    sshpass -p "$STAGE_PASSWORD" ssh -o StrictHostKeyChecking=no root@$STAGE_HOST -p 22 \
        SERVICE_NAME="$SERVICE_NAME" \
        TARGET_TAG="$PREVIOUS_TAG" \
        SYSTEM_REPO="$SYSTEM_REPO" \
        SERVICE_PREFIX="$SERVICE_PREFIX" \
        STAGE_DOMAIN="$STAGE_DOMAIN" \
        bash << 'EOFMAIN'
set -e

# ============================================
# Настройка логирования на удаленном сервере
# ============================================

LOG_DIR="/var/log/deployments/rollback/$SERVICE_NAME"
LOG_FILE="$LOG_DIR/$TARGET_TAG-rollback.log"

init_logging() {
    mkdir -p "$LOG_DIR"
    {
        echo "========================================"
        echo "ОТКАТ НАЧАТ"
        echo "========================================"
        echo "Дата:         $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Сервис:       $SERVICE_NAME"
        echo "Целевой тег:  $TARGET_TAG"
        echo "Префикс:      $SERVICE_PREFIX"
        echo "Домен:        $STAGE_DOMAIN"
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
# Сохранение текущего состояния
# ============================================

save_current_state() {
    echo ""
    log INFO "Сохранение текущего состояния"
    cd name/$SERVICE_NAME

    local current_ref=$(git symbolic-ref --short HEAD 2>/dev/null || git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log INFO "Текущее состояние: $current_ref"

    echo "$current_ref" > /tmp/${SERVICE_NAME}_rollback_previous.txt
    log SUCCESS "Состояние сохранено для восстановления"

    cd
}

# ============================================
# Откат миграций базы данных
# ============================================

rollback_migrations() {
    echo ""
    log INFO "Откат миграций к версии $TARGET_TAG"
    cd name/$SERVICE_NAME

    # Создаем временный файл для вывода миграций
    local migration_output=$(mktemp)

    docker run --rm \
        --network net \
        -v ./:/app \
        -w /app \
        -e PREVIOUS_TAG="$TARGET_TAG" \
        --env-file ../$SYSTEM_REPO/env/.env.app \
        --env-file ../$SYSTEM_REPO/env/.env.db \
        --env-file ../$SYSTEM_REPO/env/.env.monitoring \
        python:3.11-slim \
        bash -c '
            pip install -q -r .github/requirements.txt
            python internal/migration/run.py stage --command down --version $PREVIOUS_TAG
        ' > "$migration_output" 2>&1

    local exit_code=$?

    # Показываем только важные строки из вывода миграций
    if [ $exit_code -eq 0 ]; then
        grep -E "(Rolling back|Rolled back|Reverting|No migrations|Downgrade)" "$migration_output" || echo "Откат миграций выполнен"
        log SUCCESS "Миграции откачены успешно"
    else
        cat "$migration_output"
        log ERROR "Ошибка отката миграций"
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

rebuild_container_for_rollback() {
    echo ""
    log INFO "Переключение на версию $TARGET_TAG"
    cd name/$SERVICE_NAME

    git fetch --tags >> "$LOG_FILE" 2>&1

    if git checkout "$TARGET_TAG" >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Переключено на $TARGET_TAG"
    else
        log ERROR "Ошибка переключения на $TARGET_TAG"
        exit 1
    fi

    local current_version=$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
    log INFO "Текущая версия: $current_version"

    cd

    log INFO "Пересборка контейнера для отката"
    cd name/$SYSTEM_REPO

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    # Создаем временный файл для вывода docker compose
    local docker_output=$(mktemp)

    docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME > "$docker_output" 2>&1
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        grep -E "(Building|Built|Creating|Created|Starting|Started|Recreating)" "$docker_output" || echo "Контейнер пересобран"
        log SUCCESS "Контейнер $SERVICE_NAME пересобран успешно"
    else
        cat "$docker_output"
        log ERROR "Ошибка пересборки контейнера $SERVICE_NAME"
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

wait_for_health_after_rollback() {
    echo ""
    log INFO "Проверка работоспособности после отката"
    log INFO "Ожидание 10 секунд перед проверкой..."
    sleep 10

    local max_attempts=5
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        log INFO "Попытка $attempt/$max_attempts"

        if check_health; then
            log SUCCESS "Сервис работает после отката (HTTP 200)"
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            log WARN "Сервис не готов, ожидание 20 сек..."
            sleep 20
        fi

        ((attempt++))
    done

    log ERROR "Проверка не пройдена после $max_attempts попыток"
    echo ""
    echo "Логи контейнера (последние 30 строк):"
    docker logs --tail 30 $SERVICE_NAME 2>&1 | tee -a "$LOG_FILE"
    exit 1
}

# ============================================
# Восстановление к исходной версии
# ============================================

restore_to_original() {
    echo ""
    log INFO "Восстановление исходной версии"
    cd name/$SERVICE_NAME

    local previous_ref=$(cat /tmp/${SERVICE_NAME}_rollback_previous.txt 2>/dev/null || echo "")

    if [ -z "$previous_ref" ]; then
        log WARN "Не найдено сохраненное состояние"
        return 1
    fi

    log INFO "Восстановление к: $previous_ref"

    if git checkout "$previous_ref" >> "$LOG_FILE" 2>&1; then
        log SUCCESS "Переключено на $previous_ref"
    else
        log ERROR "Не удалось переключиться на $previous_ref"
        return 1
    fi

    log INFO "Повторное применение миграций для исходной версии"

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

    if [ $exit_code -eq 0 ]; then
        grep -E "(Running migration|Applied|Skipping|No migrations)" "$migration_output" || echo "Миграции применены"
        log SUCCESS "Миграции применены успешно"
    else
        log WARN "Миграции завершились с предупреждениями"
    fi

    cat "$migration_output" >> "$LOG_FILE"
    rm -f "$migration_output"

    cd ../$SYSTEM_REPO

    export $(cat env/.env.app env/.env.db env/.env.monitoring | xargs)

    log INFO "Пересборка контейнера с исходной версией"

    # Создаем временный файл для вывода docker compose
    local docker_output=$(mktemp)

    docker compose -f ./docker-compose/app.yaml up -d --build $SERVICE_NAME > "$docker_output" 2>&1
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        grep -E "(Building|Built|Creating|Created|Starting|Started|Recreating)" "$docker_output" || echo "Контейнер восстановлен"
        log SUCCESS "Исходная версия восстановлена"
    else
        cat "$docker_output"
        log WARN "Предупреждения при восстановлении контейнера"
    fi

    cat "$docker_output" >> "$LOG_FILE"
    rm -f "$docker_output"

    rm -f /tmp/${SERVICE_NAME}_rollback_previous.txt

    return 0
}

# ============================================
# Основной процесс отката
# ============================================

main() {
    init_logging

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║               ПРОЦЕСС ОТКАТА                               ║"
    echo "╚════════════════════════════════════════════════════════════╝"

    save_current_state
    rollback_migrations
    rebuild_container_for_rollback
    wait_for_health_after_rollback

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           ОТКАТ ПРОТЕСТИРОВАН УСПЕШНО! ✅                  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    log INFO "Версия отката $TARGET_TAG проверена успешно"
    log INFO "Начинается восстановление исходной версии..."

    restore_to_original

    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║        ЦИКЛ ТЕСТА ОТКАТА ЗАВЕРШЕН! 🎉                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    {
        echo ""
        echo "========================================"
        echo "ТЕСТ ОТКАТА ЗАВЕРШЕН"
        echo "========================================"
        echo "Время:          $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Статус:         УСПЕШНО"
        echo "Версия отката:  $TARGET_TAG"
        echo "========================================"
    } >> "$LOG_FILE"

    log INFO "📁 Полный лог сохранен: $LOG_FILE"
}

main
EOFMAIN

    local ssh_exit_code=$?

    echo ""
    if [ $ssh_exit_code -ne 0 ]; then
        echo "❌ Тест отката завершился с ошибкой (код: $ssh_exit_code)"
        echo ""
        exit 1
    fi

    echo "✅ Тест отката на $STAGE_HOST успешно завершен"
    echo ""
}

# ============================================
# Обработчики после отката
# ============================================

verify_rollback_success() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ИТОГИ ТЕСТА ОТКАТА                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✅ Статус:          Успешно завершено"
    echo "📦 Сервис:          $SERVICE_NAME"
    echo "🔄 Версия отката:   $1"
    echo "🖥️  Сервер:          $STAGE_HOST"
    echo "📁 Логи:            /var/log/deployments/rollback/$SERVICE_NAME/$1-rollback.log"
    echo ""
    echo "ℹ️  Откат протестирован, исходная версия восстановлена"
    echo ""
}

handle_rollback_failure() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ОШИБКА ТЕСТА ОТКАТА                           ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "❌ Статус:          Завершено с ошибкой"
    echo "📦 Сервис:          $SERVICE_NAME"
    echo "🔄 Целевая версия:  $1"
    echo "🖥️  Сервер:          $STAGE_HOST"
    echo "📁 Логи:            /var/log/deployments/rollback/$SERVICE_NAME/$1-rollback.log"
    echo ""
    echo "🔍 Проверьте логи выше для получения подробностей"
    echo ""
}

# ============================================
# Высокоуровневая обёртка отката
# ============================================

rollback_with_status_tracking() {
    echo ""
    echo "─────────────────────────────────────────"
    echo "Обновление статуса: stage_test_rollback"
    echo "─────────────────────────────────────────"
    update_release_status "stage_test_rollback"

    execute_rollback

    if [ $? -eq 0 ]; then
        echo ""
        echo "─────────────────────────────────────────"
        echo "Обновление статуса: manual_testing"
        echo "─────────────────────────────────────────"
        update_release_status "manual_testing"
        verify_rollback_success "$PREVIOUS_TAG"
    else
        echo ""
        echo "─────────────────────────────────────────"
        echo "Обновление статуса: stage_test_rollback_failed"
        echo "─────────────────────────────────────────"
        update_release_status "stage_test_rollback_failed"
        handle_rollback_failure "$PREVIOUS_TAG"
        exit 1
    fi
}