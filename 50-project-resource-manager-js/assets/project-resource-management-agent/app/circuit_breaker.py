"""A small, dependency-free circuit breaker for per-model fallback.

The agent tries a chain of models (primary, then fallbacks). Without any memory,
a model that is consistently failing (e.g. a timeout on every request) is retried
on every single request, and the caller pays the full timeout each time before
falling through to the next model. This breaker gives the chain a short memory:
after a model fails enough times in a row it is "opened" and skipped for a cooldown
window, so the agent goes straight to the next model instead of waiting again.

The breaker is intentionally tiny and stdlib-only to keep the generated agent
generic and lightweight. It holds no LLM state and makes no network calls.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class _ModelState:
    """Failure bookkeeping for a single model."""

    consecutive_failures: int = 0
    # Monotonic timestamp until which the model stays skipped; None means available.
    open_until: float | None = None
    # True after a cooldown elapses: the next attempt is a probe that either
    # closes the breaker (on success) or re-opens it (on failure).
    half_open: bool = False


class CircuitBreaker:
    """Tracks per-model failures and decides whether a model may be attempted.

    States per model:
      - closed:    normal operation; failures are counted.
      - open:      skipped until the cooldown elapses.
      - half-open: cooldown elapsed; one probe attempt is allowed. A success
                   closes the breaker; a failure re-opens it for another cooldown.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        # A threshold below 1 would open the breaker before any failure, which is
        # never intended; clamp so misconfiguration cannot wedge every model shut.
        self._failure_threshold = max(1, failure_threshold)
        self._cooldown_seconds = max(0.0, cooldown_seconds)
        self._time_fn = time_fn
        self._states: dict[str, _ModelState] = {}
        self._lock = asyncio.Lock()

    async def allows(self, model: str) -> bool:
        """Return True if the model may be attempted now.

        When an open model's cooldown has elapsed, this transitions it to
        half-open and returns True so a single probe attempt can run.
        """
        async with self._lock:
            state = self._states.get(model)
            if state is None or state.open_until is None:
                return True
            if self._time_fn() >= state.open_until:
                # Cooldown elapsed: allow one probe attempt.
                state.open_until = None
                state.half_open = True
                return True
            return False

    async def record_success(self, model: str) -> None:
        """Reset a model to healthy after a successful call."""
        async with self._lock:
            self._states[model] = _ModelState()

    async def record_failure(self, model: str) -> None:
        """Record a failure, opening the breaker once the threshold is reached."""
        async with self._lock:
            state = self._states.setdefault(model, _ModelState())
            if state.half_open:
                # The probe failed: re-open immediately for another cooldown.
                state.half_open = False
                state.consecutive_failures = 0
                state.open_until = self._time_fn() + self._cooldown_seconds
                return
            state.consecutive_failures += 1
            if state.consecutive_failures >= self._failure_threshold:
                # Reset the streak as the breaker opens so a stale count cannot
                # linger across the cooldown and re-trip the threshold on the
                # first post-cooldown probe. Re-opening after a failed probe is
                # governed solely by the half-open branch above, keeping the two
                # transitions independent.
                state.consecutive_failures = 0
                state.open_until = self._time_fn() + self._cooldown_seconds
