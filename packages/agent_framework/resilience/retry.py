"""
Retry policies and decorators for resilient execution.

Provides configurable retry logic with exponential backoff.
"""

import asyncio
import functools
import random
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (including first try)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff (e.g., 2 for doubling)
        jitter: Add random jitter to delays (0.0 to 1.0)
        retryable_exceptions: Exception types that should trigger retry
        non_retryable_exceptions: Exception types that should NOT retry
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.1
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should trigger a retry."""
        if attempt >= self.max_attempts:
            return False

        if isinstance(exception, self.non_retryable_exceptions):
            return False

        return isinstance(exception, self.retryable_exceptions)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


class ExponentialBackoff:
    """
    Exponential backoff calculator with jitter.

    Usage:
        backoff = ExponentialBackoff()
        for attempt in range(5):
            delay = backoff.get_delay(attempt)
            await asyncio.sleep(delay)
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: float = 0.1,
    ) -> None:
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt (0-indexed)."""
        delay = self.base_delay * (self.exponential_base**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


@dataclass
class RetryResult:
    """Result of a retry operation."""

    success: bool
    result: Any = None
    exception: Optional[Exception] = None
    attempts: int = 0
    total_delay: float = 0.0
    attempt_errors: List[Tuple[int, Exception, float]] = field(default_factory=list)


async def retry_with_policy(
    func: Callable[..., T],
    policy: RetryPolicy,
    *args: Any,
    on_retry: Optional[Callable[[int, Exception, float], Any]] = None,
    **kwargs: Any,
) -> RetryResult:
    """
    Execute a function with retry logic.

    Args:
        func: Async function to execute
        policy: Retry policy configuration
        *args: Arguments to pass to func
        on_retry: Optional callback called before each retry
        **kwargs: Keyword arguments to pass to func

    Returns:
        RetryResult with success status and result/exception
    """
    result = RetryResult(success=False)
    total_delay = 0.0

    for attempt in range(1, policy.max_attempts + 1):
        result.attempts = attempt

        try:
            if asyncio.iscoroutinefunction(func):
                value = await func(*args, **kwargs)
            else:
                value = func(*args, **kwargs)

            result.success = True
            result.result = value
            result.total_delay = total_delay
            return result

        except Exception as e:
            result.attempt_errors.append((attempt, e, total_delay))

            if not policy.should_retry(e, attempt):
                result.exception = e
                result.total_delay = total_delay
                return result

            delay = policy.get_delay(attempt)
            total_delay += delay

            if on_retry:
                callback_result = on_retry(attempt, e, delay)
                if asyncio.iscoroutine(callback_result):
                    await callback_result

            await asyncio.sleep(delay)

    result.total_delay = total_delay
    return result


def with_retry(
    policy: Optional[RetryPolicy] = None,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for adding retry logic to async functions.

    Usage:
        @with_retry(max_attempts=3, base_delay=1.0)
        async def my_function():
            ...
    """
    if policy is None:
        policy = RetryPolicy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            retryable_exceptions=retryable_exceptions,
        )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            result = await retry_with_policy(func, policy, *args, **kwargs)

            if result.success:
                return result.result

            if result.exception:
                raise result.exception

            raise RuntimeError(f"Retry failed after {result.attempts} attempts")

        return wrapper

    return decorator
