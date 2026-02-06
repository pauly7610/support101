"""
LLM helper utilities for agent framework.

Provides per-call retry logic with exponential backoff and
EvalAI cost/decision tracking helpers for use inside agent steps.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


def llm_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 15.0,
    backoff_factor: float = 2.0,
) -> Callable:
    """
    Decorator for retrying async LLM calls with exponential backoff.

    Usage:
        @llm_retry(max_attempts=3)
        async def _analyze_intent(self, query: str) -> Dict[str, Any]:
            chain = self.INTENT_PROMPT | self.llm
            result = await chain.ainvoke({"query": query})
            return json.loads(result.content)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.warning(
                            "LLM call %s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            e,
                        )
                        raise
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    logger.debug(
                        "LLM call %s attempt %d/%d failed (%s), retrying in %.1fs",
                        func.__name__,
                        attempt,
                        max_attempts,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


async def track_llm_cost(
    tracer: Optional[Any],
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: Optional[int] = None,
) -> None:
    """
    Record LLM token cost to EvalAI tracer if available.

    Safe to call even when tracer is None or disabled — silently no-ops.

    Args:
        tracer: EvalAITracer instance (or None)
        provider: LLM provider name (e.g. "openai", "anthropic")
        model: Model name (e.g. "gpt-4o", "gpt-3.5-turbo")
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        duration_ms: Optional call duration in milliseconds
    """
    if tracer is None:
        return
    try:
        from ..observability.evalai_tracer import EvalAICostRecord

        cost_record = EvalAICostRecord(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        await tracer.record_cost(cost_record)
    except Exception as e:
        logger.debug("track_llm_cost failed: %s", e)


async def track_agent_decision(
    tracer: Optional[Any],
    agent_name: str,
    decision_type: str,
    chosen: str,
    alternatives: Optional[list] = None,
    confidence: int = 80,
    reasoning: str = "",
) -> None:
    """
    Record an agent decision to EvalAI tracer if available.

    Safe to call even when tracer is None or disabled — silently no-ops.

    Args:
        tracer: EvalAITracer instance (or None)
        agent_name: Name of the agent making the decision
        decision_type: Type of decision (e.g. "route", "escalate", "classify")
        chosen: The chosen action/option
        alternatives: List of alternative options considered
        confidence: Confidence score 0-100
        reasoning: Brief explanation of why this decision was made
    """
    if tracer is None:
        return
    try:
        from ..observability.evalai_tracer import EvalAIDecision

        decision = EvalAIDecision(
            agent=agent_name,
            type=decision_type,
            chosen=chosen,
            alternatives=alternatives or [],
            confidence=confidence,
            reasoning=reasoning,
        )
        await tracer.record_decision(decision)
    except Exception as e:
        logger.debug("track_agent_decision failed: %s", e)


class LLMCallTimer:
    """
    Context manager for timing LLM calls and tracking costs.

    Usage:
        async with LLMCallTimer(tracer, "openai", "gpt-4o") as timer:
            result = await chain.ainvoke({"query": query})
            timer.set_tokens(input_tokens=500, output_tokens=200)
    """

    def __init__(
        self,
        tracer: Optional[Any] = None,
        provider: str = "openai",
        model: str = "gpt-4o",
    ) -> None:
        self._tracer = tracer
        self._provider = provider
        self._model = model
        self._start: float = 0
        self._input_tokens: int = 0
        self._output_tokens: int = 0

    def set_tokens(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens

    async def __aenter__(self) -> "LLMCallTimer":
        self._start = time.monotonic()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = int((time.monotonic() - self._start) * 1000)
        if self._input_tokens > 0 or self._output_tokens > 0:
            await track_llm_cost(
                self._tracer,
                self._provider,
                self._model,
                self._input_tokens,
                self._output_tokens,
                duration_ms,
            )
