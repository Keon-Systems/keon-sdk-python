import json
from pathlib import Path
from zipfile import ZipFile

from keon_sdk import EvidencePack


def test_load_evidence_pack_reads_artifacts_and_policy_hash_manifest(tmp_path: Path) -> None:
    pack_path = tmp_path / "pack.zip"
    manifest = {
        "artifacts": [
            {
                "name": "artifacts/policy-hash-manifest.json",
                "type": "policy_hash_manifest",
                "sha256": "abc",
                "version": "v1",
            },
            {
                "name": "receipts/r1.json",
                "type": "receipt",
                "sha256": "def",
                "version": "v1",
            },
        ]
    }
    with ZipFile(pack_path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("artifacts/policy-hash-manifest.json", json.dumps({"policy_hash": "abc"}))
        archive.writestr("receipts/r1.json", json.dumps({"receipt_id": "r1"}))

    pack = EvidencePack.load(str(pack_path))

    assert len(pack.artifacts) == 2
    assert pack.policy_hash_manifest is not None
    assert pack.policy_hash_manifest.payload["policy_hash"] == "abc"

