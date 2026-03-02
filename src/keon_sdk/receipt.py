from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    is_valid: bool
    has_receipt_id: bool
    tenant_authorized: bool
    key_authorized: bool


@dataclass(frozen=True)
class TrustBundle:
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: str) -> "TrustBundle":
        return cls(payload=json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class DecisionReceipt:
    raw: dict[str, Any]

    def verify(self, bundle: TrustBundle) -> VerificationResult:
        receipt_id = self.raw.get("receipt_id") or self.raw.get("receiptId")
        tenant_id = self.raw.get("tenant_id") or self.raw.get("tenantId")
        signer_kid = self.raw.get("signer_kid") or self.raw.get("key_id") or self.raw.get("kid")
        has_receipt_id = isinstance(receipt_id, str) and bool(receipt_id)
        authorized_tenant = _find_tenant(bundle.payload, tenant_id)
        key_authorized = _tenant_has_key(authorized_tenant, signer_kid)
        return VerificationResult(
            is_valid=has_receipt_id and authorized_tenant is not None and key_authorized,
            has_receipt_id=has_receipt_id,
            tenant_authorized=authorized_tenant is not None,
            key_authorized=key_authorized,
        )


def _find_tenant(bundle: dict[str, Any], tenant_id: Any) -> dict[str, Any] | None:
    if not isinstance(tenant_id, str):
        return None
    tenants = bundle.get("tenants", [])
    if not isinstance(tenants, list):
        return None
    for tenant in tenants:
        if isinstance(tenant, dict) and tenant.get("tenant_id", tenant.get("tenantId")) == tenant_id:
            return tenant
    return None


def _tenant_has_key(tenant: dict[str, Any] | None, signer_kid: Any) -> bool:
    if tenant is None or not isinstance(signer_kid, str):
        return False
    keys = tenant.get("keys", [])
    if not isinstance(keys, list):
        return False
    for key in keys:
        if isinstance(key, dict) and key.get("kid") == signer_kid:
            return True
    return False

