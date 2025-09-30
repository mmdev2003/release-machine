import httpx
import asyncio
import random
import weakref
from pathlib import Path
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Any, AsyncIterator, Callable
from tenacity import stop_after_attempt, AsyncRetrying, retry_if_exception_type

from opentelemetry import propagate

from internal import interface


class CircuitBreaker:
    def __init__(
            self,
            failure_threshold: int = 5,
            recovery_timeout: int = 60,
            expected_exceptions: tuple[type[Exception], ...] = (httpx.HTTPError,),
            logger: interface.IOtelLogger = None
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        self._failures: deque[datetime] = deque(maxlen=failure_threshold)
        self._last_failure_time: Optional[datetime] = None
        self._state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()
        self.logger = logger

    @property
    def state(self) -> str:
        return self._state

    def _log_state_change(self, old_state: str, new_state: str, context: str = ""):
        self.logger.warning(
            f"Circuit Breaker изменил состояние: {old_state} -> {new_state}. "
            f"количество ошибок: {len(self._failures)}/{self.failure_threshold}. "
            f"Подробности: {context}"
        )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            current_state = self._state

            if self._state == "open":
                time_since_failure = (datetime.now() - self._last_failure_time
                                      if self._last_failure_time else timedelta(0))

                if (self._last_failure_time and
                        time_since_failure > timedelta(seconds=self.recovery_timeout)):
                    old_state = self._state
                    self._state = "half-open"
                    if self.logger is not None:
                        self._log_state_change(
                            old_state,
                            self._state,
                            f"Восстановление после {time_since_failure.total_seconds()} секунд"
                        )
                else:
                    remaining_time = self.recovery_timeout - time_since_failure.total_seconds()
                    if self.logger is not None:
                        self.logger.warning(
                            f"Circuit breaker включен. Ошибок: {len(self._failures)}/{self.failure_threshold}. "
                            f"Восстановление через {remaining_time:.1f} секунд"
                        )
                    raise Exception(f"Circuit breaker is OPEN (failures: {len(self._failures)})")

        try:
            if current_state == "half-open":
                if self.logger is not None:
                    self.logger.debug("Circuit breaker в HALF-OPEN состоянии. Проверка состояния")

            result = await func(*args, **kwargs)

            async with self._lock:
                if self._state == "half-open":
                    old_state = self._state
                    self._state = "closed"
                    self._failures.clear()
                    if self.logger is not None:
                        self._log_state_change(
                            old_state, self._state,
                            "Восстановились. Circuit breaker выключен"
                        )

            return result

        except self.expected_exceptions as e:
            await self._record_failure()
            raise

    async def _record_failure(self):
        async with self._lock:
            self._failures.append(datetime.now())
            self._last_failure_time = datetime.now()
            old_state = self._state
            if self.logger is not None:
                self.logger.warning(
                    f"Circuit breaker обнаружил проблему. Количество ошибок: {len(self._failures)}/{self.failure_threshold}"
                )

            if len(self._failures) >= self.failure_threshold:
                self._state = "open"
                if self.logger is not None:
                    self._log_state_change(old_state, self._state)

    def reset(self):
        old_state = self._state
        self._failures.clear()
        self._last_failure_time = None
        self._state = "closed"

        if old_state != "closed":
            if self.logger is not None:
                self._log_state_change(old_state, self._state, "Ручное выключение")


class ExponentialBackoffWithJitter:
    def __init__(self, base_delay: float = 0.1, max_delay: float = 10.0, jitter: float = 0.1):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def __call__(self, retry_state) -> float:
        delay = min(
            self.base_delay * (2 ** (retry_state.attempt_number - 1)),
            self.max_delay
        )

        jitter_value = delay * self.jitter * random.random()
        return delay + jitter_value


class AsyncHTTPClient:
    _instances: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
    _lock = asyncio.Lock()

    def __new__(
            cls,
            host: str,
            port: int,
            prefix: str = "",
            headers: dict = None,
            cookies: dict = None,
            use_tracing: bool = False,
            use_http2: bool = True,
            use_https: bool = False,
            timeout: float = 30,
            max_connections: int = 100,
            max_keepalive_connections: int = 20,
            retry_count: int = 3,
            retry_wait_multiplier: float = 0.3,
            retry_wait_min: float = 0.1,
            retry_wait_max: float = 10,
            circuit_breaker_enabled: bool = True,
            circuit_breaker_failure_threshold: int = 5,
            circuit_breaker_recovery_timeout: int = 60,
            logger: interface.IOtelLogger = None,
    ):
        protocol = "https" if use_https else "http"
        base_url = f"{protocol}://{host}:{port}{prefix}"

        if base_url in cls._instances:
            return cls._instances[base_url]

        instance = super().__new__(cls)
        cls._instances[base_url] = instance
        return instance

    def __init__(
            self,
            host: str,
            port: int,
            prefix: str = "",
            headers: dict = None,
            cookies: dict = None,
            use_tracing: bool = False,
            use_http2: bool = False,
            use_https: bool = False,
            timeout: float = 30,
            max_connections: int = 100,
            max_keepalive_connections: int = 20,
            retry_count: int = 3,
            retry_wait_multiplier: float = 0.3,
            retry_wait_min: float = 0.1,
            retry_wait_max: float = 10,
            circuit_breaker_enabled: bool = True,
            circuit_breaker_failure_threshold: int = 5,
            circuit_breaker_recovery_timeout: int = 60,
            logger: interface.IOtelLogger = None,
    ):
        if hasattr(self, "_initialized"):
            return

        self._initialized = True

        protocol = "https" if use_https else "http"
        self.base_url = f"{protocol}://{host}:{port}{prefix}"

        self.default_headers = headers or {}
        self.default_cookies = cookies or {}

        self.logger = logger
        self.use_tracing = use_tracing

        self.session: Optional[httpx.AsyncClient] = None
        self.session_lock = asyncio.Lock()

        self.circuit_breaker: Optional[CircuitBreaker] = None
        if circuit_breaker_enabled:
            self._circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_failure_threshold,
                recovery_timeout=circuit_breaker_recovery_timeout
            )

        self.timeout = timeout
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.retry_count = retry_count
        self.retry_wait_multiplier = retry_wait_multiplier
        self.retry_wait_min = retry_wait_min
        self.retry_wait_max = retry_wait_max
        self.use_http2 = use_http2
        self.backoff = ExponentialBackoffWithJitter(
            base_delay=self.retry_wait_min,
            max_delay=self.retry_wait_max
        )

    async def _get_session(self) -> httpx.AsyncClient:
        if self.session is None or self.session.is_closed:
            async with self.session_lock:
                if self.session is None or self.session.is_closed:
                    self.session = self._create_session()
        return self.session

    def _create_session(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.default_headers,
            cookies=self.default_cookies,
            timeout=self.timeout,
            http2=self.use_http2,
            limits=httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections
            ),
            follow_redirects=True
        )

    async def close(self):
        if self.session and not self.session.is_closed:
            await self.session.aclose()
            self.session = None
            self.logger.info("session_closed")

    async def __aenter__(self) -> 'AsyncHTTPClient':
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @classmethod
    async def cleanup_all(cls):
        for instance in list(cls._instances.values()):
            await instance.close()

    def _create_retry_strategy(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(self.retry_count),
            wait=self.backoff,
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True
        )

    async def _execute_request(
            self,
            method: str,
            url: str,
            **kwargs
    ) -> httpx.Response:
        try:
            session = await self._get_session()

            headers = {**self.default_headers, **kwargs.pop('headers', {})}
            cookies = {**self.default_cookies, **kwargs.pop('cookies', {})}

            if self.use_tracing:
                propagate.inject(headers)

            if self._circuit_breaker:
                response = await self._circuit_breaker.call(
                    session.request,
                    method,
                    url,
                    headers=headers,
                    cookies=cookies,
                    **kwargs
                )
            else:
                response = await session.request(
                    method,
                    url,
                    headers=headers,
                    cookies=cookies,
                    **kwargs
                )

            response.raise_for_status()
            return response

        except Exception as e:
            raise

    async def _request_with_retry(
            self,
            method: str,
            url: str,
            **kwargs
    ) -> httpx.Response | None:
        start_time = datetime.now()

        last_exception = None
        retry_count = 0

        async for attempt in self._create_retry_strategy():
            with attempt:
                retry_count = attempt.retry_state.attempt_number - 1

                if retry_count > 0:
                    wait_time = self.backoff(attempt.retry_state)
                    self.logger.warning(
                        f"Попытка #{retry_count} для {method} {url}"
                        f"после {wait_time:.2f}с ожидания. "
                        f"Последняя ошибка: {last_exception.__class__.__name__}: {str(last_exception)}"
                    )

                try:
                    response = await self._execute_request(method, url, **kwargs)

                    elapsed = (datetime.now() - start_time).total_seconds()
                    if retry_count > 0:
                        self.logger.info(
                            f"Запрос {method} {url} выполнен успешно "
                            f"после {retry_count} попыток в течение {elapsed:.2f}с "
                            f"(status: {response.status_code})"
                        )

                    return response

                except Exception as e:
                    last_exception = e
                    elapsed = (datetime.now() - start_time).total_seconds()

                    if retry_count < self.retry_count - 1:  # Есть еще попытки
                        next_delay = self.backoff(attempt.retry_state)
                        self.logger.warning(
                            f"Запрос {method} {url} неуспешен "
                            f"(попытка {retry_count + 1}/{self.retry_count}) "
                            f"за {elapsed:.2f}с. Следующая попытка через {next_delay:.2f}с. "
                            f"Ошибка: {e.__class__.__name__}: {str(e)}"
                        )
                    else:
                        self.logger.error(
                            f"Запрос {method} {url} окончательно провален "
                            f"после {retry_count + 1} попыток за {elapsed:.2f}с. "
                            f"Ошибка: {e.__class__.__name__}: {str(e)}"
                        )

                    raise
        return None

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry('GET', url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry('POST', url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry('PUT', url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry('PATCH', url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self._request_with_retry('DELETE', url, **kwargs)

    async def stream_get(
            self,
            url: str,
            chunk_size: int = 8192,
            **kwargs
    ) -> AsyncIterator[bytes]:
        session = await self._get_session()

        try:
            async with session.stream('GET', url, **kwargs) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size):
                    yield chunk
        except Exception as e:
            raise

    async def download_file(
            self,
            url: str,
            file_path: Path,
            chunk_size: int = 8192,
            progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        import aiofiles

        session = await self._get_session()
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with session.stream('GET', url) as response:
                response.raise_for_status()
                total = int(response.headers.get('content-length', 0))

                async with aiofiles.open(file_path, 'wb') as file:
                    downloaded = 0
                    async for chunk in response.aiter_bytes(chunk_size):
                        await file.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback:
                            progress_callback(downloaded, total)

        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise

    def reset_circuit_breaker(self):
        if self._circuit_breaker:
            self._circuit_breaker.reset()

    @property
    def circuit_breaker_state(self) -> str | None:
        return self._circuit_breaker.state if self._circuit_breaker else None