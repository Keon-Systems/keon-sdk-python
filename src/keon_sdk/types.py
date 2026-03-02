from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class VerificationError:
    code: str


@dataclass(frozen=True)
class L3VerificationResult:
    schema_id: str | None
    verdict: str | None
    is_valid: bool
    phase: int | None
    pack_hash: str | None
    tenant_id: str | None
    signer_kids: tuple[str, ...]
    pack_integrity: bool | None
    signature_valid: bool | None
    authorization_valid: bool | None
    trust_bundle_provided: bool
    outcome: str | None
    errors: tuple[VerificationError, ...]
    l3_01: bool
    l3_02: bool
    l3_03: bool
    l3_04: bool
    l3_05: bool
    l3_06: bool
    l3_07: bool
    l3_08: bool
    l3_09: bool
    l3_10: bool
    l3_11: bool
    l3_12: bool
    l3_13: bool
    l3_14: bool
    l3_15: bool
    l3_16: bool
    l3_17: bool
    raw_report: Mapping[str, Any]

