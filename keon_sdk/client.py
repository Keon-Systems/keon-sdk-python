"""
Keon SDK Client

Main entry point for interacting with Keon Runtime.
"""

import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from .contracts import (
    DecideRequest,
    DecideResponse,
    DecisionReceipt,
    ExecuteRequest,
    ExecuteResponse,
    ExecutionResult,
)
from .errors import ExecutionDeniedError
from .gateway import RuntimeGateway
from .http_gateway import HttpRuntimeGateway
from .retry import RetryPolicy

logger = logging.getLogger(__name__)


def generate_uuidv7() -> str:
    """
    Generate a UUIDv7 string.

    Note: Python's uuid module doesn't have native UUIDv7 support yet.
    This is a placeholder that generates UUIDv4.
    In production, use a proper UUIDv7 library.
    """
    # TODO: Replace with proper UUIDv7 generation
    # For now, using UUIDv4 with version byte manually set to 7
    base = str(uuid4())
    # Hack: change version nibble to 7
    return base[:14] + "7" + base[15:]


class KeonClient:
    """
    Keon Python SDK Client

    Safe-by-default client for Keon Runtime with:
    - Strict validation (CorrelationId, receipt requirements)
    - Automatic retries for transient failures
    - Structured error handling
    - Optional batching support

    Example:
        ```python
        from keon_sdk import KeonClient

        client = KeonClient(
            base_url="https://api.keon.systems/runtime/v1",
            api_key="your-api-key",
        )

        # Decide
        receipt = await client.decide(
            tenant_id="tenant-123",
            actor_id="user-456",
            action="execute_workflow",
            resource_type="workflow",
            resource_id="workflow-789",
        )

        # Execute (requires receipt)
        if receipt.decision == "allow":
            result = await client.execute(
                receipt=receipt,
                action="execute_workflow",
                parameters={"workflowId": "workflow-789"},
            )
        ```
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080/runtime/v1",
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        retry_policy: Optional[RetryPolicy] = None,
        timeout: float = 30.0,
        gateway: Optional[RuntimeGateway] = None,
    ) -> None:
        """
        Initialize Keon client.

        Args:
            base_url: Keon Runtime API base URL
            api_key: Optional API key for authentication
            bearer_token: Optional bearer token for authentication
            retry_policy: Retry policy (default: RetryPolicy.default())
            timeout: Request timeout in seconds (default: 30.0)
            gateway: Optional custom gateway implementation
        """
        self.base_url = base_url
        self.retry_policy = retry_policy or RetryPolicy.default()

        # Use provided gateway or create HTTP gateway
        if gateway:
            self.gateway = gateway
        else:
            self.gateway = HttpRuntimeGateway(
                base_url=base_url,
                api_key=api_key,
                bearer_token=bearer_token,
                retry_policy=self.retry_policy,
                timeout=timeout,
            )

    async def decide(
        self,
        tenant_id: str,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> DecisionReceipt:
        """
        Request a policy decision.

        Args:
            tenant_id: Tenant identifier
            actor_id: Actor identifier (user, service, agent)
            action: Action being requested
            resource_type: Type of resource
            resource_id: Resource identifier
            context: Optional additional context
            correlation_id: Optional correlation ID (auto-generated if not provided)

        Returns:
            DecisionReceipt with decision (allow/deny) and receiptId

        Raises:
            InvalidCorrelationIdError: CorrelationId format invalid
            ValidationError: Request validation failed
            NetworkError: Connection/timeout issues
            ServerError: 5xx server errors
            KeonError: Other errors

        Example:
            ```python
            receipt = await client.decide(
                tenant_id="tenant-123",
                actor_id="user-456",
                action="execute_workflow",
                resource_type="workflow",
                resource_id="workflow-789",
                context={"environment": "production"},
            )

            if receipt.decision == "allow":
                # Proceed to execute
                pass
            else:
                # Handle denial
                print(f"Denied: {receipt.reason}")
            ```
        """
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = f"t:{tenant_id}|c:{generate_uuidv7()}"

        request = DecideRequest(
            correlationId=correlation_id,
            tenantId=tenant_id,
            actorId=actor_id,
            action=action,
            resourceType=resource_type,
            resourceId=resource_id,
            context=context,
        )

        logger.info(
            f"Decide request: action={action}, resource={resource_type}/{resource_id}, correlation_id={correlation_id}"
        )

        response = await self.gateway.decide(request)

        logger.info(
            f"Decide response: decision={response.data.decision}, receipt_id={response.data.receipt_id}"
        )

        return response.data

    async def execute(
        self,
        receipt: DecisionReceipt,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute an action under governance.

        REQUIRES a DecisionReceipt from a prior decide() call.
        Hard fails if receipt is missing or invalid.

        Args:
            receipt: DecisionReceipt from decide()
            action: Action to execute
            parameters: Optional action parameters

        Returns:
            ExecutionResult with execution details

        Raises:
            MissingReceiptError: Receipt not provided
            InvalidReceiptError: Receipt invalid or expired
            ExecutionDeniedError: Policy denied execution
            NetworkError: Connection/timeout issues
            ServerError: 5xx server errors
            KeonError: Other errors

        Example:
            ```python
            receipt = await client.decide(...)

            if receipt.decision == "allow":
                result = await client.execute(
                    receipt=receipt,
                    action="execute_workflow",
                    parameters={
                        "workflowId": "workflow-789",
                        "inputs": {"param1": "value1"},
                    },
                )
                print(f"Execution ID: {result.execution_id}")
            ```
        """
        # Enforce receipt requirement
        if not receipt:
            from .errors import MissingReceiptError

            raise MissingReceiptError()

        # Check if decision was deny
        if receipt.decision == "deny":
            raise ExecutionDeniedError(
                receipt_id=receipt.receipt_id,
                reason=receipt.reason,
            )

        request = ExecuteRequest(
            correlationId=receipt.correlation_id,
            decisionReceiptId=receipt.receipt_id,
            tenantId=receipt.tenant_id,
            actorId=receipt.actor_id,
            action=action,
            parameters=parameters,
        )

        logger.info(
            f"Execute request: action={action}, receipt_id={receipt.receipt_id}, correlation_id={receipt.correlation_id}"
        )

        response = await self.gateway.execute(request)

        logger.info(
            f"Execute response: execution_id={response.data.execution_id}, status={response.data.status}"
        )

        return response.data

    async def decide_and_execute(
        self,
        tenant_id: str,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Convenience method: decide + execute in one call.

        Automatically handles the decide -> execute flow.
        Raises ExecutionDeniedError if policy denies.

        Args:
            tenant_id: Tenant identifier
            actor_id: Actor identifier
            action: Action to execute
            resource_type: Resource type
            resource_id: Resource identifier
            parameters: Execution parameters
            context: Decision context

        Returns:
            ExecutionResult

        Raises:
            ExecutionDeniedError: Policy denied execution
            Other exceptions from decide() or execute()

        Example:
            ```python
            result = await client.decide_and_execute(
                tenant_id="tenant-123",
                actor_id="user-456",
                action="execute_workflow",
                resource_type="workflow",
                resource_id="workflow-789",
                parameters={"inputs": {"param1": "value1"}},
            )
            ```
        """
        # Decide
        receipt = await self.decide(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            context=context,
        )

        # Execute (will raise ExecutionDeniedError if denied)
        return await self.execute(
            receipt=receipt,
            action=action,
            parameters=parameters,
        )

    async def close(self) -> None:
        """Close gateway resources."""
        if hasattr(self.gateway, "close"):
            await self.gateway.close()

    async def __aenter__(self) -> "KeonClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Async context manager exit."""
        await self.close()
