# Архитектурный обзор микросервиса Name-Account

## Введение

Name-Account представляет собой микросервис управления учетными записями, разработанный в соответствии с современными принципами построения распределенных систем. Сервис реализует критически важные функции аутентификации и авторизации, включая двухфакторную аутентификацию (2FA), управление паролями и интеграцию с внешними сервисами авторизации.

## Архитектурные принципы и паттерны

### 1. Clean Architecture и многоуровневая архитектура

Микросервис строго следует принципам **Clean Architecture**, предложенным Робертом Мартином, с четким разделением ответственности между слоями:

#### Слой представления (Controller Layer)
- Обрабатывает HTTP-запросы через FastAPI
- Преобразует HTTP-запросы в доменные команды
- Управляет сериализацией/десериализацией данных через Pydantic
- Обеспечивает валидацию входящих данных на уровне API

#### Слой бизнес-логики (Service Layer)
- Инкапсулирует все бизнес-правила приложения
- Координирует взаимодействие между различными компонентами
- Реализует сложную логику: хеширование паролей с использованием bcrypt, генерацию TOTP-токенов для 2FA, верификацию учетных данных
- Обеспечивает транзакционную целостность операций

#### Слой доступа к данным (Repository Layer)
- Изолирует бизнес-логику от деталей персистентности
- Реализует паттерн Repository для абстракции работы с БД
- Управляет SQL-запросами и маппингом данных
- Обеспечивает централизованную точку для операций с PostgreSQL

**Преимущества такого подхода:**
- Независимость бизнес-логики от фреймворков и инфраструктуры
- Высокая тестируемость каждого слоя в изоляции
- Возможность изменения технологий без переписывания бизнес-логики
- Четкие границы ответственности и принцип единственной ответственности (SRP)

### 2. Dependency Injection и Protocol-ориентированное проектирование

Сервис использует **Protocol-based Dependency Injection** через интерфейсы Python (Protocol из typing):

```python
class IAccountService(Protocol):
    @abstractmethod
    async def register(self, login: str, password: str) -> model.AuthorizationDataDTO: pass
    
    @abstractmethod
    async def login(self, login: str, password: str) -> model.AuthorizationDataDTO: pass
```

**Ключевые преимущества:**
- **Инверсия зависимостей (DIP)**: высокоуровневые модули не зависят от низкоуровневых, оба зависят от абстракций
- **Тестируемость**: легкость создания mock-объектов для unit-тестирования
- **Слабая связанность**: компоненты взаимодействуют через интерфейсы, не зная о конкретных реализациях
- **Гибкость**: простота замены реализаций без изменения клиентского кода

Все зависимости конструируются в точке входа (`main.py`), следуя паттерну **Composition Root**.

### 3. Паттерн Repository

Реализован классический паттерн Repository для абстракции доступа к данным:

```python
class AccountRepo(interface.IAccountRepo):
    async def create_account(self, login: str, password: str) -> int
    async def account_by_id(self, account_id: int) -> list[model.Account]
    async def account_by_login(self, login: str) -> list[model.Account]
```

**Преимущества паттерна:**
- Централизация логики доступа к данным
- Возможность смены СУБД без изменения бизнес-логики
- Упрощение тестирования через mock-репозитории
- Единая точка для оптимизации запросов

## Observability: Комплексный подход к мониторингу

### OpenTelemetry Integration

Сервис полностью интегрирован с **OpenTelemetry** - индустриальным стандартом для наблюдаемости (observability), предоставляя три столпа мониторинга:

#### 1. Distributed Tracing (Распределенная трассировка)

Каждый запрос сопровождается уникальным trace_id, позволяющим отследить путь запроса через всю систему:

```python
with self.tracer.start_as_current_span(
    "AccountService.register",
    kind=SpanKind.INTERNAL,
    attributes={"login": login}
) as span:
    # Бизнес-логика
    span.set_status(Status(StatusCode.OK))
```

**Преимущества:**
- **End-to-end visibility**: полная видимость путешествия запроса через микросервисы
- **Performance profiling**: точное определение узких мест в производительности
- **Dependency mapping**: автоматическое построение карты зависимостей сервисов
- **Root cause analysis**: быстрая локализация источника проблем в распределенной системе

#### 2. Metrics (Метрики)

Реализована всесторонняя сборка метрик для мониторинга здоровья системы:

- **HTTP метрики**: request duration, active requests, request/response body size
- **Business метрики**: успешные/неудачные запросы, разделенные по маршрутам
- **Custom метрики**: специфичные для домена показатели

**Архитектурные решения:**
- Использование PeriodicExportingMetricReader для батчинга метрик
- Асинхронная отправка метрик без блокировки основного потока
- Агрегация метрик с использованием labels для многомерного анализа

#### 3. Structured Logging (Структурированное логирование)

Логи обогащаются контекстной информацией и отправляются в централизованную систему:

```python
self.logger.info("Registration successful", {
    "login": body.login,
    "account_id": authorization_data.account_id,
    "trace_id": trace_id,
    "span_id": span_id
})
```

**Ключевые особенности:**
- Автоматическая корреляция логов с трассировками через trace_id/span_id
- Контекстное обогащение каждого лог-события
- Информация о файле и строке кода для быстрой локализации
- Батчинговая отправка для снижения накладных расходов

### Intelligent Alert Management

Реализована интеллектуальная система алертинга с несколькими уровнями защиты от информационного шума:

#### 1. Дедупликация алертов

Использование Redis для предотвращения дублирования оповещений:

```python
alert_send = await self.redis_client.get(trace_id)
if alert_send:
    return  # Алерт уже отправлен
await self.redis_client.set(trace_id, "1", ttl=30)
```

**Преимущества:**
- Защита от alert fatigue (усталости от алертов)
- Снижение noise-to-signal ratio
- Экономия ресурсов системы уведомлений

#### 2. AI-powered анализ ошибок

Интеграция с OpenAI GPT-4 для автоматического анализа stack traces:

```python
async def generate_analysis(self, traceback: str) -> str:
    system_prompt = """Ты опытный Python-разработчик.
    Проанализируй stacktrace и дай краткий анализ:
    - Проблема → Причина → Решение
    - Максимум 300-400 символов"""
```

**Преимущества:**
- Автоматическая диагностика проблем в режиме реального времени
- Рекомендации по исправлению без участия человека
- Сокращение MTTR (Mean Time To Resolution)
- Обучающий эффект для junior-разработчиков

#### 3. Rich notifications

Алерты отправляются в Telegram с богатым контекстом:
- Прямые ссылки на Grafana для просмотра логов и трейсов
- Временные метки и идентификаторы трейсов
- AI-анализ проблемы
- Структурированное форматирование для читаемости

## Middleware Architecture: Cross-cutting Concerns

Реализована цепочка middleware для обработки сквозной функциональности:

### 1. Trace Middleware (Приоритет 01)

**Назначение**: Создание корневого span для каждого запроса

```python
with self.tracer.start_as_current_span(
    f"{request.method} {request.url.path}",
    context=propagate.extract(dict(request.headers)),
    kind=SpanKind.SERVER
)
```

**Ключевые функции:**
- Извлечение trace context из входящих заголовков (W3C Trace Context)
- Создание нового trace, если контекст отсутствует
- Пропагация trace_id и span_id в заголовки ответа
- Автоматическая обработка и логирование HTTP ошибок

### 2. Metrics Middleware (Приоритет 02)

**Назначение**: Сбор метрик производительности и использования

Собираемые метрики:
- Request duration histogram
- Active requests up/down counter
- Request/response body size histograms
- Success/error counters с разделением по статус-кодам

**Архитектурные решения:**
- Использование гистограмм для точного распределения latency
- Атрибуты для многомерной агрегации (метод, маршрут, статус)
- Graceful error handling в finally-блоке

### 3. Logger Middleware (Приоритет 03)

**Назначение**: Структурированное логирование всех запросов

Логируемая информация:
- HTTP метод, маршрут, статус-код
- Время выполнения запроса
- Trace/Span ID для корреляции
- Stack traces при ошибках

### 4. Authorization Middleware (Приоритет 04)

**Назначение**: Проверка JWT токенов и управление доступом

```python
access_token = request.cookies.get("Access-Token")
authorization_data = await self.name_authorization_client.check_authorization(access_token)
request.state.authorization_data = authorization_data
```

**Особенности:**
- Интеграция с внешним сервисом авторизации через HTTP
- Graceful degradation для гостевого доступа
- Обработка expired/invalid токенов с соответствующими HTTP кодами
- Прикрепление authorization context к request state

## Надежность и устойчивость к сбоям

### Circuit Breaker Pattern

Реализован полнофункциональный Circuit Breaker для защиты от каскадных сбоев:

```python
class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (httpx.HTTPError,)
    )
```

**Состояния:**
1. **Closed**: Нормальная работа, запросы выполняются
2. **Open**: Превышен порог ошибок, запросы блокируются
3. **Half-Open**: Тестирование восстановления сервиса

**Преимущества:**
- Защита от перегрузки downstream-сервисов
- Быстрый fail-fast вместо долгих таймаутов
- Автоматическое восстановление после сбоев
- Предотвращение cascade failures в микросервисной архитектуре

### Retry Strategy с Exponential Backoff

Интеллектуальная стратегия повторов с использованием библиотеки tenacity:

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

**Ключевые компоненты:**
- **Exponential backoff**: экспоненциальное увеличение задержки между попытками
- **Jitter**: случайная компонента для предотвращения thundering herd problem
- **Max delay cap**: ограничение максимального времени ожидания
- **Selective retry**: повтор только для определенных типов исключений

**Предотвращаемые проблемы:**
- Thundering herd: одновременные повторы от множества клиентов
- Resource exhaustion: исчерпание ресурсов при агрессивных повторах
- Overload amplification: усиление нагрузки на восстанавливающийся сервис

### Connection Pooling

Эффективное управление HTTP-соединениями:

```python
httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    ),
    http2=True
)
```

**Преимущества:**
- Переиспользование TCP-соединений (избегание handshake overhead)
- Контроль над максимальным числом соединений
- HTTP/2 multiplexing для одновременных запросов
- Автоматическое управление keep-alive

### Singleton Pattern для HTTP-клиентов

```python
class AsyncHTTPClient:
    _instances: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
    
    def __new__(cls, host: str, port: int, ...):
        if base_url in cls._instances:
            return cls._instances[base_url]
```

**Преимущества:**
- Переиспользование connection pool между вызовами
- Экономия памяти и сетевых ресурсов
- Использование weak references для автоматической очистки

## Database Management

### Migration System

Профессиональная система миграций базы данных:

```python
class Migration(ABC):
    def get_info(self) -> MigrationInfo
    async def up(self, db) -> None
    async def down(self, db) -> None
```

**Ключевые возможности:**
- **Версионирование**: каждая миграция имеет уникальную версию
- **Зависимости**: миграции могут зависеть друг от друга
- **Rollback**: возможность отката к любой версии
- **История**: таблица migration_history отслеживает примененные миграции
- **Идемпотентность**: безопасное повторное применение

**Архитектурные решения:**
- Автоматическая загрузка миграций через importlib
- Топологическая сортировка для разрешения зависимостей
- Транзакционность на уровне отдельных миграций
- Детальное логирование процесса миграции

### Async PostgreSQL with SQLAlchemy

```python
async_engine = create_async_engine(
    f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}",
    pool_size=15,
    max_overflow=15,
    pool_recycle=300
)
```

**Конфигурация для production:**
- **pool_size=15**: базовый размер пула соединений
- **max_overflow=15**: дополнительные соединения при пиковых нагрузках
- **pool_recycle=300**: переподключение каждые 5 минут для предотвращения stale connections
- **asyncpg**: высокопроизводительный асинхронный драйвер PostgreSQL

## Security: Defense in Depth

### Password Security

Многоуровневая защита паролей:

```python
def __hash_password(self, password: str) -> str:
    peppered_password = self.password_secret_key + password
    hashed_password = bcrypt.hashpw(
        peppered_password.encode('utf-8'), 
        bcrypt.gensalt()
    )
```

**Слои защиты:**
1. **Pepper**: секретный ключ на уровне приложения (защита от утечки БД)
2. **Salt**: уникальная случайная строка для каждого пароля (защита от rainbow tables)
3. **Bcrypt**: адаптивная хеш-функция с настраиваемой сложностью (защита от brute-force)

**Преимущества bcrypt:**
- Адаптивная сложность (cost factor)
- Встроенный salt generation
- Защита от timing attacks
- Устойчивость к параллельным вычислениям на GPU

### Two-Factor Authentication (2FA)

Реализация TOTP (Time-based One-Time Password) согласно RFC 6238:

```python
def generate_two_fa_key(self, account_id: int) -> tuple[str, io.BytesIO]:
    two_fa_key = pyotp.random_base32()
    totp_auth = pyotp.totp.TOTP(two_fa_key).provisioning_uri(
        name=f"account_id-{account_id}",
        issuer_name="crmessenger"
    )
    qr_image = qrcode.make(totp_auth)
```

**Workflow:**
1. Генерация случайного Base32-ключа
2. Создание provisioning URI для Google Authenticator
3. Генерация QR-кода для удобной настройки
4. Верификация кода перед активацией (защита от ошибок настройки)

**Безопасность:**
- Коды действительны 30 секунд (стандарт TOTP)
- Защита от replay attacks
- Невозможность восстановления ключа из кодов

### JWT Token Management

Делегирование управления токенами отдельному микросервису:

```python
jwt_token = await self.name_authorization_client.authorization(
    account_id, two_fa_status, "employee"
)
```

**Архитектурные преимущества:**
- Централизованное управление сессиями
- Единая точка для ротации ключей подписи
- Возможность глобального отзыва токенов
- Разделение ответственности (SoC)

**Cookie-based хранение:**
```python
response.set_cookie(
    key="Access-Token",
    value=token,
    httponly=True,    # Защита от XSS
    secure=True,      # Только HTTPS
    samesite="strict" # Защита от CSRF
)
```

## Конфигурация и управление окружениями

### Environment-based Configuration

```python
class Config:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "dev")
        self.db_host = os.getenv("NAME_ACCOUNT_POSTGRES_CONTAINER_NAME")
        self.otlp_host = os.getenv("NAME_OTEL_COLLECTOR_CONTAINER_NAME")
```

**Принципы:**
- **12-Factor App**: конфигурация через переменные окружения
- **Separation of concerns**: разделение конфигурации и кода
- **Environment parity**: одинаковый код для разных окружений
- **Secrets management**: чувствительные данные не в коде

## Асинхронное программирование

### Async/Await Pattern

Полная асинхронность на всех уровнях стека:

```python
async def register(self, login: str, password: str):
    hashed_password = self.__hash_password(password)
    account_id = await self.account_repo.create_account(login, hashed_password)
    jwt_token = await self.name_authorization_client.authorization(...)
```

**Преимущества:**
- **Высокая concurrency**: обработка тысяч одновременных запросов
- **Эффективное использование ресурсов**: потоки не блокируются на I/O
- **Масштабируемость**: меньше ресурсов на обработку запроса
- **Responsive**: быстрое время отклика даже под нагрузкой

**Технологический стек:**
- FastAPI для асинхронного HTTP
- SQLAlchemy async engine для БД
- httpx для асинхронных HTTP-клиентов
- aioredis для асинхронного Redis

## Модели данных и валидация

### Pydantic Models

```python
class RegisterBody(BaseModel):
    login: str
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "login": "user@example.com",
                "password": "securePassword123"
            }
        }
```

**Преимущества:**
- Автоматическая валидация на уровне типов
- Генерация OpenAPI спецификации
- Сериализация/десериализация из коробки
- Понятные сообщения об ошибках валидации

### Domain Models

```python
@dataclass
class Account:
    id: int
    login: str
    password: str
    google_two_fa_key: str
    created_at: datetime
```

**Разделение concerns:**
- Pydantic для API boundary (входящие/исходящие данные)
- Dataclasses для domain models (внутреннее представление)
- Четкое разделение внешних и внутренних представлений

## Производительность и оптимизация

### Batch Processing

```python
BatchSpanProcessor(
    otlp_exporter,
    max_export_batch_size=512,
    max_queue_size=2048,
    export_timeout_millis=5000
)
```

**Стратегия:**
- Батчинг spans/logs/metrics перед отправкой
- Асинхронная экспортация без блокировки main thread
- Настраиваемые размеры батчей и таймауты

### Caching Strategy

Redis используется для:
- Дедупликация алертов (TTL-based expiration)
- Кеширование сессий (будущее расширение)
- Rate limiting (потенциальное применение)

### Database Query Optimization

- Использование prepared statements через SQLAlchemy
- Параметризованные запросы для защиты от SQL-injection
- Индексы на часто запрашиваемых полях (login, id)

## Тестируемость

### Dependency Injection для тестов

Благодаря Protocol-based DI, легко создавать mock-объекты:

```python
class MockAccountRepo(IAccountRepo):
    async def create_account(self, login: str, password: str) -> int:
        return 123  # Fake ID для тестов
```

### Изоляция слоев

Каждый слой может тестироваться независимо:
- Controller тесты: проверка HTTP-интерфейса
- Service тесты: проверка бизнес-логики
- Repository тесты: проверка SQL-запросов

## Операционная готовность

### Health Checks

```python
app.add_api_route(prefix + "/health", heath_check_handler(), methods=["GET"])
```

Эндпоинт для:
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Мониторинга доступности сервиса

### Graceful Shutdown

Корректное завершение работы:
- Закрытие database connections
- Flush pending telemetry data
- Завершение активных запросов

### Database Management Endpoints

```python
app.add_api_route(prefix + "/table/create", create_table_handler(db))
app.add_api_route(prefix + "/table/drop", drop_table_handler(db))
```

Для development/staging окружений (должны быть защищены в production).

## Заключение

Name-Account представляет собой образец современного enterprise-grade микросервиса, демонстрирующий:

### Технологическое превосходство
- Полная асинхронность для максимальной производительности
- OpenTelemetry для world-class observability
- AI-интеграция для проактивного мониторинга

### Архитектурная зрелость
- Clean Architecture для долгосрочной поддерживаемости
- Паттерны устойчивости (Circuit Breaker, Retry, Timeout)
- Separation of Concerns на всех уровнях

### Безопасность
- Defense in Depth для защиты критичных данных
- Современные стандарты криптографии
- Многофакторная аутентификация

### Операционная готовность
- Comprehensive monitoring и alerting
- Database migrations для управления схемой
- Production-ready конфигурация

Такой подход обеспечивает:
- **Высокую доступность**: благодаря паттернам устойчивости
- **Масштабируемость**: через асинхронность и эффективное использование ресурсов
- **Поддерживаемость**: через чистую архитектуру и разделение ответственности
- **Наблюдаемость**: через полную интеграцию с OpenTelemetry
- **Безопасность**: через многоуровневую защиту на каждом этапе

Этот микросервис может служить референсной реализацией для построения современных, надежных и масштабируемых распределенных систем.