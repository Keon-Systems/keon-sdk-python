"""
Keon Python SDK

Thin, safe-by-default client for Keon Runtime.

Features:
- Strict validation (CorrelationId, receipt requirements)
- Automatic retries for transient failures
- Structured error handling
- Type-safe contracts

Example:
    ```python
    from keon_sdk import KeonClient

    async with KeonClient(
        base_url="https://api.keon.systems/runtime/v1",
        api_key="your-api-key",
    ) as client:
        # Decide
        receipt = await client.decide(
            tenant_id="tenant-123",
            actor_id="user-456",
            action="execute_workflow",
            resource_type="workflow",
            resource_id="workflow-789",
        )

        # Execute
        if receipt.decision == "allow":
            result = await client.execute(
                receipt=receipt,
                action="execute_workflow",
                parameters={"workflowId": "workflow-789"},
            )
    ```
"""

from .client import KeonClient
from .contracts import (
    DecideRequest,
    DecideResponse,
    DecisionEnum,
    DecisionReceipt,
    ErrorDetail,
    ErrorResponse,
    ExecuteRequest,
    ExecuteResponse,
    ExecutionResult,
    ExecutionStatus,
)
from .errors import (
    ExecutionDeniedError,
    InvalidCorrelationIdError,
    InvalidReceiptError,
    KeonError,
    MissingReceiptError,
    NetworkError,
    RateLimitError,
    RetryExhaustedError,
    ServerError,
    ValidationError,
)
from .gateway import BaseRuntimeGateway, RuntimeGateway
from .http_gateway import HttpRuntimeGateway
from .retry import RetryPolicy
from .canonicalize import (
    canonicalize,
    canonicalize_to_string,
    canonicalize_bytes,
    validate_integrity,
)

__version__ = "1.0.0"

__all__ = [
    # Client
    "KeonClient",
    # Contracts
    "DecideRequest",
    "DecideResponse",
    "DecisionReceipt",
    "DecisionEnum",
    "ExecuteRequest",
    "ExecuteResponse",
    "ExecutionResult",
    "ExecutionStatus",
    "ErrorResponse",
    "ErrorDetail",
    # Errors
    "KeonError",
    "ValidationError",
    "InvalidCorrelationIdError",
    "MissingReceiptError",
    "InvalidReceiptError",
    "ExecutionDeniedError",
    "NetworkError",
    "RetryExhaustedError",
    "ServerError",
    "RateLimitError",
    # Gateway
    "RuntimeGateway",
    "BaseRuntimeGateway",
    "HttpRuntimeGateway",
    # Retry
    "RetryPolicy",
    # Canonicalization (RFC 8785)
    "canonicalize",
    "canonicalize_to_string",
    "canonicalize_bytes",
    "validate_integrity",
]
