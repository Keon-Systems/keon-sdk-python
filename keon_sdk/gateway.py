"""
Runtime Gateway abstraction.

Protocol for communication with Keon Runtime.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from .contracts import DecideRequest, DecideResponse, ExecuteRequest, ExecuteResponse


class RuntimeGateway(Protocol):
    """
    Protocol for Keon Runtime communication.

    Implementations handle the specifics of HTTP, auth, serialization, etc.
    """

    async def decide(self, request: DecideRequest) -> DecideResponse:
        """
        Submit a decision request to Keon Runtime.

        Args:
            request: Decision request with tenant, actor, action, resource

        Returns:
            DecideResponse with DecisionReceipt

        Raises:
            ValidationError: Request validation failed
            InvalidCorrelationIdError: CorrelationId format invalid
            NetworkError: Connection/timeout issues
            ServerError: 5xx server errors
            KeonError: Other errors
        """
        ...

    async def execute(self, request: ExecuteRequest) -> ExecuteResponse:
        """
        Execute an action with governance.

        Args:
            request: Execute request with DecisionReceiptId (REQUIRED)

        Returns:
            ExecuteResponse with ExecutionResult

        Raises:
            MissingReceiptError: DecisionReceiptId not provided
            InvalidReceiptError: Receipt invalid or expired
            ExecutionDeniedError: Policy denied execution
            NetworkError: Connection/timeout issues
            ServerError: 5xx server errors
            KeonError: Other errors
        """
        ...


class BaseRuntimeGateway(ABC):
    """
    Abstract base class for gateway implementations.

    Provides common validation and error handling.
    """

    @abstractmethod
    async def decide(self, request: DecideRequest) -> DecideResponse:
        """Submit decision request."""
        pass

    @abstractmethod
    async def execute(self, request: ExecuteRequest) -> ExecuteResponse:
        """Execute with governance."""
        pass

    async def close(self) -> None:
        """
        Close any resources (HTTP connections, etc.).

        Optional - override if needed.
        """
        pass

    async def __aenter__(self) -> "BaseRuntimeGateway":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Async context manager exit."""
        await self.close()
