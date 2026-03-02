from __future__ import annotations

from typing import Any

from ._cli import verify_pack_json
from .evidence_pack import EvidencePack
from .types import L3VerificationResult, VerificationError

_TRUST_BUNDLE_ERROR_PREFIX = "KEON_VERIFY_TRUST_BUNDLE_"
_AUTHORIZATION_ERRORS = {
    "KEON_VERIFY_TENANT_NOT_IN_BUNDLE",
    "KEON_VERIFY_SIGNER_NOT_AUTHORIZED",
    "KEON_VERIFY_SIGNER_KEY_REVOKED",
    "KEON_VERIFY_SIGNER_KEY_DISABLED",
    "KEON_VERIFY_SIGNER_KEY_EXPIRED",
    "KEON_VERIFY_TENANT_AMBIGUOUS",
}
_RECEIPT_CHAIN_ERRORS = {
    "KEON_VERIFY_RECEIPT_CHAIN_INVALID",
    "KEON_VERIFY_PACK_INVALID",
}
_VERSION_ERRORS = {
    "KEON_VERIFY_VERSION_INVALID",
    "KEON_VERIFY_VERSION_MISSING",
}


def verify_caes(pack_path: str, bundle_path: str | None = None) -> L3VerificationResult:
    evidence_pack = EvidencePack.load(pack_path)
    cli_result = verify_pack_json(pack_path, bundle_path=bundle_path)
    report = cli_result.payload
    errors = tuple(
        VerificationError(code=str(item["code"]))
        for item in report.get("errors", [])
        if isinstance(item, dict) and "code" in item
    )
    error_codes = {item.code for item in errors}
    artifact_types = {artifact.type.lower() for artifact in evidence_pack.artifacts}
    artifact_names = {artifact.name.lower() for artifact in evidence_pack.artifacts}
    # TODO(WS-D): Replace string matching with schema-backed artifact classification once pack extension
    # artifacts are frozen and emitted with stable identifiers.
    has_delegation_artifact = any(
        "delegation" in artifact.name.lower() or "delegation" in artifact.type.lower()
        for artifact in evidence_pack.artifacts
    )
    has_chaos_attestation = any("chaos" in artifact.name.lower() for artifact in evidence_pack.artifacts)
    has_policy_hash_manifest = evidence_pack.policy_hash_manifest is not None
    has_only_structured_errors = all(code.startswith("KEON_") for code in error_codes)
    offline_verification_used = cli_result.offline_mode_used and bool(bundle_path) and bool(
        report.get("trust_bundle_provided", False)
    )
    # TODO(WS-F): L3-04 and L3-15 need distinct signals from chaos attestation contents. Until WS-F
    # ships those fields, keep these as conservative provisional checks instead of claiming a full proof.
    l3_chaos_attestation_present = has_chaos_attestation
    l3_retention_chaos_attested = has_chaos_attestation and "retention" in " ".join(artifact_names)

    return L3VerificationResult(
        schema_id=_as_str(report.get("schema_id")),
        verdict=_as_str(report.get("verdict")),
        is_valid=bool(report.get("is_valid", False)),
        phase=_as_int(report.get("phase")),
        pack_hash=_as_str(report.get("pack_hash")),
        tenant_id=_as_str(report.get("tenant_id")),
        signer_kids=tuple(_as_str_list(report.get("signer_kids"))),
        pack_integrity=_as_bool(report.get("pack_integrity")),
        signature_valid=_as_bool(report.get("signature_valid")),
        authorization_valid=_as_bool(report.get("authorization_valid")),
        trust_bundle_provided=bool(report.get("trust_bundle_provided", bundle_path is not None)),
        outcome=_as_str(report.get("outcome")),
        errors=errors,
        l3_01=has_policy_hash_manifest and "KEON_POLICY_HASH_MISMATCH" not in error_codes,
        l3_02="receipt" in artifact_types and not error_codes.intersection(_RECEIPT_CHAIN_ERRORS),
        l3_03=bool(report.get("signature_valid", False)),
        l3_04=l3_chaos_attestation_present,
        l3_05=bool(report.get("pack_integrity", False)),
        l3_06=offline_verification_used,
        l3_07=has_delegation_artifact and "KEON_DELEGATION_BINDING_MISSING" not in error_codes,
        l3_08=has_policy_hash_manifest and has_delegation_artifact and has_chaos_attestation,
        l3_09=not error_codes.intersection(_VERSION_ERRORS),
        l3_10="KEON_PROVENANCE_BROKEN" not in error_codes,
        l3_11=bundle_path is not None and not any(code.startswith(_TRUST_BUNDLE_ERROR_PREFIX) for code in error_codes),
        l3_12=has_policy_hash_manifest,
        l3_13=has_delegation_artifact,
        l3_14=has_chaos_attestation,
        l3_15=l3_retention_chaos_attested,
        l3_16=has_only_structured_errors,
        l3_17=has_delegation_artifact and "KEON_DELEGATION_BINDING_MISSING" not in error_codes,
        raw_report=report,
    )


def _as_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _as_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
