"""
Test execute receipt requirement.

Execute MUST have DecisionReceiptId - hard fail if absent.
"""

import pytest
from pydantic import ValidationError

from keon_sdk import DecisionReceipt, KeonClient, MissingReceiptError
from keon_sdk.contracts import DecisionEnum, ExecuteRequest


class TestExecuteRequiresReceipt:
    """Execute requires DecisionReceiptId (hard fail if absent)."""

    def test_execute_request_missing_receipt_id(self) -> None:
        """ExecuteRequest without DecisionReceiptId fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ExecuteRequest(
                correlationId="t:tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890",
                # decisionReceiptId missing!
                tenantId="tenant-123",
                actorId="user-456",
                action="test_action",
            )
        # Should fail on required field
        assert "decisionReceiptId" in str(exc_info.value).lower() or "required" in str(
            exc_info.value
        ).lower()

    def test_execute_request_empty_receipt_id(self) -> None:
        """ExecuteRequest with empty DecisionReceiptId fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ExecuteRequest(
                correlationId="t:tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890",
                decisionReceiptId="",  # Empty!
                tenantId="tenant-123",
                actorId="user-456",
                action="test_action",
            )
        assert "receipt" in str(exc_info.value).lower()

    def test_execute_request_invalid_receipt_format(self) -> None:
        """ExecuteRequest with invalid receipt format fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ExecuteRequest(
                correlationId="t:tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890",
                decisionReceiptId="not-a-valid-receipt",
                tenantId="tenant-123",
                actorId="user-456",
                action="test_action",
            )
        assert "receipt" in str(exc_info.value).lower()

    def test_execute_request_valid_receipt_id(self) -> None:
        """ExecuteRequest with valid DecisionReceiptId passes."""
        request = ExecuteRequest(
            correlationId="t:tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890",
            decisionReceiptId="dr-01932b3c-4d5e-7890-abcd-ef1234567890",
            tenantId="tenant-123",
            actorId="user-456",
            action="test_action",
        )
        assert request.decision_receipt_id == "dr-01932b3c-4d5e-7890-abcd-ef1234567890"

    @pytest.mark.asyncio
    async def test_client_execute_without_receipt_fails(self) -> None:
        """KeonClient.execute() without receipt raises MissingReceiptError."""
        client = KeonClient(base_url="http://localhost:8080/runtime/v1")

        with pytest.raises(MissingReceiptError):
            await client.execute(
                receipt=None,  # type: ignore
                action="test_action",
            )

    @pytest.mark.asyncio
    async def test_client_execute_with_denied_receipt_fails(self) -> None:
        """KeonClient.execute() with denied receipt raises ExecutionDeniedError."""
        from datetime import datetime, timezone

        from keon_sdk import ExecutionDeniedError

        client = KeonClient(base_url="http://localhost:8080/runtime/v1")

        denied_receipt = DecisionReceipt(
            receiptId="dr-01932b3c-4d5e-7890-abcd-ef1234567891",
            decision=DecisionEnum.DENY,
            correlationId="t:tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890",
            tenantId="tenant-123",
            actorId="user-456",
            decidedAt=datetime.now(timezone.utc),
            reason="Policy denies this action",
        )

        with pytest.raises(ExecutionDeniedError) as exc_info:
            await client.execute(
                receipt=denied_receipt,
                action="test_action",
            )

        assert "denied" in str(exc_info.value).lower()
        assert denied_receipt.receipt_id in str(exc_info.value)
