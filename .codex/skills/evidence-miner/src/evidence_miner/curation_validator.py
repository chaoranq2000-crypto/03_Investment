"""Validate that an evidence YAML file is curated before registration."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from investment_system.core.project_loader import WORKSPACE_ROOT


DRAFT_MARKERS = [
    "DRAFT_PLACEHOLDER",
    "TODO_MANUAL_EXTRACTION",
    "draft_source_skeleton",
]


@dataclass
class Finding:
    severity: str
    code: str
    message: str


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"evidence YAML is not a mapping: {path}")
    return data


def _load_manifest_source_ids(paths: list[Path]) -> set[str]:
    source_ids: set[str] = set()
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for record in data.get("records", []) or []:
            source_id = str(record.get("source_id") or "").strip()
            if source_id:
                source_ids.add(source_id)
    return source_ids


def _contains_draft_marker(value: Any) -> bool:
    text = yaml.safe_dump(value, allow_unicode=True, sort_keys=False)
    return any(marker in text for marker in DRAFT_MARKERS)


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def validate_evidence_data(
    data: dict[str, Any],
    *,
    manifest_source_ids: set[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    status = str(data.get("status") or "").strip()
    if status == "draft_source_skeleton":
        findings.append(Finding("ERROR", "DRAFT_STATUS_NOT_REGISTERABLE", "status=draft_source_skeleton is not active evidence."))
    if _contains_draft_marker(data):
        findings.append(Finding("ERROR", "DRAFT_PLACEHOLDER_PRESENT", "Draft placeholder markers remain in the evidence YAML."))

    source_index = data.get("source_index") or []
    evidence_items = data.get("evidence_items") or []
    if not isinstance(source_index, list) or not source_index:
        findings.append(Finding("ERROR", "SOURCE_INDEX_MISSING", "source_index[] is missing or empty."))
        source_index = []
    if not isinstance(evidence_items, list) or not evidence_items:
        findings.append(Finding("ERROR", "EVIDENCE_ITEMS_MISSING", "evidence_items[] is missing or empty."))
        evidence_items = []

    source_ids = {str(row.get("source_id") or "").strip() for row in source_index if isinstance(row, dict)}
    source_ids.discard("")
    if manifest_source_ids is not None:
        unknown = source_ids - manifest_source_ids
        if unknown:
            findings.append(Finding("ERROR", "SOURCE_ID_NOT_IN_SOURCE_MANIFEST", f"source_index references sources not found in source manifest: {sorted(unknown)}"))

    required_item_fields = [
        "evidence_id",
        "sector_id",
        "evidence_level",
        "evidence_type",
        "extracted_text",
        "claim",
        "limitation",
        "missing_fields",
    ]
    for index, item in enumerate(evidence_items):
        if not isinstance(item, dict):
            findings.append(Finding("ERROR", "EVIDENCE_ITEM_NOT_MAPPING", f"evidence_items[{index}] is not a mapping."))
            continue
        evidence_id = str(item.get("evidence_id") or "").strip()
        if evidence_id.startswith("EV-DRAFT-"):
            findings.append(Finding("ERROR", "DRAFT_EVIDENCE_ID_PRESENT", f"draft evidence_id is not registerable: {evidence_id}"))
        missing_fields = [field for field in required_item_fields if _is_missing(item.get(field))]
        if missing_fields:
            findings.append(Finding("ERROR", "CURATED_FIELD_MISSING", f"{evidence_id or index} missing fields: {missing_fields}"))
        item_sources = set()
        if item.get("source_id"):
            item_sources.add(str(item.get("source_id")).strip())
        for source_id in item.get("source_ids") or []:
            if str(source_id).strip():
                item_sources.add(str(source_id).strip())
        if not item_sources:
            findings.append(Finding("ERROR", "EVIDENCE_ITEM_SOURCE_MISSING", f"{evidence_id or index} has no source_id/source_ids."))
        unknown_sources = item_sources - source_ids
        if unknown_sources:
            findings.append(Finding("ERROR", "EVIDENCE_ITEM_SOURCE_NOT_IN_INDEX", f"{evidence_id or index} references unknown source_ids: {sorted(unknown_sources)}"))
        if _is_missing(item.get("metrics_supported")):
            findings.append(Finding("ERROR", "METRICS_SUPPORTED_MISSING", f"{evidence_id or index} missing metrics_supported."))
        if "draft_placeholder" in {str(x) for x in (item.get("metrics_supported") or [])}:
            findings.append(Finding("ERROR", "DRAFT_METRIC_PRESENT", f"{evidence_id or index} still uses draft_placeholder metric."))

    if not any(f.severity == "ERROR" for f in findings):
        findings.append(Finding("INFO", "CURATED_EVIDENCE_READY", "Evidence YAML has no draft markers and required curated fields are present."))
    return findings


def validate_evidence_file(evidence_path: Path, manifest_paths: list[Path] | None = None) -> list[Finding]:
    data = _read_yaml(evidence_path)
    manifest_source_ids = _load_manifest_source_ids(manifest_paths or []) if manifest_paths else None
    return validate_evidence_data(data, manifest_source_ids=manifest_source_ids)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Validate curated evidence YAML before registration.")
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--source-manifest", action="append", default=[])
    args = parser.parse_args(argv)

    try:
        evidence_path = _resolve_path(args.evidence_path)
        manifest_paths = [_resolve_path(path) for path in args.source_manifest]
        findings = validate_evidence_file(evidence_path, manifest_paths)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    error_count = sum(1 for finding in findings if finding.severity == "ERROR")
    warning_count = sum(1 for finding in findings if finding.severity == "WARNING")
    info_count = sum(1 for finding in findings if finding.severity == "INFO")
    print("Curated Evidence Validation")
    print(f"evidence_path: {evidence_path}")
    print(f"ERROR: {error_count}")
    print(f"WARNING: {warning_count}")
    print(f"INFO: {info_count}")
    for finding in findings:
        print(f"[{finding.severity}] {finding.code}: {finding.message}")
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
