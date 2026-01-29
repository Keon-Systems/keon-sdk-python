"""
Test CorrelationId validation.

Ensures canonical form is enforced: t:<TenantId>|c:<uuidv7>
"""

import pytest
from pydantic import ValidationError

from keon_sdk.contracts import DecideRequest, ExecuteRequest


class TestCorrelationIdValidation:
    """CorrelationId must match canonical form."""

    def test_valid_correlation_id_decide(self) -> None:
        """Valid CorrelationId is accepted in DecideRequest."""
        request = DecideRequest(
            correlationId="t:tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890",
            tenantId="tenant-123",
            actorId="user-456",
            action="execute_workflow",
            resourceType="workflow",
            resourceId="workflow-789",
        )
        assert request.correlation_id == "t:tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890"

    def test_valid_correlation_id_execute(self) -> None:
        """Valid CorrelationId is accepted in ExecuteRequest."""
        request = ExecuteRequest(
            correlationId="t:tenant-abc|c:01932b3c-4d5e-7111-abcd-ef1234567890",
            decisionReceiptId="dr-01932b3c-4d5e-7890-abcd-ef1234567890",
            tenantId="tenant-abc",
            actorId="user-123",
            action="test_action",
        )
        assert request.correlation_id == "t:tenant-abc|c:01932b3c-4d5e-7111-abcd-ef1234567890"

    def test_invalid_correlation_id_missing_prefix(self) -> None:
        """CorrelationId without 't:' prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DecideRequest(
                correlationId="tenant-123|c:01932b3c-4d5e-7890-abcd-ef1234567890",
                tenantId="tenant-123",
                actorId="user-456",
                action="execute_workflow",
                resourceType="workflow",
                resourceId="workflow-789",
            )
        assert "canonical form" in str(exc_info.value).lower()

    def test_invalid_correlation_id_wrong_separator(self) -> None:
        """CorrelationId with wrong separator is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DecideRequest(
                correlationId="t:tenant-123:c:01932b3c-4d5e-7890-abcd-ef1234567890",
                tenantId="tenant-123",
                actorId="user-456",
                action="execute_workflow",
                resourceType="workflow",
                resourceId="workflow-789",
            )
        assert "canonical form" in str(exc_info.value).lower()

    def test_invalid_correlation_id_not_uuidv7(self) -> None:
        """CorrelationId with non-UUIDv7 format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DecideRequest(
                correlationId="t:tenant-123|c:not-a-uuid",
                tenantId="tenant-123",
                actorId="user-456",
                action="execute_workflow",
                resourceType="workflow",
                resourceId="workflow-789",
            )
        assert "canonical form" in str(exc_info.value).lower()

    def test_invalid_correlation_id_uuidv4_not_v7(self) -> None:
        """CorrelationId with UUIDv4 (not v7) is rejected."""
        # UUIDv4 has version nibble '4', not '7'
        with pytest.raises(ValidationError) as exc_info:
            DecideRequest(
                correlationId="t:tenant-123|c:01932b3c-4d5e-4890-abcd-ef1234567890",
                tenantId="tenant-123",
                actorId="user-456",
                action="execute_workflow",
                resourceType="workflow",
                resourceId="workflow-789",
            )
        assert "canonical form" in str(exc_info.value).lower()

    def test_correlation_id_with_underscores_and_hyphens(self) -> None:
        """TenantId can contain alphanumeric, hyphens, underscores."""
        request = DecideRequest(
            correlationId="t:tenant_123-abc|c:01932b3c-4d5e-7890-abcd-ef1234567890",
            tenantId="tenant_123-abc",
            actorId="user-456",
            action="execute_workflow",
            resourceType="workflow",
            resourceId="workflow-789",
        )
        assert request.correlation_id == "t:tenant_123-abc|c:01932b3c-4d5e-7890-abcd-ef1234567890"
