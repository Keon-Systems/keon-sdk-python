"""
Keon SDK Errors

Typed exceptions for error handling.
"""

from typing import Any, Dict, Optional


class KeonError(Exception):
    """Base exception for all Keon SDK errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or "UNKNOWN_ERROR"
        self.details = details or {}


class ValidationError(KeonError):
    """Request validation failed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class InvalidCorrelationIdError(ValidationError):
    """CorrelationId does not match canonical form."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__(
            f"CorrelationId must match canonical form: t:<TenantId>|c:<uuidv7>, got: {correlation_id}",
            details={"correlationId": correlation_id},
        )


class MissingReceiptError(ValidationError):
    """DecisionReceiptId is required but missing."""

    def __init__(self) -> None:
        super().__init__(
            "Execute requires DecisionReceiptId (hard fail if absent)",
            details={"required": True},
        )


class InvalidReceiptError(KeonError):
    """DecisionReceiptId is invalid or expired."""

    def __init__(self, receipt_id: str, reason: Optional[str] = None) -> None:
        super().__init__(
            f"DecisionReceiptId is invalid or expired: {receipt_id}",
            code="INVALID_DECISION_RECEIPT",
            details={"receiptId": receipt_id, "reason": reason or "Unknown"},
        )


class ExecutionDeniedError(KeonError):
    """Execution was denied by policy."""

    def __init__(self, receipt_id: str, reason: Optional[str] = None) -> None:
        super().__init__(
            f"Execution denied by policy: {reason or 'See decision receipt'}",
            code="EXECUTION_DENIED",
            details={"receiptId": receipt_id, "reason": reason},
        )


class NetworkError(KeonError):
    """Network-related error (connection, timeout, etc.)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, code="NETWORK_ERROR", details=details)


class RetryExhaustedError(KeonError):
    """Retries exhausted for transient failure."""

    def __init__(
        self, original_error: Exception, attempts: int, details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            f"Retries exhausted after {attempts} attempts: {original_error}",
            code="RETRY_EXHAUSTED",
            details={**(details or {}), "attempts": attempts, "originalError": str(original_error)},
        )


class ServerError(KeonError):
    """Server-side error (5xx)."""

    def __init__(
        self, status_code: int, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            f"Server error ({status_code}): {message}",
            code="SERVER_ERROR",
            details={**(details or {}), "statusCode": status_code},
        )


class RateLimitError(KeonError):
    """Rate limit exceeded (429)."""

    def __init__(self, retry_after: Optional[int] = None) -> None:
        super().__init__(
            f"Rate limit exceeded. Retry after: {retry_after or 'unknown'}",
            code="RATE_LIMIT_EXCEEDED",
            details={"retryAfter": retry_after},
        )
