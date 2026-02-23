"""Keon SDK Architecture Sentinels.

Policy authority guards for keon-sdk-python:

  KEON-SDK-SENTINEL-1a: DecideRequest schema strict — all required fields enforced,
                         invalid correlationId rejected at construction time
  KEON-SDK-SENTINEL-1b: DecisionReceipt schema strict — receipt format + decision field
  KEON-SDK-SENTINEL-1c: Timeout → NetworkError; gateway never silently allows on failure

A failure here means the Keon policy contract has been weakened and CI must block the merge.
"""

import hashlib
import json

import pytest

_VALID_CORRELATION_ID = "t:test-tenant|c:01932b3c-4d5e-7890-abcd-ef1234567890"
_VALID_RECEIPT_ID = "dr-01932b3c-4d5e-7890-abcd-ef1234567890"


@pytest.mark.sentinel
class TestKeonSdkSentinels:
    """Architecture guard tests for keon-sdk-python.

    Schema-level and unit-level checks that enforce the policy authority contract.
    These tests have zero external dependencies — they run in any environment.
    """

    # ───────────────────────────────────────────────────────────────────────────
    # KEON-SDK-SENTINEL-1a: DecideRequest schema is strict
    # ───────────────────────────────────────────────────────────────────────────

    def test_keon_sdk_sentinel_1a_decide_request_requires_correlation_id(self) -> None:
        """KEON-SDK-SENTINEL-1a: DecideRequest without correlationId must fail at construction."""
        from pydantic import ValidationError
        from keon_sdk.contracts import DecideRequest

        with pytest.raises(ValidationError):
            DecideRequest(
                tenantId="t", actorId="a",
                action="x", resourceType="r", resourceId="id",
            )

    def test_keon_sdk_sentinel_1a_decide_request_rejects_invalid_correlation_id(self) -> None:
        """KEON-SDK-SENTINEL-1a: Malformed correlationId must be rejected at construction."""
        from pydantic import ValidationError
        from keon_sdk.contracts import DecideRequest

        with pytest.raises(ValidationError):
            DecideRequest(
                correlationId="not-valid",
                tenantId="t", actorId="a",
                action="x", resourceType="r", resourceId="id",
            )

    def test_keon_sdk_sentinel_1a_decide_request_requires_tenant_and_actor(self) -> None:
        """KEON-SDK-SENTINEL-1a: tenantId and actorId are mandatory — both absent cases fail."""
        from pydantic import ValidationError
        from keon_sdk.contracts import DecideRequest

        with pytest.raises(ValidationError):  # missing tenantId
            DecideRequest(
                correlationId=_VALID_CORRELATION_ID,
                actorId="a", action="x", resourceType="r", resourceId="id",
            )

        with pytest.raises(ValidationError):  # missing actorId
            DecideRequest(
                correlationId=_VALID_CORRELATION_ID,
                tenantId="t", action="x", resourceType="r", resourceId="id",
            )

    # ───────────────────────────────────────────────────────────────────────────
    # KEON-SDK-SENTINEL-1b: DecisionReceipt schema is strict
    # ───────────────────────────────────────────────────────────────────────────

    def test_keon_sdk_sentinel_1b_decision_receipt_requires_receipt_id(self) -> None:
        """KEON-SDK-SENTINEL-1b: DecisionReceipt without receiptId must fail."""
        from datetime import datetime, timezone
        from pydantic import ValidationError
        from keon_sdk.contracts import DecisionEnum, DecisionReceipt

        with pytest.raises(ValidationError):
            DecisionReceipt(
                decision=DecisionEnum.ALLOW,
                correlationId=_VALID_CORRELATION_ID,
                tenantId="t", actorId="a",
                decidedAt=datetime.now(timezone.utc),
            )

    def test_keon_sdk_sentinel_1b_decision_receipt_rejects_invalid_receipt_id(self) -> None:
        """KEON-SDK-SENTINEL-1b: receiptId not matching ^dr-<uuidv7> must fail."""
        from datetime import datetime, timezone
        from pydantic import ValidationError
        from keon_sdk.contracts import DecisionEnum, DecisionReceipt

        with pytest.raises(ValidationError):
            DecisionReceipt(
                receiptId="not-a-valid-receipt",
                decision=DecisionEnum.ALLOW,
                correlationId=_VALID_CORRELATION_ID,
                tenantId="t", actorId="a",
                decidedAt=datetime.now(timezone.utc),
            )

    def test_keon_sdk_sentinel_1b_decision_receipt_requires_decision(self) -> None:
        """KEON-SDK-SENTINEL-1b: DecisionReceipt without decision field must fail."""
        from datetime import datetime, timezone
        from pydantic import ValidationError
        from keon_sdk.contracts import DecisionReceipt

        with pytest.raises(ValidationError):
            DecisionReceipt(
                receiptId=_VALID_RECEIPT_ID,
                correlationId=_VALID_CORRELATION_ID,
                tenantId="t", actorId="a",
                decidedAt=datetime.now(timezone.utc),
            )

    # ───────────────────────────────────────────────────────────────────────────
    # KEON-SDK-SENTINEL-1c: Timeout → NetworkError (fail-closed)
    # ───────────────────────────────────────────────────────────────────────────

    async def test_keon_sdk_sentinel_1c_timeout_is_fail_closed(self) -> None:
        """KEON-SDK-SENTINEL-1c: Gateway timeout raises NetworkError — never silently allows.

        Uses RetryPolicy.no_retry() to ensure a single attempt is made and the
        NetworkError propagates without masking or silent fallback.
        """
        from unittest.mock import AsyncMock
        import httpx
        from keon_sdk.contracts import DecideRequest
        from keon_sdk.errors import NetworkError
        from keon_sdk.http_gateway import HttpRuntimeGateway
        from keon_sdk.retry import RetryPolicy

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = httpx.TimeoutException("Read timeout")

        gateway = HttpRuntimeGateway(
            base_url="http://keon.example.com/runtime/v1",
            http_client=mock_client,
            retry_policy=RetryPolicy.no_retry(),
        )
        request = DecideRequest(
            correlationId=_VALID_CORRELATION_ID,
            tenantId="test-tenant", actorId="user-456",
            action="read_campaign", resourceType="campaign",
            resourceId="campaign-123",
        )

        with pytest.raises(NetworkError) as exc_info:
            await gateway.decide(request)

        assert exc_info.value.code == "NETWORK_ERROR", (
            f"KEON-SDK-SENTINEL-1c FAILED: timeout did not produce NetworkError, "
            f"got code={exc_info.value.code!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Drift tripwire hashes — update only after doctrine review
# ─────────────────────────────────────────────────────────────────────────────
_DECIDE_FIELDS_HASH = "6a8c75b57593cd19"
_RECEIPT_FIELDS_HASH = "d5f0c62ffa683fde"


def _compute_hash(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


def _required_model_fields(model_cls: type) -> list[str]:
    """Return sorted names of required fields (no default) from a Pydantic v2 model."""
    return sorted(name for name, info in model_cls.model_fields.items() if info.is_required())


@pytest.mark.sentinel
class TestKeonSdkDriftTripwire:
    """Drift tripwires: detect unapproved changes to Keon contract schemas.

    If the required-field set of DecideRequest or DecisionReceipt changes without
    updating the stored hash, this class trips and blocks merge.  To approve:
      1. Make the intentional schema change.
      2. Re-derive the hash (see SENTINELS.md for command).
      3. Update _DECIDE_FIELDS_HASH / _RECEIPT_FIELDS_HASH above.
      4. Commit: sentinel(drift): approve <what changed> — <reason>
    """

    def test_decide_request_schema_hash_unchanged(self) -> None:
        """DRIFT: DecideRequest required-field set must match stored hash."""
        from keon_sdk.contracts import DecideRequest

        actual = _compute_hash(_required_model_fields(DecideRequest))
        assert actual == _DECIDE_FIELDS_HASH, (
            f"DRIFT TRIPWIRE TRIPPED — DecideRequest required fields changed without approval. "
            f"New hash={actual!r}. Fields now: {_required_model_fields(DecideRequest)}. "
            f"Update _DECIDE_FIELDS_HASH after doctrine review."
        )

    def test_decision_receipt_schema_hash_unchanged(self) -> None:
        """DRIFT: DecisionReceipt required-field set must match stored hash."""
        from keon_sdk.contracts import DecisionReceipt

        actual = _compute_hash(_required_model_fields(DecisionReceipt))
        assert actual == _RECEIPT_FIELDS_HASH, (
            f"DRIFT TRIPWIRE TRIPPED — DecisionReceipt required fields changed without approval. "
            f"New hash={actual!r}. Fields now: {_required_model_fields(DecisionReceipt)}. "
            f"Update _RECEIPT_FIELDS_HASH after doctrine review."
        )

