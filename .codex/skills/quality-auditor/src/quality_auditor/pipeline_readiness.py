"""Audit the active project-aware runtime boundary.

This audit intentionally treats removed compatibility entry points as forbidden.
The old investment_system/pipelines path is retired and should not contain
source files or directory-marker documentation.
It does not inspect historical audit logs or generated research outputs.
Retired compatibility checks report only regressions by default; pass
--include-retired-checks to show successful absence confirmations.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from investment_system.core.constants import WORKSPACE_ROOT
from investment_system.core.output_contracts import get_output_contract, list_output_types
from investment_system.core.project_loader import load_project
from investment_system.core.sector_runtime import resolve_sector_context


TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml"}

REMOVED_RUNTIME_FILES = [
    "investment_system/core/legacy_cli.py",
    "investment_system/core/legacy_broad_cli.py",
    "investment_system/core/legacy_broad_collection.py",
    "investment_system/core/legacy_broad_runner.py",
    ".codex/skills/research-writer/src/research_writer/legacy_broad_outputs.py",
    ".codex/skills/quality-auditor/src/quality_auditor/retired_surfaces.py",
]

FORBIDDEN_ACTIVE_TOKENS = {
    "LegacyCommand": "old command delegator type",
    "dispatch_legacy_commands": "old command delegator function",
    "investment_system.core.legacy_cli": "removed command delegator module",
    "investment_system.core.legacy_broad_cli": "removed broad-runner CLI",
    "investment_system.core.legacy_broad_runner": "removed broad-runner module",
    "investment_system.core.legacy_broad_collection": "removed broad-runner collection module",
    "research_writer.legacy_broad_outputs": "removed generated-output adapter",
    "quality_auditor.retired_surfaces": "removed retired-surface audit module",
    "retired-surfaces": "removed retired-surface CLI command",
    "legacy-daily-kline": "removed market-data command",
    "legacy-index-daily": "removed market-data command",
    "investment_system.pipelines.sector_research": "removed pipeline wrapper package",
}

SELF_AUDIT_FILES = {
    ".codex/skills/quality-auditor/src/quality_auditor/pipeline_readiness.py",
    ".codex/skills/quality-auditor/src/quality_auditor/output_schema.py",
}


@dataclass
class AuditFinding:
    file: str
    category: str
    severity: str
    code: str
    message: str
    location: str = ""
    recommendation: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "file": self.file,
            "category": self.category,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "location": self.location,
            "recommendation": self.recommendation,
        }


def _rel(path: Path) -> str:
    return str(path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")


def _iter_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = root.rglob("*")
        for path in candidates:
            if path.is_dir():
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(part in {".git", "__pycache__", ".venv", ".conda"} for part in path.parts):
                continue
            yield path


def _add(
    findings: list[AuditFinding],
    severity: str,
    code: str,
    message: str,
    file: str = "",
    category: str = "runtime_boundary",
    recommendation: str = "",
) -> None:
    findings.append(
        AuditFinding(
            file=file,
            category=category,
            severity=severity,
            code=code,
            message=message,
            recommendation=recommendation,
        )
    )


def _check_removed_runtime_files(findings: list[AuditFinding], include_retired_checks: bool) -> None:
    for rel_path in REMOVED_RUNTIME_FILES:
        path = WORKSPACE_ROOT / rel_path
        if path.exists():
            _add(
                findings,
                "HIGH",
                "REMOVED_RUNTIME_FILE_PRESENT",
                "A removed compatibility runtime file is still present.",
                rel_path,
                recommendation="Delete this explicit file path after confirming active callers are gone.",
            )
        elif include_retired_checks:
            _add(
                findings,
                "INFO",
                "REMOVED_RUNTIME_FILE_ABSENT",
                "Removed compatibility runtime file is absent.",
                rel_path,
            )


def _check_pipeline_directory(findings: list[AuditFinding], include_retired_checks: bool) -> None:
    pipelines_root = WORKSPACE_ROOT / "investment_system" / "pipelines"
    if not pipelines_root.exists():
        if include_retired_checks:
            _add(findings, "INFO", "PIPELINE_DIRECTORY_ABSENT", "retired pipeline directory is absent.")
        return

    source_files = [
        _rel(path)
        for path in pipelines_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.lower() != ".pyc"
    ]
    if source_files:
        _add(
            findings,
            "HIGH",
            "PIPELINE_DIRECTORY_STILL_HAS_FILES",
            f"retired pipeline directory contains source/documentation file(s): {sorted(source_files)}",
            "investment_system/pipelines",
            recommendation="Delete explicit files and stop documenting investment_system/pipelines as a valid project boundary.",
        )
    elif include_retired_checks:
        _add(
            findings,
            "INFO",
            "PIPELINE_DIRECTORY_ONLY_IGNORED_CACHE",
            "retired pipeline directory contains no source/documentation files; only ignored cache directories may remain locally.",
            "investment_system/pipelines",
        )


def _check_active_references(findings: list[AuditFinding]) -> None:
    roots = [
        WORKSPACE_ROOT / "investment_system" / "core",
        WORKSPACE_ROOT / "investment_system" / "README.md",
        WORKSPACE_ROOT / ".codex" / "skills",
        WORKSPACE_ROOT / "investment_system" / "research" / "projects" / "tech_ai_semiconductor" / "workflow_stages.yaml",
    ]
    for path in _iter_files(roots):
        rel_path = _rel(path)
        if rel_path in SELF_AUDIT_FILES:
            continue
        if "/audits/" in rel_path or rel_path.endswith("skill_module_refactor_plan.md"):
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for token, label in FORBIDDEN_ACTIVE_TOKENS.items():
            if token not in content:
                continue
            _add(
                findings,
                "HIGH",
                "FORBIDDEN_ACTIVE_REFERENCE",
                f"Forbidden active reference remains: {token} ({label}).",
                rel_path,
                category="active_reference",
                recommendation="Route users through project-aware skill CLIs and core helpers only.",
            )


def _check_project_loader(project_id: str, findings: list[AuditFinding]) -> Any | None:
    try:
        config = load_project(project_id, silent=True, strict=False)
    except Exception as exc:  # noqa: BLE001
        _add(
            findings,
            "BLOCKER",
            "PROJECT_LOAD_FAILED",
            f"Project configuration failed to load: {exc}",
            f"investment_system/research/projects/{project_id}",
            category="project_loader",
        )
        return None

    errors = [w for w in config.warnings if w.severity == "error"]
    if errors:
        _add(
            findings,
            "HIGH",
            "PROJECT_LOAD_HAS_ERRORS",
            f"Project loaded with {len(errors)} error-severity validation issue(s).",
            f"investment_system/research/projects/{project_id}",
            category="project_loader",
            recommendation="Run project_loader --json and fix error-severity issues.",
        )
    else:
        _add(
            findings,
            "INFO",
            "PROJECT_LOAD_OK",
            f"Project loaded with {len(config.warnings)} warning(s) and no error-severity issues.",
            f"investment_system/research/projects/{project_id}",
            category="project_loader",
        )
    return config


def _check_canonical_sector_context(config: Any, findings: list[AuditFinding]) -> None:
    sectors = config.raw.get("sectors", [])
    first = next((s for s in sectors if s.get("sector_id")), None)
    if not first:
        _add(
            findings,
            "HIGH",
            "NO_CANONICAL_SECTOR",
            "No sector with sector_id found.",
            "sector_universe.yaml",
            category="canonical_sector",
        )
        return
    sector_id = first["sector_id"]
    try:
        ctx = resolve_sector_context(config, sector_id)
    except Exception as exc:  # noqa: BLE001
        _add(
            findings,
            "HIGH",
            "CANONICAL_SECTOR_CONTEXT_FAILED",
            f"Cannot resolve canonical sector_id '{sector_id}': {exc}",
            "investment_system/core/sector_runtime.py",
            category="canonical_sector",
        )
        return
    if ctx.sector_id != sector_id:
        _add(
            findings,
            "HIGH",
            "CANONICAL_SECTOR_ID_MUTATED",
            f"Canonical sector_id '{sector_id}' resolved to '{ctx.sector_id}'.",
            "investment_system/core/sector_runtime.py",
            category="canonical_sector",
        )
    else:
        _add(
            findings,
            "INFO",
            "CANONICAL_SECTOR_CONTEXT_OK",
            f"Canonical sector_id resolves directly: {sector_id}.",
            "investment_system/core/sector_runtime.py",
            category="canonical_sector",
        )


def _check_output_contracts(config: Any, findings: list[AuditFinding]) -> None:
    try:
        output_types = list_output_types(config)
    except Exception as exc:  # noqa: BLE001
        _add(
            findings,
            "HIGH",
            "OUTPUT_CONTRACT_LIST_FAILED",
            f"Cannot list output contract types: {exc}",
            "investment_system/research/schemas/output.schema.yaml",
            category="output_contract",
        )
        return
    missing_required: list[str] = []
    for output_type in output_types:
        contract = get_output_contract(config, output_type)
        if not contract.get("required_fields"):
            missing_required.append(output_type)
    if missing_required:
        _add(
            findings,
            "HIGH",
            "OUTPUT_CONTRACT_REQUIRED_FIELDS_MISSING",
            f"Output contracts missing required_fields: {missing_required}",
            "investment_system/research/schemas/output.schema.yaml",
            category="output_contract",
        )
    else:
        _add(
            findings,
            "INFO",
            "OUTPUT_CONTRACTS_OK",
            f"Loaded {len(output_types)} output contract type(s).",
            "investment_system/research/schemas/output.schema.yaml",
            category="output_contract",
        )


def _check_workflow_stage_commands(project_id: str, findings: list[AuditFinding]) -> None:
    path = WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "workflow_stages.yaml"
    if not path.exists():
        _add(
            findings,
            "HIGH",
            "WORKFLOW_STAGES_MISSING",
            "workflow_stages.yaml is missing.",
            _rel(path),
            category="workflow",
        )
        return
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    stage_map = (data.get("skill_cli_routing", {}) or {}).get("stages", {}) or {}
    bad_commands: list[str] = []
    for stage_name, stage in stage_map.items():
        commands = stage.get("preferred_cli", []) if isinstance(stage, dict) else []
        for command in commands:
            text = " ".join(str(part) for part in command) if isinstance(command, list) else str(command)
            if any(token in text for token in FORBIDDEN_ACTIVE_TOKENS):
                bad_commands.append(f"{stage_name}: {text}")
    if bad_commands:
        _add(
            findings,
            "HIGH",
            "WORKFLOW_STAGE_FORBIDDEN_COMMAND",
            f"workflow_stages.yaml still contains removed command(s): {bad_commands}",
            _rel(path),
            category="workflow",
        )
    else:
        _add(
            findings,
            "INFO",
            "WORKFLOW_STAGE_COMMANDS_OK",
            "workflow stage commands use project-aware skill CLI routes.",
            _rel(path),
            category="workflow",
        )


def _counts(findings: list[AuditFinding]) -> dict[str, int]:
    return {
        severity: sum(1 for f in findings if f.severity == severity)
        for severity in ["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]
    }


def _build_next_steps(counts: dict[str, int], include_retired_checks: bool) -> list[dict[str, str]]:
    if counts["BLOCKER"] or counts["HIGH"]:
        return [
            {
                "severity": "HIGH",
                "title": "Finish active compatibility removal",
                "description": "Delete remaining explicit removed files or update active guidance that still references them.",
            }
        ]
    description = (
        "No active runtime-boundary issues found; retired compatibility absence details are shown."
        if include_retired_checks
        else "No active runtime-boundary issues found; use --include-retired-checks for retired compatibility absence details."
    )
    return [
        {
            "severity": "info",
            "title": "Runtime boundary is clean",
            "description": description,
        }
    ]


def run_audit(project_id: str, include_retired_checks: bool = False) -> tuple[list[AuditFinding], dict[str, Any]]:
    findings: list[AuditFinding] = []
    _check_removed_runtime_files(findings, include_retired_checks)
    _check_pipeline_directory(findings, include_retired_checks)
    _check_active_references(findings)
    _check_workflow_stage_commands(project_id, findings)

    config = _check_project_loader(project_id, findings)
    if config is not None:
        _check_canonical_sector_context(config, findings)
        _check_output_contracts(config, findings)

    counts = _counts(findings)
    summary = {
        "project_id": project_id,
        "total_findings": len(findings),
        "BLOCKER_count": counts["BLOCKER"],
        "HIGH_count": counts["HIGH"],
        "MEDIUM_count": counts["MEDIUM"],
        "LOW_count": counts["LOW"],
        "INFO_count": counts["INFO"],
        "removed_runtime_file_count": len(REMOVED_RUNTIME_FILES),
        "retired_checks_included": include_retired_checks,
        "next_steps": _build_next_steps(counts, include_retired_checks),
    }
    return findings, summary


def print_audit_report(findings: list[AuditFinding], summary: dict[str, Any]) -> None:
    print("=" * 70)
    print(f" Pipeline Readiness Audit - {summary['project_id']}")
    print(f" Total findings: {summary['total_findings']}")
    print("=" * 70)

    for severity in ["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]:
        rows = [f for f in findings if f.severity == severity]
        if not rows:
            continue
        print(f"\n[{severity}] ({len(rows)})")
        by_file: dict[str, list[AuditFinding]] = {}
        for finding in rows:
            by_file.setdefault(finding.file or "(project)", []).append(finding)
        for file, file_rows in by_file.items():
            print(f"  {file}:")
            for finding in file_rows:
                print(f"    [{finding.code}] {finding.message}")
                if finding.recommendation:
                    print(f"      -> {finding.recommendation}")

    print("\nSummary by severity:")
    for key in ["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]:
        print(f"  {key:<7}: {summary[f'{key}_count']}")

    print("\nRecommended next steps:")
    for step in summary.get("next_steps", []):
        tag = f"[{step['severity']}]" if step.get("severity") != "info" else ""
        print(f"  {tag} {step['title']}: {step['description']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit project-aware runtime readiness.")
    parser.add_argument("--project", default="tech_ai_semiconductor")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--include-retired-checks",
        action="store_true",
        help="Show INFO findings for already-removed compatibility files and retired pipeline directory absence.",
    )
    args = parser.parse_args(argv)

    findings, summary = run_audit(args.project, include_retired_checks=args.include_retired_checks)
    if args.json:
        print(json.dumps({"summary": summary, "findings": [f.to_dict() for f in findings]}, ensure_ascii=False, indent=2))
    else:
        print_audit_report(findings, summary)
    return 1 if summary["BLOCKER_count"] or summary["HIGH_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
