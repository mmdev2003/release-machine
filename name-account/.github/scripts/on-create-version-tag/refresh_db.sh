#!/bin/bash

# ============================================
# Операции с таблицами базы данных
# ============================================

refresh_database_table() {
    local service_prefix=$1
    local service_name=$2

    echo ""
    echo "  📋 Сервис: $service_name"
    echo "  🔗 Префикс: $service_prefix"

    local drop_url="${STAGE_DOMAIN}${service_prefix}/table/drop"
    local create_url="${STAGE_DOMAIN}${service_prefix}/table/create"

    # Удаление существующих таблиц
    echo -n "     🗑️  Удаление таблиц... "
    local drop_response=$(curl -s -w "\n%{http_code}" -X GET "$drop_url")
    local drop_code=$(echo "$drop_response" | tail -n1)
    local drop_body=$(echo "$drop_response" | head -n -1)

    if [ "$drop_code" -ne 200 ]; then
        echo "⚠️  HTTP $drop_code"
        echo "     URL: $drop_url"
        echo "     Ответ: $drop_body"
    else
        echo "✅"
    fi

    # Создание новых таблиц
    echo -n "     📝 Создание таблиц... "
    local create_response=$(curl -s -w "\n%{http_code}" -X GET "$create_url")
    local create_code=$(echo "$create_response" | tail -n1)
    local create_body=$(echo "$create_response" | head -n -1)

    if [ "$create_code" -ne 200 ]; then
        echo "❌ HTTP $create_code"
        echo "     URL: $create_url"
        echo "     Ответ: $create_body"
        return 1
    fi

    echo "✅"
    return 0
}

# ============================================
# Массовое обновление баз данных
# ============================================

refresh_all_databases() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          ОБНОВЛЕНИЕ БАЗ ДАННЫХ ВСЕХ СЕРВИСОВ              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🌐 Домен: $STAGE_DOMAIN"

    # Определение всех сервисов для обновления
    local services=(
        "$NAME_TG_BOT_PREFIX:TG Bot"
        "$NAME_ACCOUNT_PREFIX:Account"
        "$NAME_AUTHORIZATION_PREFIX:Authorization"
        "$NAME_EMPLOYEE_PREFIX:Employee"
        "$NAME_ORGANIZATION_PREFIX:Organization"
        "$NAME_CONTENT_PREFIX:Content"
    )

    local total=${#services[@]}
    local failed=0
    local success=0

    echo ""
    echo "─────────────────────────────────────────"
    echo "Обработка $total сервисов"
    echo "─────────────────────────────────────────"

    # Отключаем set -e для цикла
    set +e

    for service_info in "${services[@]}"; do
        IFS=':' read -r prefix name <<< "$service_info"

        # Проверка на пустой префикс
        if [ -z "$prefix" ] || [ "$prefix" = ":" ]; then
            echo ""
            echo "  ⚠️  Пропуск: $name (пустой префикс)"
            ((failed++))
            continue
        fi

        # Вызов функции с явной обработкой результата
        if refresh_database_table "$prefix" "$name"; then
            ((success++))
        else
            ((failed++))
        fi
    done

    # Включаем обратно set -e
    set -e

    # Итоги
    echo ""
    echo "─────────────────────────────────────────"
    echo "Итоги обновления"
    echo "─────────────────────────────────────────"
    echo "✅ Успешно:   $success"
    echo "❌ С ошибками: $failed"
    echo "📊 Всего:      $total"
    echo ""

    if [ $failed -gt 0 ]; then
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║         ОБНОВЛЕНИЕ БД ЗАВЕРШЕНО С ОШИБКАМИ                ║"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo ""
        return 1
    fi

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         ВСЕ БАЗЫ ДАННЫХ УСПЕШНО ОБНОВЛЕНЫ                 ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    return 0
}