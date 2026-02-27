"""
Retry policy for transient failures.

Safe-by-default retry with exponential backoff.
"""

from typing import Callable, Type

from tenacity import (
    RetryCallState,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .errors import NetworkError, RateLimitError, ServerError


def is_transient_error(exception: BaseException) -> bool:
    """
    Determine if an error is transient and should be retried.

    Transient errors:
    - NetworkError (connection issues, timeouts)
    - ServerError with 5xx status codes
    - RateLimitError (429)

    Non-transient errors (do NOT retry):
    - ValidationError
    - InvalidCorrelationIdError
    - MissingReceiptError
    - ExecutionDeniedError
    - Client errors (4xx except 429)
    """
    if isinstance(exception, (NetworkError, RateLimitError)):
        return True

    if isinstance(exception, ServerError):
        # Retry 5xx errors
        status_code = exception.details.get("statusCode", 0)
        return 500 <= status_code < 600

    return False


class RetryPolicy:
    """
    Retry policy configuration.

    Defaults:
    - Max attempts: 3
    - Exponential backoff: 1s, 2s, 4s
    - Only retries transient errors
    """

    def __init__(
        self,
        max_attempts: int = 3,
        min_wait_seconds: float = 1.0,
        max_wait_seconds: float = 10.0,
        multiplier: float = 2.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.min_wait_seconds = min_wait_seconds
        self.max_wait_seconds = max_wait_seconds
        self.multiplier = multiplier

    @classmethod
    def default(cls) -> "RetryPolicy":
        """Default retry policy with safe defaults."""
        return cls(
            max_attempts=3,
            min_wait_seconds=1.0,
            max_wait_seconds=10.0,
            multiplier=2.0,
        )

    @classmethod
    def no_retry(cls) -> "RetryPolicy":
        """No retry policy - fail immediately."""
        return cls(max_attempts=1)

    @classmethod
    def aggressive(cls) -> "RetryPolicy":
        """Aggressive retry for high-availability scenarios."""
        return cls(
            max_attempts=5,
            min_wait_seconds=0.5,
            max_wait_seconds=30.0,
            multiplier=2.0,
        )

    def to_tenacity_kwargs(self) -> dict:
        """Convert to tenacity retry decorator kwargs."""
        return {
            "stop": stop_after_attempt(self.max_attempts),
            "wait": wait_exponential(
                min=self.min_wait_seconds,
                max=self.max_wait_seconds,
                multiplier=self.multiplier,
            ),
            "retry": retry_if_exception(is_transient_error),
            "reraise": True,
        }
