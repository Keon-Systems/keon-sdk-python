"""
Keon Runtime API Contracts

In production, these would be auto-generated from keon-contracts OpenAPI spec.
For now, hand-crafted Pydantic v2 models that match the contract.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# CorrelationId validation
CORRELATION_ID_PATTERN = re.compile(
    r"^t:[a-zA-Z0-9\-_]+\|c:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

RECEIPT_ID_PATTERN = re.compile(
    r"^dr-[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class DecisionEnum(str, Enum):
    """Policy decision outcome."""

    ALLOW = "allow"
    DENY = "deny"


class ExecutionStatus(str, Enum):
    """Execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DecideRequest(BaseModel):
    """Request a policy decision."""

    correlation_id: str = Field(
        ...,
        alias="correlationId",
        description="Canonical form: t:<TenantId>|c:<uuidv7>",
    )
    tenant_id: str = Field(..., alias="tenantId", min_length=1)
    actor_id: str = Field(..., alias="actorId", min_length=1)
    action: str = Field(..., min_length=1)
    resource_type: str = Field(..., alias="resourceType", min_length=1)
    resource_id: str = Field(..., alias="resourceId", min_length=1)
    subject_hash: str = Field(
        ...,
        alias="subjectHash",
        min_length=1,
        description="SHA-256 hex digest of the canonical subject payload (content being governed)",
    )
    context: Optional[Dict[str, Any]] = None

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, v: str) -> str:
        if not CORRELATION_ID_PATTERN.match(v):
            raise ValueError(
                f"CorrelationId must match canonical form: t:<TenantId>|c:<uuidv7>, got: {v}"
            )
        return v

    model_config = {
        "populate_by_name": True,
    }


class DecisionReceipt(BaseModel):
    """Decision receipt returned from /decide."""

    receipt_id: str = Field(..., alias="receiptId", pattern=r"^dr-")
    decision: DecisionEnum
    correlation_id: str = Field(..., alias="correlationId")
    tenant_id: str = Field(..., alias="tenantId")
    actor_id: str = Field(..., alias="actorId")
    decided_at: datetime = Field(..., alias="decidedAt")
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")
    reason: Optional[str] = None
    applied_policies: Optional[list[str]] = Field(None, alias="appliedPolicies")

    @field_validator("receipt_id")
    @classmethod
    def validate_receipt_id(cls, v: str) -> str:
        if not RECEIPT_ID_PATTERN.match(v):
            raise ValueError(f"Invalid DecisionReceiptId format: {v}")
        return v

    model_config = {
        "populate_by_name": True,
    }


class DecideResponse(BaseModel):
    """Response from /decide."""

    success: Literal[True]
    data: DecisionReceipt

    model_config = {
        "populate_by_name": True,
    }


class ExecuteRequest(BaseModel):
    """Execute an action under governance."""

    correlation_id: str = Field(
        ...,
        alias="correlationId",
        description="Canonical form: t:<TenantId>|c:<uuidv7>",
    )
    decision_receipt_id: str = Field(
        ...,
        alias="decisionReceiptId",
        description="Receipt from /decide (REQUIRED)",
    )
    tenant_id: str = Field(..., alias="tenantId", min_length=1)
    actor_id: str = Field(..., alias="actorId", min_length=1)
    action: str = Field(..., min_length=1)
    parameters: Optional[Dict[str, Any]] = None

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, v: str) -> str:
        if not CORRELATION_ID_PATTERN.match(v):
            raise ValueError(
                f"CorrelationId must match canonical form: t:<TenantId>|c:<uuidv7>, got: {v}"
            )
        return v

    @field_validator("decision_receipt_id")
    @classmethod
    def validate_receipt_id(cls, v: str) -> str:
        if not v:
            raise ValueError("Execute requires DecisionReceiptId (hard fail if absent)")
        if not RECEIPT_ID_PATTERN.match(v):
            raise ValueError(f"Invalid DecisionReceiptId format: {v}")
        return v

    model_config = {
        "populate_by_name": True,
    }


class ExecutionResult(BaseModel):
    """Result from /execute."""

    execution_id: str = Field(..., alias="executionId", pattern=r"^exec-")
    correlation_id: str = Field(..., alias="correlationId")
    decision_receipt_id: str = Field(..., alias="decisionReceiptId")
    status: ExecutionStatus
    result: Optional[Dict[str, Any]] = None
    executed_at: datetime = Field(..., alias="executedAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")

    model_config = {
        "populate_by_name": True,
    }


class ExecuteResponse(BaseModel):
    """Response from /execute."""

    success: Literal[True]
    data: ExecutionResult

    model_config = {
        "populate_by_name": True,
    }


class ErrorDetail(BaseModel):
    """Structured error detail."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    model_config = {
        "populate_by_name": True,
    }


class ErrorResponse(BaseModel):
    """Error response envelope."""

    success: Literal[False]
    error: ErrorDetail

    model_config = {
        "populate_by_name": True,
    }
