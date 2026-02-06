"""
Circuit Breaker pattern implementation.

Prevents cascading failures by failing fast when a service is unhealthy.
"""

import asyncio
import functools
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, name: str, until: datetime) -> None:
        self.name = name
        self.until = until
        super().__init__(f"Circuit breaker '{name}' is open until {until.isoformat()}")


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3
    excluded_exceptions: tuple[type[Exception], ...] = ()


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing fast, requests are rejected immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Usage:
        breaker = CircuitBreaker("my_service")

        async with breaker:
            result = await call_external_service()

        # Or with decorator
        @breaker.protect
        async def my_function():
            ...
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._opened_at: datetime | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        return self._stats

    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        return self._state == CircuitState.HALF_OPEN

    def _should_allow_request(self) -> bool:
        """Determine if a request should be allowed."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            if self._opened_at:
                timeout = timedelta(seconds=self.config.timeout_seconds)
                if datetime.utcnow() >= self._opened_at + timeout:
                    self._transition_to_half_open()
                    return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls

        return False

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self._state = CircuitState.OPEN
        self._opened_at = datetime.utcnow()
        self._half_open_calls = 0

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._stats.consecutive_failures = 0
        self._stats.consecutive_successes = 0

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._half_open_calls = 0
        self._stats.consecutive_failures = 0

    def _record_success(self) -> None:
        """Record a successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._stats.last_success_time = datetime.utcnow()
        self._stats.consecutive_successes += 1
        self._stats.consecutive_failures = 0

        if (
            self._state == CircuitState.HALF_OPEN
            and self._stats.consecutive_successes >= self.config.success_threshold
        ):
            self._transition_to_closed()

    def _record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        if isinstance(exception, self.config.excluded_exceptions):
            return

        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._stats.last_failure_time = datetime.utcnow()
        self._stats.consecutive_failures += 1
        self._stats.consecutive_successes = 0

        if self._state == CircuitState.CLOSED:
            if self._stats.consecutive_failures >= self.config.failure_threshold:
                self._transition_to_open()

        elif self._state == CircuitState.HALF_OPEN:
            self._transition_to_open()

    def _record_rejection(self) -> None:
        """Record a rejected call."""
        self._stats.total_calls += 1
        self._stats.rejected_calls += 1

    async def __aenter__(self) -> "CircuitBreaker":
        """Async context manager entry."""
        async with self._lock:
            if not self._should_allow_request():
                self._record_rejection()
                timeout = timedelta(seconds=self.config.timeout_seconds)
                until = (self._opened_at or datetime.utcnow()) + timeout
                raise CircuitBreakerOpenError(self.name, until)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        return self

    async def __aexit__(
        self,
        exc_type: type[Exception] | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> bool:
        """Async context manager exit."""
        async with self._lock:
            if exc_val is None:
                self._record_success()
            else:
                self._record_failure(exc_val)

        return False

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to protect a function with this circuit breaker."""

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            async with self:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

        return wrapper

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._half_open_calls = 0
        self._stats = CircuitStats()

    def force_open(self) -> None:
        """Force the circuit to open state."""
        self._transition_to_open()

    def force_close(self) -> None:
        """Force the circuit to closed state."""
        self._transition_to_closed()

    def to_dict(self) -> dict[str, Any]:
        """Serialize circuit breaker state."""
        return {
            "name": self.name,
            "state": self._state.value,
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rejected_calls": self._stats.rejected_calls,
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
            },
            "opened_at": self._opened_at.isoformat() if self._opened_at else None,
        }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Usage:
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("my_service")
    """

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get(self, name: str) -> CircuitBreaker | None:
        """Get a circuit breaker by name."""
        return self._breakers.get(name)

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def remove(self, name: str) -> bool:
        """Remove a circuit breaker."""
        if name in self._breakers:
            del self._breakers[name]
            return True
        return False

    def list_all(self) -> dict[str, dict[str, Any]]:
        """List all circuit breakers with their states."""
        return {name: breaker.to_dict() for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()
