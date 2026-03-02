from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .evidence_pack import EvidencePack


class KeonCliError(RuntimeError):
    pass


class KeonCliNotFoundError(KeonCliError):
    pass


@dataclass(frozen=True)
class KeonCliResult:
    returncode: int
    stdout: str
    stderr: str
    payload: dict[str, Any]
    offline_mode_used: bool = False


def resolve_keon_cli() -> list[str]:
    env_path = os.environ.get("KEON_CLI_PATH")
    if env_path:
        return [env_path]

    on_path = shutil.which("keon")
    if on_path:
        return [on_path]

    repo_root = Path(__file__).resolve().parents[3]
    candidates = (
        repo_root / "keon-systems" / "src" / "Keon.Cli" / "bin" / "Debug" / "net10.0" / "Keon.Cli.exe",
        repo_root / "keon-systems" / "src" / "Keon.Cli" / "bin" / "Release" / "net10.0" / "Keon.Cli.exe",
        repo_root / "keon-systems" / "src" / "Keon.Cli" / "bin" / "Debug" / "net10.0" / "Keon.Cli.dll",
        repo_root / "keon-systems" / "src" / "Keon.Cli" / "bin" / "Release" / "net10.0" / "Keon.Cli.dll",
    )
    for candidate in candidates:
        if candidate.exists():
            if candidate.suffix == ".dll":
                return ["dotnet", str(candidate)]
            return [str(candidate)]

    raise KeonCliNotFoundError(
        "Unable to locate the Keon CLI. Set KEON_CLI_PATH or install the keon executable."
    )


def run_keon_json(args: list[str], *, offline_mode_used: bool = False) -> KeonCliResult:
    command = [*resolve_keon_cli(), *args]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = completed.stdout.strip()
    if not stdout:
        raise KeonCliError(completed.stderr.strip() or "Keon CLI produced no JSON output.")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise KeonCliError(f"Keon CLI returned non-JSON output: {stdout}") from exc
    if not isinstance(payload, dict):
        raise KeonCliError("Keon CLI JSON output must be an object.")
    return KeonCliResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        payload=payload,
        offline_mode_used=offline_mode_used,
    )


def verify_pack_json(pack_path: str, bundle_path: str | None = None) -> KeonCliResult:
    args = ["verify-pack", "--path", pack_path]
    temp_pubkey_path: str | None = None
    offline_mode_requested = bundle_path is not None
    if bundle_path:
        args.extend(["--offline", "--trust-bundle", bundle_path])
        public_key_b64 = _resolve_public_key_from_bundle(pack_path, bundle_path)
        if public_key_b64:
            with NamedTemporaryFile("w", suffix=".pub", delete=False, encoding="utf-8") as handle:
                handle.write(public_key_b64)
                temp_pubkey_path = handle.name
            args.extend(["--pubkey", temp_pubkey_path])
    try:
        try:
            return run_keon_json(args, offline_mode_used=offline_mode_requested)
        except KeonCliError as exc:
            if not offline_mode_requested or not _is_unknown_offline_flag(exc):
                raise
            fallback_args = [arg for arg in args if arg != "--offline"]
            return run_keon_json(fallback_args, offline_mode_used=False)
    finally:
        if temp_pubkey_path:
            Path(temp_pubkey_path).unlink(missing_ok=True)


def export_pack_json(cli_args: list[str]) -> KeonCliResult:
    return run_keon_json(["export-pack", *cli_args])


def _is_unknown_offline_flag(error: KeonCliError) -> bool:
    message = str(error).lower()
    return "unknown option" in message and "--offline" in message or "unrecognized option" in message and "--offline" in message


def _resolve_public_key_from_bundle(pack_path: str, bundle_path: str) -> str | None:
    pack = EvidencePack.load(pack_path)
    bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    bundle_payload = bundle.get("payload", bundle) if isinstance(bundle, dict) else {}
    if not isinstance(bundle_payload, dict):
        return None
    tenants = bundle_payload.get("tenants", [])
    if not isinstance(tenants, list):
        return None

    signer_kid = _find_signer_kid(pack)
    tenant_id = _find_tenant_id(pack)
    matching_tenants = [
        tenant
        for tenant in tenants
        if isinstance(tenant, dict)
        and (tenant_id is None or tenant.get("tenant_id", tenant.get("tenantId")) == tenant_id)
    ]
    for tenant in matching_tenants:
        keys = tenant.get("keys", [])
        if not isinstance(keys, list):
            continue
        for key in keys:
            if not isinstance(key, dict):
                continue
            if signer_kid and key.get("kid") != signer_kid:
                continue
            public_key = key.get("public_key_b64", key.get("publicKeyB64"))
            if isinstance(public_key, str) and public_key:
                return public_key
    for tenant in matching_tenants:
        keys = tenant.get("keys", [])
        if isinstance(keys, list):
            for key in keys:
                if isinstance(key, dict):
                    public_key = key.get("public_key_b64", key.get("publicKeyB64"))
                    if isinstance(public_key, str) and public_key:
                        return public_key
    return None


def _find_signer_kid(pack: EvidencePack) -> str | None:
    for artifact in pack.artifacts:
        payload = artifact.payload
        if artifact.type == "attestation" and isinstance(payload, dict):
            key_id = payload.get("key_id")
            if isinstance(key_id, str) and key_id:
                return key_id
    return None


def _find_tenant_id(pack: EvidencePack) -> str | None:
    for artifact in pack.artifacts:
        payload = artifact.payload
        if artifact.type == "receipt" and isinstance(payload, dict):
            tenant_id = payload.get("tenant_id")
            if isinstance(tenant_id, str) and tenant_id:
                return tenant_id
    for artifact in pack.artifacts:
        payload = artifact.payload
        if artifact.type == "attestation" and isinstance(payload, dict):
            tenant_id = payload.get("tenant_id")
            if isinstance(tenant_id, str) and tenant_id:
                return tenant_id
    return None
