import asyncio
import secrets
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

from core.config import settings

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


@dataclass(slots=True)
class CircuitBreaker:
    name: str
    failure_threshold: int = settings.circuit_breaker_failure_threshold
    reset_seconds: int = settings.circuit_breaker_reset_seconds
    failures: deque[float] = field(default_factory=deque)
    opened_at: float | None = None

    def allow_request(self) -> bool:
        if self.opened_at is None:
            return True

        if time.monotonic() - self.opened_at >= self.reset_seconds:
            self.opened_at = None
            self.failures.clear()
            return True

        return False

    def record_success(self) -> None:
        self.failures.clear()
        self.opened_at = None

    def record_failure(self) -> None:
        now = time.monotonic()
        self.failures.append(now)

        while self.failures and now - self.failures[0] > 60:
            self.failures.popleft()

        if len(self.failures) >= self.failure_threshold:
            self.opened_at = now

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "state": "open" if self.opened_at else "closed",
            "failure_count": len(self.failures),
            "reset_seconds": self.reset_seconds,
        }


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name)
    return _breakers[name]


def circuit_status() -> list[dict]:
    return [breaker.snapshot() for breaker in _breakers.values()]


async def with_resilience(
    name: str,
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int | None = None,
    timeout_seconds: float | None = None,
) -> T:
    breaker = get_breaker(name)
    if not breaker.allow_request():
        raise CircuitOpenError(f"Circuit for {name} is open")

    max_attempts = attempts or settings.agent_retry_attempts
    timeout = timeout_seconds or settings.agent_timeout_seconds
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = await asyncio.wait_for(operation(), timeout=timeout)
            breaker.record_success()
            return result
        except Exception as exc:
            last_error = exc
            breaker.record_failure()
            if attempt >= max_attempts:
                break

            backoff = min(4.0, 0.25 * (2 ** (attempt - 1))) + secrets.randbelow(100) / 1000
            await asyncio.sleep(backoff)

    if last_error is None:
        raise RuntimeError(f"{name} failed without an exception")
    raise last_error
