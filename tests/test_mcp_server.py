from dataclasses import asdict

import keon_sdk.mcp_server as mcp_server
from keon_sdk import L3VerificationResult, VerificationError


def test_check_l3_compliance_tool_returns_dataclass_payload(monkeypatch) -> None:
    result = L3VerificationResult(
        schema_id="keon.verify_pack.report.v1",
        verdict="PASS",
        is_valid=True,
        phase=5,
        pack_hash="sha256:test",
        tenant_id="tenant-1",
        signer_kids=("kid-1",),
        pack_integrity=True,
        signature_valid=True,
        authorization_valid=True,
        trust_bundle_provided=True,
        outcome="valid",
        errors=(VerificationError(code="KEON_NONE"),),
        l3_01=True,
        l3_02=True,
        l3_03=True,
        l3_04=True,
        l3_05=True,
        l3_06=True,
        l3_07=True,
        l3_08=True,
        l3_09=True,
        l3_10=True,
        l3_11=True,
        l3_12=True,
        l3_13=True,
        l3_14=True,
        l3_15=True,
        l3_16=True,
        l3_17=True,
        raw_report={"is_valid": True},
    )
    monkeypatch.setattr(mcp_server, "verify_caes", lambda pack_path, bundle_path=None: result)

    payload = mcp_server._call_tool(
        "check_l3_compliance",
        {"pack_path": "pack.zip", "bundle_path": "bundle.json"},
    )

    assert payload == asdict(result)

