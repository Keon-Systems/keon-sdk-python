from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Any

from ._cli import export_pack_json
from .verify import verify_caes


TOOLS = [
    {
        "name": "verify_pack",
        "description": "Verify a Keon evidence pack and return the CLI JSON contract.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pack_path": {"type": "string"},
                "bundle_path": {"type": ["string", "null"]},
            },
            "required": ["pack_path"],
        },
    },
    {
        "name": "export_pack",
        "description": "Pass through to keon export-pack using explicit CLI args.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cli_args": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            "required": ["cli_args"],
        },
    },
    {
        "name": "check_l3_compliance",
        "description": "Verify a pack and return the typed L3 invariant result.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pack_path": {"type": "string"},
                "bundle_path": {"type": ["string", "null"]},
            },
            "required": ["pack_path"],
        },
    },
]


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        response = handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        return _ok(request_id, {"protocolVersion": "2025-11-05", "serverInfo": {"name": "keon-sdk", "version": "1.0.0"}})
    if method == "tools/list":
        return _ok(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        return _ok(request_id, {"content": [{"type": "json", "json": _call_tool(name, arguments)}]})
    return _error(request_id, -32601, "Method not found")


def _call_tool(name: Any, arguments: Any) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")
    if name == "verify_pack":
        result = verify_caes(arguments["pack_path"], bundle_path=arguments.get("bundle_path"))
        return dict(result.raw_report)
    if name == "export_pack":
        cli_args = arguments["cli_args"]
        if not isinstance(cli_args, list) or not all(isinstance(item, str) for item in cli_args):
            raise ValueError("cli_args must be an array of strings.")
        return export_pack_json(cli_args).payload
    if name == "check_l3_compliance":
        return asdict(verify_caes(arguments["pack_path"], bundle_path=arguments.get("bundle_path")))
    raise ValueError(f"Unknown tool: {name}")


def _ok(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

