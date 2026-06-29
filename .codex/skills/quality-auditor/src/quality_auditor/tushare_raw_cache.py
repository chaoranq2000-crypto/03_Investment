"""Audit Tushare raw-cache envelopes produced by skill data routers."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from investment_system.core.constants import WORKSPACE_ROOT


SECRET_KEY_RE = re.compile(r"(token|api[_-]?key|secret|password)", re.IGNORECASE)
LONG_HEX_RE = re.compile(r"\b[a-fA-F0-9]{32,}\b")


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _iter_json_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def _walk_values(value: Any, key_path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            next_key = f"{key_path}.{key}" if key_path else str(key)
            found.append((next_key, str(key)))
            found.extend(_walk_values(item, next_key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_values(item, f"{key_path}[{index}]"))
    elif isinstance(value, str):
        found.append((key_path, value))
    return found


def _audit_file(path: Path) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [("ERROR", f"{path}: invalid json: {type(exc).__name__}: {exc}")]
    if not isinstance(payload, dict):
        return [("ERROR", f"{path}: top-level JSON is not an object")]

    schema = str(payload.get("schema_version") or "")
    if schema and schema != "tushare_raw_cache.v1":
        findings.append(("ERROR", f"{path}: unsupported schema_version={schema}"))
    if schema == "tushare_raw_cache.v1":
        for field in ("source", "dataset", "api_name", "request", "fetched_at", "fetch_status", "rows"):
            if field not in payload:
                findings.append(("ERROR", f"{path}: missing envelope field {field}"))
        if payload.get("source") != "tushare":
            findings.append(("ERROR", f"{path}: source is not tushare"))

    for key_path, text in _walk_values(payload):
        if SECRET_KEY_RE.search(key_path) or SECRET_KEY_RE.search(text):
            findings.append(("ERROR", f"{path}: token/key-like field or value found at {key_path}: {text[:80]}"))
        elif LONG_HEX_RE.search(text) and "sha256" not in key_path.lower():
            findings.append(("WARN", f"{path}: long hex-like value found at {key_path}; verify it is not a token"))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Tushare raw-cache JSON files for schema and secret leakage.")
    parser.add_argument("--path", default="investment_system/data/raw/tushare")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    root = _resolve_path(args.path)
    files = _iter_json_files(root)
    findings: list[dict[str, str]] = []
    for path in files:
        for severity, message in _audit_file(path):
            findings.append({"severity": severity, "message": message})

    payload = {
        "audit": "tushare-raw-cache",
        "path": str(root),
        "files_checked": len(files),
        "error_count": sum(1 for item in findings if item["severity"] == "ERROR"),
        "warn_count": sum(1 for item in findings if item["severity"] == "WARN"),
        "findings": findings,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Tushare raw-cache audit")
        print(f"path: {payload['path']}")
        print(f"files_checked: {payload['files_checked']}")
        print(f"error_count: {payload['error_count']}")
        print(f"warn_count: {payload['warn_count']}")
        for item in findings:
            print(f"- {item['severity']}: {item['message']}")
    return 1 if payload["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
