"""
HTTP Runtime Gateway implementation.

Uses httpx for async HTTP communication with Keon Runtime.
"""

import logging
from typing import Optional

import httpx
from pydantic import ValidationError as PydanticValidationError
from tenacity import AsyncRetrying

from .contracts import DecideRequest, DecideResponse, ExecuteRequest, ExecuteResponse, ErrorResponse
from .errors import (
    ExecutionDeniedError,
    InvalidReceiptError,
    KeonError,
    NetworkError,
    RateLimitError,
    RetryExhaustedError,
    ServerError,
    ValidationError,
)
from .gateway import BaseRuntimeGateway
from .retry import RetryPolicy

logger = logging.getLogger(__name__)


class HttpRuntimeGateway(BaseRuntimeGateway):
    """
    HTTP implementation of RuntimeGateway.

    Features:
    - Automatic retries for transient failures
    - Idempotency via CorrelationId header
    - Structured error mapping
    - Connection pooling via httpx
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        retry_policy: Optional[RetryPolicy] = None,
        timeout: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initialize HTTP gateway.

        Args:
            base_url: Base URL for Keon Runtime API (e.g., https://api.keon.systems/runtime/v1)
            api_key: Optional API key for X-API-Key header
            bearer_token: Optional bearer token for Authorization header
            retry_policy: Retry policy (default: RetryPolicy.default())
            timeout: Request timeout in seconds (default: 30.0)
            http_client: Optional custom httpx.AsyncClient
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.retry_policy = retry_policy or RetryPolicy.default()
        self.timeout = timeout

        # Create HTTP client if not provided
        if http_client:
            self._http_client = http_client
            self._own_client = False
        else:
            headers = {}
            if api_key:
                headers["X-API-Key"] = api_key
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"

            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=timeout,
            )
            self._own_client = True

    async def decide(self, request: DecideRequest) -> DecideResponse:
        """Submit decision request with retry."""
        async for attempt in AsyncRetrying(**self.retry_policy.to_tenacity_kwargs()):
            with attempt:
                try:
                    response = await self._http_client.post(
                        "/decide",
                        json=request.model_dump(by_alias=True, exclude_none=True),
                        headers={"X-Correlation-Id": request.correlation_id},
                    )
                    return self._handle_response(response, DecideResponse)

                except httpx.TimeoutException as e:
                    logger.warning(f"Decide request timeout: {e}")
                    raise NetworkError(f"Request timeout: {e}", details={"url": "/decide"}) from e

                except httpx.ConnectError as e:
                    logger.warning(f"Decide connection error: {e}")
                    raise NetworkError(
                        f"Connection error: {e}", details={"url": "/decide"}
                    ) from e

                except httpx.HTTPError as e:
                    logger.error(f"Decide HTTP error: {e}")
                    raise NetworkError(f"HTTP error: {e}", details={"url": "/decide"}) from e

        # Should never reach here due to reraise=True, but satisfy type checker
        raise RetryExhaustedError(
            original_error=Exception("Unknown error"),
            attempts=self.retry_policy.max_attempts,
        )

    async def execute(self, request: ExecuteRequest) -> ExecuteResponse:
        """Execute request with retry."""
        async for attempt in AsyncRetrying(**self.retry_policy.to_tenacity_kwargs()):
            with attempt:
                try:
                    response = await self._http_client.post(
                        "/execute",
                        json=request.model_dump(by_alias=True, exclude_none=True),
                        headers={"X-Correlation-Id": request.correlation_id},
                    )
                    return self._handle_response(response, ExecuteResponse)

                except httpx.TimeoutException as e:
                    logger.warning(f"Execute request timeout: {e}")
                    raise NetworkError(
                        f"Request timeout: {e}", details={"url": "/execute"}
                    ) from e

                except httpx.ConnectError as e:
                    logger.warning(f"Execute connection error: {e}")
                    raise NetworkError(
                        f"Connection error: {e}", details={"url": "/execute"}
                    ) from e

                except httpx.HTTPError as e:
                    logger.error(f"Execute HTTP error: {e}")
                    raise NetworkError(f"HTTP error: {e}", details={"url": "/execute"}) from e

        raise RetryExhaustedError(
            original_error=Exception("Unknown error"),
            attempts=self.retry_policy.max_attempts,
        )

    def _handle_response(self, response: httpx.Response, success_model: type) -> any:
        """
        Handle HTTP response and map to typed models or errors.

        Args:
            response: HTTP response
            success_model: Expected success model type

        Returns:
            Parsed success model

        Raises:
            KeonError subclasses for various error conditions
        """
        # Check for rate limit
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(retry_after=int(retry_after) if retry_after else None)

        # Check for server errors
        if 500 <= response.status_code < 600:
            raise ServerError(
                status_code=response.status_code,
                message=response.text,
                details={"url": str(response.url)},
            )

        # Try to parse response body
        try:
            data = response.json()
        except Exception as e:
            raise KeonError(
                f"Failed to parse response: {e}",
                code="INVALID_RESPONSE",
                details={"statusCode": response.status_code, "body": response.text[:200]},
            ) from e

        # Check for error response
        if not data.get("success", False):
            error_response = ErrorResponse.model_validate(data)
            error = error_response.error

            # Map error codes to specific exceptions
            if error.code == "MISSING_DECISION_RECEIPT":
                raise InvalidReceiptError(
                    receipt_id="<missing>",
                    reason=error.message,
                )
            elif error.code == "INVALID_DECISION_RECEIPT":
                receipt_id = error.details.get("receiptId", "unknown") if error.details else "unknown"
                raise InvalidReceiptError(
                    receipt_id=receipt_id,
                    reason=error.message,
                )
            elif error.code == "EXECUTION_DENIED":
                receipt_id = error.details.get("receiptId", "unknown") if error.details else "unknown"
                raise ExecutionDeniedError(
                    receipt_id=receipt_id,
                    reason=error.message,
                )
            elif error.code in ("INVALID_CORRELATION_ID", "VALIDATION_ERROR"):
                raise ValidationError(
                    message=error.message,
                    details=error.details,
                )
            else:
                # Generic error
                raise KeonError(
                    message=error.message,
                    code=error.code,
                    details=error.details,
                )

        # Parse success response
        try:
            return success_model.model_validate(data)
        except PydanticValidationError as e:
            raise ValidationError(
                f"Invalid response format: {e}",
                details={"errors": e.errors(), "data": data},
            ) from e

    async def close(self) -> None:
        """Close HTTP client if we own it."""
        if self._own_client:
            await self._http_client.aclose()
