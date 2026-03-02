from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZipFile


@dataclass(frozen=True)
class Artifact:
    name: str
    type: str
    sha256: str | None
    version: str | None
    payload: dict[str, Any] | None


@dataclass(frozen=True)
class PolicyHashManifest:
    artifact: Artifact
    payload: dict[str, Any]


@dataclass(frozen=True)
class EvidencePack:
    artifacts: list[Artifact]
    policy_hash_manifest: PolicyHashManifest | None

    @classmethod
    def load(cls, path: str) -> "EvidencePack":
        pack_path = Path(path)
        with ZipFile(pack_path) as archive:
            manifest_name = "manifest.json"
            if manifest_name not in archive.namelist() and "pack_manifest.json" in archive.namelist():
                manifest_name = "pack_manifest.json"
            manifest = json.loads(archive.read(manifest_name))
            artifact_specs = manifest.get("artifacts", [])
            artifacts: list[Artifact] = []
            policy_hash_manifest: PolicyHashManifest | None = None
            for spec in artifact_specs:
                name = str(spec["name"])
                payload = _read_json_entry(archive, name)
                artifact = Artifact(
                    name=name,
                    type=str(spec.get("type", "")),
                    sha256=_as_str_or_none(spec.get("sha256")),
                    version=_as_str_or_none(spec.get("version")),
                    payload=payload,
                )
                artifacts.append(artifact)
                if _is_policy_hash_artifact(artifact):
                    policy_hash_manifest = PolicyHashManifest(artifact=artifact, payload=payload or {})
            return cls(artifacts=artifacts, policy_hash_manifest=policy_hash_manifest)


def _read_json_entry(archive: ZipFile, name: str) -> dict[str, Any] | None:
    try:
        raw = archive.read(name)
    except KeyError:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _is_policy_hash_artifact(artifact: Artifact) -> bool:
    slug = artifact.name.lower()
    artifact_type = artifact.type.lower()
    # TODO(WS-D): Replace this heuristic with the canonical artifact schema id once the extension lands.
    return "policy" in slug and "hash" in slug or "policy_hash" in artifact_type


def _as_str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None
