"""Audit project-aware dry-run outputs for pipeline validation."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from investment_system.pipelines.sector_research.build_dry_run_outputs import (
    DRY_RUN_MARKER,
    build_dry_run_records,
    get_dry_run_output_dir,
)
from investment_system.pipelines.sector_research.load_project import (
    WORKSPACE_ROOT,
    ProjectConfig,
    get_output_contract,
    get_sector,
    get_stocks_for_sector,
    list_output_types,
    load_project,
)


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    file: str = ""


# Patterns that indicate formal investment conclusions
INVESTMENT_ACTION_PATTERNS = [
    (re.compile(r"建议买入|建议建仓|建议加仓|建议持有|强烈推荐"), "formal_buy_recommendation"),
    (re.compile(r"目标价|目标市值"), "price_target"),
    (re.compile(r"[ABC]级评级"), "abc_rating"),
    (re.compile(r"建仓|加仓|买入"), "position_building"),
]


def _counts(findings: list[Finding]) -> dict[str, int]:
    return {
        "ERROR": sum(1 for f in findings if f.severity == "ERROR"),
        "WARNING": sum(1 for f in findings if f.severity == "WARNING"),
        "INFO": sum(1 for f in findings if f.severity == "INFO"),
    }


def _audit_record_shapes(
    config: ProjectConfig,
    sector_id: str,
    records: dict[str, Any],
    findings: list[Finding],
) -> dict[str, int]:
    """Audit dry-run records against output contracts."""
    pass_count = 0
    fail_count = 0
    
    required_types = ["sector_card", "company_table", "sector_comparison_table", 
                      "source_index", "missing_data_log", "conflict_data_log", "score_table"]
    
    for output_type in required_types:
        if output_type not in records or not records[output_type]:
            fail_count += 1
            findings.append(Finding(
                "ERROR",
                "DRY_RUN_OUTPUT_TYPE_MISSING",
                f"Missing dry-run output type: {output_type}",
                output_type
            ))
        else:
            pass_count += 1
    
    return {"dry_run_type_pass_count": pass_count, "dry_run_type_fail_count": fail_count}


def _audit_source_id_closure(
    records: dict[str, Any],
    findings: list[Finding],
) -> None:
    """Audit source_id/evidence_id closure."""
    source_index = records.get("source_index", [])
    if not source_index:
        findings.append(Finding(
            "WARNING",
            "DRY_RUN_SOURCE_INDEX_EMPTY",
            "source_index is empty; source_id closure cannot be verified.",
        ))
        return
    
    # Collect all source_ids from source_index
    defined_source_ids = set()
    for source in source_index:
        if isinstance(source, dict):
            sid = source.get("source_id")
            if sid:
                defined_source_ids.add(sid)
    
    # Check source_ids in other records
    for output_type, data in records.items():
        if output_type == "source_index":
            continue
        
        if isinstance(data, list):
            for record in data:
                _check_source_ids_in_record(record, defined_source_ids, output_type, findings)
        elif isinstance(data, dict):
            _check_source_ids_in_record(data, defined_source_ids, output_type, findings)


def _check_source_ids_in_record(
    record: dict[str, Any],
    defined_source_ids: set[str],
    output_type: str,
    findings: list[Finding],
) -> None:
    """Check source_ids/evidence_ids in a single record."""
    sid = record.get("source_ids", "")
    eid = record.get("evidence_ids", "")
    
    if sid and sid != "NO_SOURCE_ID" and not any(s in defined_source_ids for s in str(sid).split(",")):
        findings.append(Finding(
            "WARNING",
            "DRY_RUN_SOURCE_ID_NOT_IN_SOURCE_INDEX",
            f"{output_type} references source_ids not in source_index: {sid}",
        ))
    
    if not sid or sid == "NO_SOURCE_ID":
        findings.append(Finding(
            "INFO",
            "DRY_RUN_SOURCE_ID_MISSING",
            f"{output_type} has no source_ids (may be expected in dry-run)",
        ))


def _audit_no_investment_conclusion(
    records: dict[str, Any],
    findings: list[Finding],
) -> None:
    """Audit that no formal investment conclusions are present."""
    for output_type, data in records.items():
        if isinstance(data, list):
            for record in data:
                _check_investment_conclusions_in_text(str(record), output_type, findings)
        elif isinstance(data, dict):
            _check_investment_conclusions_in_text(str(data), output_type, findings)
        
        # Also check markdown sector card
        if output_type == "sector_card" and isinstance(data, dict):
            card_text = str(data)
            for pattern, code in INVESTMENT_ACTION_PATTERNS:
                if pattern.search(card_text):
                    findings.append(Finding(
                        "ERROR",
                        f"DRY_RUN_FORMAL_INVESTMENT_{code.upper()}",
                        f"sector_card contains formal investment language: {pattern.pattern}",
                    ))


def _check_investment_conclusions_in_text(
    text: str,
    output_type: str,
    findings: list[Finding],
) -> None:
    """Check investment conclusion patterns in text."""
    for pattern, code in INVESTMENT_ACTION_PATTERNS:
        if pattern.search(text):
            findings.append(Finding(
                "ERROR",
                f"DRY_RUN_FORMAL_INVESTMENT_{code.upper()}",
                f"{output_type} contains formal investment language: {pattern.pattern}",
            ))


def _audit_dry_run_directory_pollution(
    config: ProjectConfig,
    sector_id: str,
    findings: list[Finding],
) -> dict[str, int]:
    """Audit that dry-run outputs are isolated from formal directories."""
    dry_run_dir = get_dry_run_output_dir(config)
    formal_root = config.output_root.resolve()
    
    pollution_count = 0
    dry_run_file_count = 0
    
    if dry_run_dir.exists():
        for f in dry_run_dir.glob(f"dry_run_{sector_id}_*"):
            dry_run_file_count += 1
            resolved = f.resolve()
            
            # Check not in formal output root
            if str(resolved).startswith(str(formal_root)):
                pollution_count += 1
                findings.append(Finding(
                    "ERROR",
                    "DRY_RUN_FILE_IN_FORMAL_OUTPUT_ROOT",
                    f"Dry-run file found in formal output root: {f}",
                    str(f)
                ))
            
            # Check in correct audit directory
            if not str(resolved).startswith(str(dry_run_dir.resolve())):
                pollution_count += 1
                findings.append(Finding(
                    "ERROR",
                    "DRY_RUN_FILE_OUTSIDE_AUDIT_DIR",
                    f"Dry-run file outside audit directory: {f}",
                    str(f)
                ))
            
            # Check for dry_run marker
            try:
                content = f.read_text(encoding="utf-8-sig", errors="ignore")
                if DRY_RUN_MARKER not in content:
                    findings.append(Finding(
                        "WARNING",
                        "DRY_RUN_FILE_MARKER_MISSING",
                        f"Dry-run file lacks marker: {f}",
                        str(f)
                    ))
            except Exception:
                pass
    
    # Check formal output root for accidental dry_run files
    if formal_root.exists():
        for f in formal_root.rglob("dry_run_*"):
            pollution_count += 1
            findings.append(Finding(
                "ERROR",
                "DRY_RUN_FILE_IN_FORMAL_OUTPUT_ROOT",
                f"Dry-run file found in formal output root: {f}",
                str(f)
            ))
    
    return {"dry_run_file_count": dry_run_file_count, "pollution_count": pollution_count}


def _audit_stock_universe_reference(
    config: ProjectConfig,
    sector_id: str,
    records: dict[str, Any],
    findings: list[Finding],
) -> None:
    """Audit stock_universe.yaml reference."""
    try:
        stocks = get_stocks_for_sector(config, sector_id)
        if not stocks:
            findings.append(Finding(
                "WARNING",
                "DRY_RUN_NO_STOCKS",
                f"No stocks found for sector {sector_id} in stock_universe",
            ))
        else:
            findings.append(Finding(
                "INFO",
                "DRY_RUN_STOCKS_FROM_UNIVERSE",
                f"Found {len(stocks)} stocks from stock_universe.yaml for {sector_id}",
            ))
    except Exception as e:
        findings.append(Finding(
            "ERROR",
            "DRY_RUN_STOCK_UNIVERSE_ERROR",
            f"Error loading stocks from stock_universe.yaml: {e}",
        ))


def _audit_evidence_reference(
    config: ProjectConfig,
    sector_id: str,
    findings: list[Finding],
) -> dict[str, Any]:
    """Audit evidence file resolution."""
    try:
        from investment_system.pipelines.sector_research.load_project import resolve_evidence_files_for_sector
        
        evidence_files = resolve_evidence_files_for_sector(config, sector_id)
        findings.append(Finding(
            "INFO",
            "DRY_RUN_EVIDENCE_FILES_RESOLVED",
            f"Resolved {len(evidence_files)} evidence files for {sector_id}",
        ))
        
        return {"evidence_file_count": len(evidence_files), "evidence_files": [str(f) for f in evidence_files]}
    except Exception as e:
        findings.append(Finding(
            "ERROR",
            "DRY_RUN_EVIDENCE_RESOLUTION_ERROR",
            f"Error resolving evidence files: {e}",
        ))
        return {"evidence_file_count": 0, "evidence_files": [], "error": str(e)}


def audit_project(
    project_id: str,
    sector_id: str,
    write_report: bool = True,
) -> tuple[list[Finding], dict[str, Any]]:
    """Run full dry-run output audit."""
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    findings: list[Finding] = []
    
    # Build records
    try:
        records = build_dry_run_records(config, sector_id)
    except Exception as e:
        findings.append(Finding(
            "ERROR",
            "DRY_RUN_BUILD_ERROR",
            f"Error building dry-run records: {e}",
        ))
        summary = {"ERROR": 1, "WARNING": 0, "INFO": 0, "sector_id": sector_id}
        return findings, summary
    
    # Run audits
    shape_counts = _audit_record_shapes(config, sector_id, records, findings)
    _audit_source_id_closure(records, findings)
    _audit_no_investment_conclusion(records, findings)
    dir_counts = _audit_dry_run_directory_pollution(config, sector_id, findings)
    _audit_stock_universe_reference(config, sector_id, records, findings)
    evidence_info = _audit_evidence_reference(config, sector_id, findings)
    
    counts = _counts(findings)
    summary = {
        **counts,
        "project_id": project_id,
        "sector_id": sector_id,
        "dry_run_file_count": dir_counts["dry_run_file_count"],
        "pollution_count": dir_counts["pollution_count"],
        **shape_counts,
        **evidence_info,
    }
    
    if write_report:
        _write_report(project_id, sector_id, findings, summary)
    
    return findings, summary


def _write_report(project_id: str, sector_id: str, findings: list[Finding], summary: dict[str, Any]) -> None:
    """Write audit report to file."""
    audit_dir = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / "dry_run_output_audit.md"
    
    lines = [
        "# Dry-Run Output Audit — Phase 1E-f",
        "",
        f"Project: `{project_id}`",
        f"Sector ID: `{sector_id}`",
        f"Audit Date: {summary.get('audit_date', 'N/A')}",
        "",
        "## Summary",
        f"- ERROR: {summary.get('ERROR', 0)}",
        f"- WARNING: {summary.get('WARNING', 0)}",
        f"- INFO: {summary.get('INFO', 0)}",
        f"- dry_run_file_count: {summary.get('dry_run_file_count', 0)}",
        f"- pollution_count: {summary.get('pollution_count', 0)}",
        f"- dry_run_type_pass_count: {summary.get('dry_run_type_pass_count', 0)}",
        f"- evidence_file_count: {summary.get('evidence_file_count', 0)}",
        "",
        "## Findings",
    ]
    
    for severity in ["ERROR", "WARNING", "INFO"]:
        rows = [f for f in findings if f.severity == severity]
        if not rows:
            continue
        lines.append(f"\n### {severity}\n")
        for f in rows:
            loc = f" (`{f.file}`)" if f.file else ""
            lines.append(f"- `{f.code}`{loc}: {f.message}")
    
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_summary(findings: list[Finding], summary: dict[str, Any]) -> None:
    """Print audit summary to console."""
    print("Dry-Run Output Audit")
    print("=" * 60)
    print(f"project_id: {summary.get('project_id')}")
    print(f"sector_id: {summary.get('sector_id')}")
    print(f"ERROR: {summary.get('ERROR', 0)}")
    print(f"WARNING: {summary.get('WARNING', 0)}")
    print(f"INFO: {summary.get('INFO', 0)}")
    print(f"dry_run_file_count: {summary.get('dry_run_file_count', 0)}")
    print(f"pollution_count: {summary.get('pollution_count', 0)}")
    print()
    
    if findings:
        print("Findings:")
        for f in findings:
            loc = f" ({f.file})" if f.file else ""
            print(f"  [{f.severity}] {f.code}{loc}: {f.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit project-aware dry-run outputs.")
    parser.add_argument("--project", required=True, help="Project ID")
    parser.add_argument("--sector-id", required=True, help="Canonical sector_id")
    args = parser.parse_args(argv)
    
    findings, summary = audit_project(args.project, args.sector_id, write_report=True)
    _print_summary(findings, summary)
    
    return 1 if summary.get("ERROR", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
