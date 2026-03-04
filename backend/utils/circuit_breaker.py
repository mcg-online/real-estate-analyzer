"""Circuit breaker implementation for protecting external service calls.

States
------
CLOSED   - Normal operation. Requests pass through. Failures are tracked.
OPEN     - Circuit is tripped. Requests are immediately rejected to allow the
           downstream service time to recover.
HALF_OPEN - A single probe request is allowed through to test recovery. If it
            succeeds, the circuit closes; if it fails, the circuit re-opens and
            the recovery timeout resets.

Usage example::

    from utils.circuit_breaker import CircuitBreaker, CircuitOpenError

    breaker = CircuitBreaker(name="zillow", failure_threshold=5, recovery_timeout=300)

    try:
        result = breaker.call(requests.get, url, headers=headers, timeout=10)
    except CircuitOpenError:
        logger.warning("Circuit open; skipping request to Zillow")
        result = None
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(Exception):
    """Raised when a call is attempted while the circuit breaker is OPEN."""


class CircuitBreaker:
    """A simple, thread-safe circuit breaker.

    Parameters
    ----------
    name:
        Human-readable label used in log messages.
    failure_threshold:
        Number of consecutive failures that trip the circuit to OPEN.
        Defaults to 5.
    recovery_timeout:
        Seconds to wait in OPEN state before moving to HALF_OPEN to probe
        recovery.  Defaults to 300 (5 minutes).
    expected_exception:
        The exception type (or tuple of types) that counts as a failure.
        Defaults to ``Exception`` (all exceptions).
    """

    def __init__(
        self,
        name: str = "circuit_breaker",
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,
        expected_exception: type | tuple[type, ...] = Exception,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._opened_at: float | None = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Return the current state, transitioning OPEN -> HALF_OPEN when
        the recovery timeout has elapsed."""
        if (
            self._state is CircuitState.OPEN
            and self._opened_at is not None
            and (time.monotonic() - self._opened_at) >= self.recovery_timeout
        ):
            logger.info(
                "CircuitBreaker[%s]: recovery timeout elapsed; transitioning OPEN -> HALF_OPEN",
                self.name,
            )
            self._state = CircuitState.HALF_OPEN
        return self._state

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Invoke *func* with *args*/*kwargs*, applying circuit breaker logic.

        Parameters
        ----------
        func:
            Any callable to protect.
        *args, **kwargs:
            Forwarded to *func*.

        Returns
        -------
        Any
            The return value of *func*.

        Raises
        ------
        CircuitOpenError
            When the circuit is OPEN and the recovery timeout has not yet
            elapsed.
        Exception
            Any exception raised by *func* that matches ``expected_exception``
            is re-raised after recording the failure.  Other exceptions are
            re-raised immediately without incrementing the failure counter.
        """
        current_state = self.state  # Triggers OPEN -> HALF_OPEN transition check.

        if current_state is CircuitState.OPEN:
            raise CircuitOpenError(
                f"CircuitBreaker[{self.name}] is OPEN; call rejected. "
                f"Recovery in {self._seconds_until_recovery():.0f}s."
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as exc:
            self._on_failure()
            raise exc

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _on_success(self) -> None:
        if self._state is CircuitState.HALF_OPEN:
            logger.info(
                "CircuitBreaker[%s]: probe succeeded; transitioning HALF_OPEN -> CLOSED",
                self.name,
            )
        elif self._failure_count > 0:
            logger.debug(
                "CircuitBreaker[%s]: success; resetting failure count from %d",
                self.name,
                self._failure_count,
            )
        self._failure_count = 0
        self._opened_at = None
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        logger.warning(
            "CircuitBreaker[%s]: failure recorded (%d/%d)",
            self.name,
            self._failure_count,
            self.failure_threshold,
        )

        if self._state is CircuitState.HALF_OPEN:
            # Probe failed — re-open immediately and restart the timeout.
            logger.warning(
                "CircuitBreaker[%s]: probe failed; transitioning HALF_OPEN -> OPEN",
                self.name,
            )
            self._trip()
        elif self._failure_count >= self.failure_threshold:
            logger.error(
                "CircuitBreaker[%s]: failure threshold reached (%d); transitioning CLOSED -> OPEN",
                self.name,
                self.failure_threshold,
            )
            self._trip()

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _seconds_until_recovery(self) -> float:
        if self._opened_at is None:
            return 0.0
        elapsed = time.monotonic() - self._opened_at
        return max(0.0, self.recovery_timeout - elapsed)

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state.

        Useful in tests or after a confirmed recovery.
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
        logger.info("CircuitBreaker[%s]: manually reset to CLOSED", self.name)

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name!r}, state={self._state.value}, "
            f"failures={self._failure_count}/{self.failure_threshold})"
        )
