from keon_sdk import verify_caes
from keon_sdk import _cli as cli_module
from keon_sdk import verify as verify_module


def test_verify_caes_maps_cli_report_to_l3_result(monkeypatch, tmp_path) -> None:
    pack_path = tmp_path / "pack.zip"
    pack_path.write_bytes(
        b"PK\x05\x06" + b"\x00" * 18
    )

    class StubEvidencePack:
        artifacts = []
        policy_hash_manifest = None

    monkeypatch.setattr(verify_module, "EvidencePack", type("StubLoader", (), {"load": staticmethod(lambda _: StubEvidencePack())}))
    monkeypatch.setattr(
        verify_module,
        "verify_pack_json",
        lambda pack_path, bundle_path=None: type(
            "Result",
            (),
            {
                "payload": {
                    "schema_id": "keon.verify_pack.report.v1",
                    "verdict": "FAIL",
                    "is_valid": False,
                    "phase": 5,
                    "pack_hash": "sha256:test",
                    "tenant_id": "tenant-1",
                    "signer_kids": ["kid-1"],
                    "pack_integrity": True,
                    "signature_valid": True,
                    "authorization_valid": False,
                    "trust_bundle_provided": True,
                    "outcome": "invalid",
                    "errors": [{"code": "KEON_VERIFY_TENANT_NOT_IN_BUNDLE"}],
                },
                "offline_mode_used": True,
            },
        )(),
    )

    result = verify_caes(str(pack_path), bundle_path="bundle.json")

    assert result.phase == 5
    assert result.authorization_valid is False
    assert result.l3_06 is True
    assert result.l3_11 is True
    assert result.errors[0].code == "KEON_VERIFY_TENANT_NOT_IN_BUNDLE"


def test_verify_pack_json_uses_bundle_key_as_pubkey(monkeypatch, tmp_path) -> None:
    pack_path = tmp_path / "pack.zip"
    bundle_path = tmp_path / "bundle.json"
    pack_path.write_bytes(b"unused")
    bundle_path.write_text("{}", encoding="utf-8")
    captured: list[str] = []

    class StubPack:
        artifacts = [
            type("Artifact", (), {"type": "attestation", "payload": {"key_id": "kid-1"}})(),
            type("Artifact", (), {"type": "receipt", "payload": {"tenant_id": "tenant-1"}})(),
        ]

    monkeypatch.setattr(cli_module, "EvidencePack", type("Loader", (), {"load": staticmethod(lambda _: StubPack())}))
    monkeypatch.setattr(
        cli_module.Path,
        "read_text",
        lambda self, encoding="utf-8": '{"tenants":[{"tenant_id":"tenant-1","keys":[{"kid":"kid-1","public_key_b64":"QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE="}]}]}',
    )
    monkeypatch.setattr(
        cli_module,
        "run_keon_json",
        lambda args, offline_mode_used=False: captured.extend(args) or type(
            "Result",
            (),
            {
                "returncode": 1,
                "stdout": "{}",
                "stderr": "",
                "payload": {},
                "offline_mode_used": offline_mode_used,
            },
        )(),
    )

    cli_module.verify_pack_json(str(pack_path), bundle_path=str(bundle_path))

    assert "--offline" in captured
    assert "--pubkey" in captured


def test_verify_caes_l3_06_is_false_when_cli_falls_back_without_offline(monkeypatch, tmp_path) -> None:
    pack_path = tmp_path / "pack.zip"
    pack_path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    class StubEvidencePack:
        artifacts = []
        policy_hash_manifest = None

    monkeypatch.setattr(verify_module, "EvidencePack", type("StubLoader", (), {"load": staticmethod(lambda _: StubEvidencePack())}))
    monkeypatch.setattr(
        verify_module,
        "verify_pack_json",
        lambda pack_path, bundle_path=None: type(
            "Result",
            (),
            {
                "payload": {
                    "is_valid": False,
                    "phase": 5,
                    "trust_bundle_provided": True,
                    "errors": [],
                },
                "offline_mode_used": False,
            },
        )(),
    )

    result = verify_caes(str(pack_path), bundle_path="bundle.json")

    assert result.l3_06 is False
