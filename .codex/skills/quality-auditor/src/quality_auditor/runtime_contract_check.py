"""Project-aware runtime contract check for workflow scope checks."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from investment_system.core.constants import WORKSPACE_ROOT
from investment_system.core.output_contracts import get_output_contract, list_output_types
from investment_system.core.project_loader import load_project
from investment_system.core.sector_runtime import resolve_sector_context


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


def _add(
    findings: list[AuditFinding],
    severity: str,
    code: str,
    message: str,
    file: str = "",
    category: str = "runtime_contract",
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


def _command_strings(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        if not raw:
            return []
        if all(not isinstance(item, (list, dict)) for item in raw):
            return [" ".join(str(part) for part in raw)]
        return [" ".join(str(part) for part in item) if isinstance(item, list) else str(item) for item in raw]
    return [str(raw)]


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
    routing = data.get("skill_cli_routing", {}) or {}
    stage_map = routing.get("stages", {}) or {}
    stage_defs = data.get("stages", {}) or {}

    problems: list[str] = []
    if routing.get("preferred_interface") != "skill_cli":
        problems.append("skill_cli_routing.preferred_interface must be skill_cli")
    if not stage_map:
        problems.append("skill_cli_routing.stages is empty")

    for stage_name, stage in stage_map.items():
        commands = _command_strings(stage.get("preferred_cli") if isinstance(stage, dict) else stage)
        if not commands:
            problems.append(f"{stage_name} has no preferred_cli")
            continue
        for command in commands:
            normalized = command.replace("\\", "/")
            if ".codex/skills/" not in normalized or "/scripts/cli.py" not in normalized:
                problems.append(f"{stage_name} does not route through a skill CLI: {command}")

    scope_check = stage_defs.get("scope_check", {}) if isinstance(stage_defs, dict) else {}
    if scope_check.get("requires_sector_id") is not False:
        problems.append("scope_check must not require --sector-id")
    if "runtime_contract_check" not in (scope_check.get("steps", []) or []):
        problems.append("scope_check must include runtime_contract_check")

    if problems:
        _add(
            findings,
            "HIGH",
            "WORKFLOW_STAGE_CONTRACT_FAILED",
            f"workflow stage contract issue(s): {problems}",
            _rel(path),
            category="workflow",
            recommendation="Keep workflow_stages.yaml aligned with project-aware skill CLI entry points.",
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


def _counts(findings: list[AuditFinding]) -> dict[str, int]:
    return {
        severity: sum(1 for f in findings if f.severity == severity)
        for severity in ["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]
    }


def _build_next_steps(counts: dict[str, int]) -> list[dict[str, str]]:
    if counts["BLOCKER"] or counts["HIGH"]:
        return [
            {
                "severity": "HIGH",
                "title": "Fix runtime contract failures",
                "description": "Repair the failing project loader, sector context, output contract, or workflow-stage route.",
            }
        ]
    return [
        {
            "severity": "info",
            "title": "Runtime contract is clean",
            "description": "No active runtime-contract issues found.",
        }
    ]


def run_audit(project_id: str) -> tuple[list[AuditFinding], dict[str, Any]]:
    findings: list[AuditFinding] = []
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
        "next_steps": _build_next_steps(counts),
    }
    return findings, summary


def print_audit_report(findings: list[AuditFinding], summary: dict[str, Any]) -> None:
    print("=" * 70)
    print(f" Runtime Contract Check - {summary['project_id']}")
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
    parser = argparse.ArgumentParser(description="Check the active project runtime contract.")
    parser.add_argument("--project", default="tech_ai_semiconductor")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    findings, summary = run_audit(args.project)
    if args.json:
        print(json.dumps({"summary": summary, "findings": [f.to_dict() for f in findings]}, ensure_ascii=False, indent=2))
    else:
        print_audit_report(findings, summary)
    return 1 if summary["BLOCKER_count"] or summary["HIGH_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
