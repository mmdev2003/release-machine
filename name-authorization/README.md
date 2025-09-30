# Архитектурный анализ микросервиса Name Authorization

## Обзор

Name Authorization — это специализированный микросервис аутентификации и авторизации, построенный на основе современных принципов проектирования распределенных систем. Сервис реализует JWT-based authentication с поддержкой refresh-токенов и демонстрирует комплексный подход к построению enterprise-grade решений на Python с использованием FastAPI.

## Архитектурные принципы

### Clean Architecture & Layered Architecture

Проект строго следует принципам чистой архитектуры Роберта Мартина, организуя код в четко разделенные слои с явными границами зависимостей:

**1. Domain Layer (internal/model)**
- Содержит бизнес-сущности (`Account`, `JWTToken`, `TokenPayload`)
- Не имеет внешних зависимостей
- Представляет чистую бизнес-логику без технических деталей
- Определяет структуры данных, используемые во всем приложении

**2. Application Layer (internal/service)**
- Реализует use cases и бизнес-процессы
- Оркестрирует взаимодействие между слоями
- Содержит основную логику создания, валидации и обновления токенов
- Координирует работу репозиториев и внешних сервисов

**3. Interface Adapters (internal/controller, internal/repo)**
- Контроллеры адаптируют HTTP-запросы к вызовам бизнес-логики
- Репозитории инкапсулируют доступ к данным
- Изолируют технические детали от бизнес-логики
- Обеспечивают преобразование между внешними и внутренними представлениями данных

**4. Infrastructure Layer (infrastructure/)**
- Реализации конкретных технологий (PostgreSQL, Redis, OpenTelemetry)
- Внешние зависимости и интеграции
- Легко заменяемые компоненты
- Конфигурация и инициализация внешних систем

### Dependency Inversion Principle (DIP)

Проект демонстрирует образцовое применение принципа инверсии зависимостей через систему интерфейсов с использованием Python Protocol:

```python
# internal/interface/general.py
class IDB(Protocol):
    @abstractmethod
    async def select(self, query: str, query_params: dict) -> Sequence[Any]: pass
    
    @abstractmethod
    async def insert(self, query: str, query_params: dict) -> int: pass
    
    @abstractmethod
    async def update(self, query: str, query_params: dict) -> None: pass
```

**Преимущества:**
- Высокоуровневые модули (сервисы) не зависят от низкоуровневых (БД, HTTP)
- Легкость тестирования через mock-объекты
- Возможность замены реализаций без изменения бизнес-логики
- Явные контракты между компонентами
- Type-safety благодаря Protocol

### Interface Segregation Principle (ISP)

Интерфейсы разделены по ролям и ответственности:
- `IAuthorizationController` — HTTP-обработчики запросов
- `IAuthorizationService` — бизнес-логика аутентификации
- `IAuthorizationRepo` — доступ к данным
- `ITelemetry`, `IOtelLogger` — система наблюдаемости
- `IHttpMiddleware` — обработка cross-cutting concerns

Каждый интерфейс содержит только методы, необходимые конкретному клиенту, что упрощает реализацию и понимание кода.

### Single Responsibility Principle (SRP)

Каждый компонент имеет одну четко определенную ответственность:
- `AuthorizationService` — только бизнес-логика токенов
- `AccountRepo` — только операции с БД
- `AuthorizationController` — только обработка HTTP
- `HttpMiddleware` — только cross-cutting concerns (трейсинг, метрики, логирование)

## Observability: Комплексный подход к мониторингу

### OpenTelemetry Integration

Проект демонстрирует профессиональную реализацию трех столпов наблюдаемости (observability):

**1. Distributed Tracing**

```python
with self.tracer.start_as_current_span(
    "AuthorizationService.create_tokens",
    kind=SpanKind.INTERNAL,
    attributes={
        "account_id": account_id,
        "two_fa_status": two_fa_status
    }
) as span:
    try:
        # бизнес-логика
        span.set_status(Status(StatusCode.OK))
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
```

**Возможности:**
- Сквозное отслеживание запросов через все слои приложения
- Автоматическая инжекция trace context между сервисами через W3C Trace Context
- Визуализация dependency chains и bottlenecks
- Интеграция с Grafana Tempo для анализа производительности
- Корреляция трейсов с логами и метриками через trace_id/span_id
- Атрибуты spans для детального анализа поведения

**2. Metrics Collection**

```python
ok_request_counter = self.meter.create_counter(
    name=common.OK_REQUEST_TOTAL_METRIC,
    description="Total count of 200 HTTP requests",
    unit="1"
)

request_duration = self.meter.create_histogram(
    name=common.REQUEST_DURATION_METRIC,
    description="HTTP request duration in seconds",
    unit="s"
)
```

**Метрики:**
- **RED метрики** (Rate, Errors, Duration) для HTTP-запросов
- **Гистограммы** для анализа распределения латентности
- **UpDownCounter** для отслеживания активных соединений
- **Метрики размера** запросов и ответов
- Экспорт в Prometheus-совместимый формат через OTLP

**3. Structured Logging**

```python
self.logger.info("Обработка HTTP запроса завершена", {
    common.HTTP_METHOD_KEY: request.method,
    common.HTTP_ROUTE_KEY: request.url.path,
    common.TRACE_ID_KEY: trace_id,
    common.SPAN_ID_KEY: span_id,
    common.HTTP_STATUS_KEY: response.status_code,
    common.HTTP_REQUEST_DURATION_KEY: duration
})
```

**Особенности:**
- Автоматическое обогащение логов trace_id и span_id
- Структурированные поля для эффективного поиска в Loki
- Корреляция логов с трейсами и метриками
- Информация о файле и строке вызова
- Разделение по уровням (DEBUG, INFO, WARNING, ERROR)
- Отправка в Grafana Loki через OTLP

### Alert Management с AI-анализом

Инновационная система алертинга с интеграцией LLM для автоматического анализа ошибок:

```python
class AlertManager:
    async def generate_analysis(self, traceback: str) -> str:
        # GPT-4 анализирует stacktrace и предлагает решения
        system_prompt = """Ты опытный Python-разработчик и специалист по мониторингу.
        Проанализируй stacktrace и дай краткий, но информативный анализ..."""
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=history,
            temperature=0.2,
        )
```

**Преимущества:**
- **Автоматический анализ** ошибок с помощью GPT-4o-mini
- **Дедупликация алертов** через Redis с TTL 30 секунд
- **Telegram интеграция** с интерактивными кнопками и HTML-форматированием
- **Прямые ссылки** на логи и трейсы в Grafana с предзаполненными фильтрами
- **Контекстуальные рекомендации** по исправлению проблем
- **Structured alerts** с информацией о сервисе, времени, trace_id

**Workflow алертинга:**
1. Ошибка перехватывается в middleware
2. Извлекается полный traceback и контекст выполнения
3. Проверка дедупликации через Redis (защита от спама)
4. LLM генерирует краткий анализ причин и решений (300-400 символов)
5. Форматирование сообщения с HTML-разметкой для Telegram
6. Отправка в указанный chat thread с кнопками навигации
7. Ссылки на Grafana для детального анализа логов и трейсов

## HTTP Client: Enterprise-Grade решение

### Circuit Breaker Pattern

Реализация паттерна предохранителя для защиты от каскадных отказов:

```python
class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple[type[Exception], ...] = (httpx.HTTPError,)
    ):
        self._state = "closed"  # closed, open, half-open
```

**Состояния:**
- **Closed** — нормальная работа, запросы проходят
- **Open** — после N неудач, блокировка всех запросов на recovery_timeout
- **Half-Open** — пробный период восстановления с одиночными запросами

**Преимущества:**
- Быстрая fail-fast стратегия при недоступности сервиса
- Автоматическое восстановление через recovery timeout
- Защита downstream сервисов от перегрузки
- Логирование изменений состояний для мониторинга
- Возможность ручного сброса через `reset()`

### Retry Strategy с Exponential Backoff

Умная стратегия повторных попыток с экспоненциальной задержкой и jitter:

```python
class ExponentialBackoffWithJitter:
    def __call__(self, retry_state) -> float:
        delay = min(
            self.base_delay * (2 ** (retry_state.attempt_number - 1)),
            self.max_delay
        )
        jitter_value = delay * self.jitter * random.random()
        return delay + jitter_value
```

**Механизмы:**
- **Exponential backoff**: 0.1s → 0.2s → 0.4s → 0.8s...
- **Jitter**: случайное добавление до 10% для предотвращения thundering herd
- **Max delay cap**: ограничение максимальной задержки (10s по умолчанию)
- **Tenacity integration**: использование библиотеки для декларативного retry

**Преимущества:**
- Снижение нагрузки на восстанавливающийся сервис
- Предотвращение синхронизированных retry волн
- Улучшение success rate при временных сбоях
- Детальное логирование каждой попытки

### Connection Pooling & HTTP/2

Эффективное управление соединениями:

```python
httpx.AsyncClient(
    base_url=self.base_url,
    http2=True,
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    ),
    timeout=30.0
)
```

**Оптимизации:**
- **Переиспользование соединений** через connection pooling
- **HTTP/2 multiplexing** для параллельных запросов
- **Keep-alive** для снижения latency установки соединений
- **Singleton pattern** для клиентов с одинаковым base_url
- **Async context managers** для правильной очистки ресурсов

### Distributed Tracing Integration

Автоматическая инжекция контекста трейсинга:

```python
if self.use_tracing:
    propagate.inject(headers)  # W3C Trace Context injection
```

Это позволяет:
- Прослеживать запросы между микросервисами
- Строить полную картину distributed transactions
- Анализировать межсервисное взаимодействие в Grafana

## Database Layer: Масштабируемость и производительность

### Connection Pooling с SQLAlchemy

```python
async_engine = create_async_engine(
    f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}",
    pool_size=15,
    max_overflow=15,
    pool_recycle=300
)
```

**Конфигурация:**
- **pool_size=15**: базовое количество соединений
- **max_overflow=15**: дополнительные соединения при пиковых нагрузках
- **pool_recycle=300**: переоткрытие соединений каждые 5 минут (защита от stale connections)
- **asyncpg**: высокопроизводительный PostgreSQL драйвер

**Преимущества:**
- Переиспользование соединений для снижения latency
- Автоматическое управление жизненным циклом
- Защита от исчерпания DB connections
- Graceful degradation при проблемах с БД

### Async/Await для неблокирующих операций

```python
async def select(self, query: str, query_params: dict) -> Sequence[Any]:
    async with self.pool() as session:
        result = await session.execute(text(query), query_params)
        return result.all()
```

Полностью асинхронная работа с БД позволяет:
- Обрабатывать тысячи одновременных запросов
- Эффективно использовать CPU и I/O
- Масштабироваться горизонтально без блокировок

## Middleware Architecture: Cross-Cutting Concerns

### Layered Middleware Pattern

Middleware применяются в строгом порядке (цифры в названиях методов):

```python
http_middleware.logger_middleware03(app)   # Внутренний слой
http_middleware.metrics_middleware02(app)  # Средний слой
http_middleware.trace_middleware01(app)    # Внешний слой
```

**Порядок выполнения:**
1. **trace_middleware** — создает root span, устанавливает trace_id
2. **metrics_middleware** — собирает метрики, используя trace_id
3. **logger_middleware** — логирует события с trace_id и span_id

Этот порядок обеспечивает:
- Наличие trace context для всех последующих слоев
- Правильную корреляцию метрик и логов
- Единообразную обработку ошибок

### Context Propagation

```python
with self.tracer.start_as_current_span(
    f"{request.method} {request.url.path}",
    context=propagate.extract(dict(request.headers)),
    kind=SpanKind.SERVER
) as root_span:
    request.state.trace_id = trace_id
    request.state.span_id = span_id
```

**Механизмы:**
- Извлечение trace context из входящих заголовков (W3C Trace Context)
- Сохранение в request.state для доступа в обработчиках
- Добавление в исходящие ответы для клиентов
- Автоматическая инжекция в логи и метрики

## JWT Authentication: Безопасность и гибкость

### Dual Token Strategy

Реализация best practice для JWT аутентификации:

```python
# Access Token: короткоживущий (15 минут)
access_token_payload = {
    "account_id": account_id,
    "two_fa_status": two_fa_status,
    "role": role,
    "exp": int(time.time()) + 15 * 60,
}

# Refresh Token: долгоживущий (1 час для веба, 10 лет для Telegram)
refresh_token_payload = {
    "account_id": account_id,
    "two_fa_status": two_fa_status,
    "role": role,
    "exp": int(time.time()) + 60 * 60,  # или 24 * 365 * 10 * 60 для TG
}
```

**Преимущества:**
- **Минимизация риска** при компрометации access token
- **Удобство для пользователей** через автоматическое обновление
- **Возможность отзыва** через БД (refresh токены хранятся)
- **Разные политики** для разных клиентов (web vs mobile/telegram)

### Cookie-Based Storage

```python
response.set_cookie(
    key="Access-Token",
    value=jwt_token.access_token,
    expires=datetime.now() + timedelta(minutes=15),
    httponly=True,
    path="/",
    domain=self.domain
)
```

**Безопасность:**
- **httponly=True**: защита от XSS атак
- **domain scoping**: ограничение области действия
- **path control**: точная настройка доступности
- **expires**: автоматическое удаление после истечения

### 2FA Support

Встроенная поддержка двухфакторной аутентификации:

```python
token_payload = {
    "account_id": account_id,
    "two_fa_status": two_fa_status,  # Флаг прохождения 2FA
    "role": role,
    "exp": exp
}
```

Это позволяет:
- Требовать 2FA для критичных операций
- Отслеживать статус верификации
- Реализовать step-up authentication

## Database Migrations: Версионирование схемы

### Migration Manager

Профессиональная система управления миграциями:

```python
class MigrationManager:
    async def migrate(self) -> int:
        # 1. Загрузка всех миграций из version/
        # 2. Проверка примененных версий в migration_history
        # 3. Применение недостающих миграций по порядку
        # 4. Проверка зависимостей между миграциями
```

**Возможности:**
- **Автоматическое обнаружение** миграций через import
- **Versioning**: строгий порядок применения (v0_0_1, v0_0_2, ...)
- **Dependency tracking**: миграции могут зависеть друг от друга
- **Rollback support**: откат к конкретной версии
- **History table**: отслеживание примененных миграций
- **Idempotency**: безопасное повторное применение

### Миграции как код

```python
class InitialSchemaMigration(Migration):
    def get_info(self) -> MigrationInfo:
        return MigrationInfo(
            version="v0_0_1",
            name="initial_schema",
        )
    
    async def up(self, db: interface.IDB):
        await db.multi_query([create_account_table])
    
    async def down(self, db: interface.IDB):
        await db.multi_query([drop_account_table])
```

**Преимущества:**
- Миграции в системе контроля версий
- Воспроизводимые изменения схемы
- Code review для изменений БД
- Автоматизация через CI/CD

### CLI для управления

```bash
# Development: сброс и полная миграция
python internal/migration/run.py stage

# Production: только новые миграции
python internal/migration/run.py prod --command up

# Rollback к конкретной версии
python internal/migration/run.py prod --command down --version v1.0.1
```

Это обеспечивает:
- Контролируемые изменения в продакшене
- Возможность отката при проблемах
- Разные стратегии для разных окружений

## Redis Integration: Caching & Deduplication

### AsyncIO-first подход

```python
class RedisClient(interface.IRedis):
    async def get_async_client(self) -> aioredis.Redis:
        if self.async_client is None:
            self.async_pool = aioredis.ConnectionPool.from_url(...)
            self.async_client = aioredis.Redis(connection_pool=self.async_pool)
        return self.async_client
```

**Оптимизации:**
- Полностью асинхронные операции
- Connection pooling для переиспользования
- Lazy initialization клиента
- Graceful shutdown

### Use Cases

**1. Alert Deduplication**
```python
alert_send = await self.redis_client.get(trace_id)
if alert_send:
    return  # Алерт уже отправлен

await self.redis_client.set(trace_id, "1", ttl=30)
```

**2. Future: Caching, Rate Limiting, Session Storage**
- Кэширование часто запрашиваемых данных
- Distributed rate limiting
- Session management для stateless сервисов

## Configuration Management

### Environment-Based Config

```python
class Config:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "dev")
        self.service_name = os.getenv("NAME_AUTHORIZATION_CONTAINER_NAME")
        self.db_host = os.getenv("NAME_AUTHORIZATION_POSTGRES_CONTAINER_NAME")
        # ... все настройки из environment
```

**Преимущества:**
- **12-Factor App compliance**: конфигурация через окружение
- **Security**: секреты не в коде
- **Flexibility**: разные настройки для разных окружений
- **Docker/Kubernetes friendly**: легкая интеграция с оркестраторами

### Centralized Constants

```python
# internal/common/const.py
TRACE_ID_KEY = "trace_id"
HTTP_METHOD_KEY = "http.request.method"
REQUEST_DURATION_METRIC = "http.server.request.duration"
```

Централизация констант обеспечивает:
- Единообразие именования
- Легкость рефакторинга
- Соответствие OpenTelemetry semantic conventions
- Type safety и автокомплит

## Error Handling: Graceful Degradation

### Structured Exception Hierarchy

```python
class ErrAccountNotFound(Exception):
    def __str__(self):
        return 'Account not found'

class ErrTokenExpired(Exception):
    def __str__(self):
        return 'Token expired'
```

**Преимущества:**
- Специфичная обработка разных ошибок
- Понятные сообщения для пользователей
- Возможность логирования на нужном уровне

### Try-Except в каждом слое

```python
try:
    # операция
    span.set_status(Status(StatusCode.OK))
except Exception as e:
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, str(e)))
    self.logger.error("Ошибка", {common.TRACEBACK_KEY: traceback.format_exc()})
    raise
```

Это обеспечивает:
- Полный контекст ошибки в трейсах
- Детальное логирование с traceback
- Корректное распространение исключений
- Observability на каждом уровне

## Итоговые преимущества архитектуры

### Maintainability (Поддерживаемость)

1. **Четкое разделение ответственности** — каждый компонент имеет одну задачу
2. **Слабая связанность** через интерфейсы — легко модифицировать части системы
3. **Явные зависимости** — dependency injection делает граф зависимостей прозрачным
4. **Структурированный код** — легко найти нужный компонент

### Testability (Тестируемость)

1. **Protocol-based интерфейсы** — простое создание mock-объектов
2. **Pure functions в domain layer** — изолированное тестирование бизнес-логики
3. **Dependency injection** — подмена компонентов в тестах
4. **Observability встроена** — метрики и трейсы для тестирования производительности

### Scalability (Масштабируемость)

1. **Stateless сервис** — горизонтальное масштабирование без ограничений
2. **Async/await везде** — эффективное использование ресурсов
3. **Connection pooling** — оптимизация работы с БД и внешними сервисами
4. **Circuit breaker** — защита от каскадных отказов

### Observability (Наблюдаемость)

1. **Полная трассировка** запросов через все слои
2. **Структурированные метрики** для анализа производительности
3. **Корреляция** логов, трейсов и метрик
4. **AI-powered алертинг** для быстрого реагирования

### Reliability (Надежность)

1. **Retry mechanisms** с exponential backoff
2. **Circuit breaker** для fail-fast
3. **Graceful error handling** на всех уровнях
4. **Health checks** для оркестраторов
5. **Database migrations** для безопасных изменений схемы

### Security (Безопасность)

1. **JWT best practices** — dual token strategy
2. **HttpOnly cookies** — защита от XSS
3. **2FA support** встроенная
4. **Секреты через environment** — не в коде
5. **Role-based access** — подготовка к RBAC

## Применимость паттернов

Эта архитектура идеально подходит для:

- **Микросервисных систем** с множеством взаимодействующих сервисов
- **Enterprise приложений** с высокими требованиями к надежности
- **Высоконагруженных систем** с потребностью в масштабировании
- **Команд разработки** с разными уровнями квалификации (четкая структура помогает онбордингу)
- **Проектов с долгим жизненным циклом** (легко поддерживать и развивать)

## Выводы

Name Authorization демонстрирует современный подход к построению микросервисов на Python, объединяющий:

- **Clean Architecture** для долгосрочной поддерживаемости
- **SOLID принципы** для гибкости и расширяемости
- **Enterprise patterns** (Circuit Breaker, Retry, Connection Pooling) для надежности
- **Observability-first** подход с полной интеграцией OpenTelemetry
- **AI-enhanced operations** через LLM-анализ ошибок

Это не просто сервис аутентификации, а образец архитектуры, который можно использовать как reference implementation для других микросервисов в системе. Каждое архитектурное решение продумано с точки зрения production-ready требований и может служить основой для построения надежной, масштабируемой и поддерживаемой системы.