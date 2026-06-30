"""Audit the project workflow stage contract."""

from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from investment_system.core.constants import WORKSPACE_ROOT
from investment_system.core.skill_module_loader import add_skill_src_paths


REQUIRED_STAGE_FIELDS = {
    "preferred_cli",
    "description",
    "writes",
    "requires_sector_id",
    "requires_manual_confirmation",
    "formal_output_write",
    "steps",
}


class DuplicateKeyError(ValueError):
    """Raised when a YAML mapping contains the same key twice."""


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects duplicate mapping keys."""


def _construct_unique_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    locations: dict[Any, yaml.Mark] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            first = locations[key]
            current = key_node.start_mark
            raise DuplicateKeyError(
                f"duplicate key {key!r} at line {current.line + 1}, column {current.column + 1}; "
                f"first occurrence at line {first.line + 1}, column {first.column + 1}"
            )
        locations[key] = key_node.start_mark
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


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
    try:
        return str(path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _workflow_stage_path(project_id: str) -> Path:
    return WORKSPACE_ROOT / "investment_system" / "research" / "projects" / project_id / "workflow_stages.yaml"


def _add(
    findings: list[AuditFinding],
    severity: str,
    code: str,
    message: str,
    file: str,
    *,
    category: str = "workflow_stage_contract",
    location: str = "",
    recommendation: str = "",
) -> None:
    findings.append(
        AuditFinding(
            file=file,
            category=category,
            severity=severity,
            code=code,
            message=message,
            location=location,
            recommendation=recommendation,
        )
    )


def _load_yaml_without_duplicate_keys(path: Path, findings: list[AuditFinding]) -> dict[str, Any] | None:
    rel_path = _rel(path)
    if not path.exists():
        _add(
            findings,
            "HIGH",
            "WORKFLOW_STAGES_MISSING",
            "workflow_stages.yaml is missing.",
            rel_path,
            recommendation="Create workflow_stages.yaml before running project-aware stages.",
        )
        return None

    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader) or {}
    except DuplicateKeyError as exc:
        _add(
            findings,
            "HIGH",
            "YAML_DUPLICATE_KEY",
            str(exc),
            rel_path,
            recommendation="Remove duplicate YAML keys; PyYAML keeps only one value in normal safe_load mode.",
        )
        return None
    except yaml.YAMLError as exc:
        _add(
            findings,
            "HIGH",
            "YAML_PARSE_FAILED",
            f"workflow_stages.yaml could not be parsed: {exc}",
            rel_path,
            recommendation="Fix YAML syntax before validating stage policy.",
        )
        return None

    if not isinstance(data, dict):
        _add(
            findings,
            "HIGH",
            "YAML_ROOT_NOT_MAPPING",
            "workflow_stages.yaml root must be a mapping.",
            rel_path,
            recommendation="Use mapping keys such as stage_order, warning_only_rules, global_forbidden_outputs, and stages.",
        )
        return None

    _add(
        findings,
        "INFO",
        "YAML_KEYS_UNIQUE",
        "workflow_stages.yaml parsed with no duplicate mapping keys.",
        rel_path,
    )
    return data


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


def _split_command(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=False)
    except ValueError:
        return command.split()


def _extract_skill_cli_paths(command: str) -> list[str]:
    paths: list[str] = []
    for token in _split_command(command):
        normalized = token.strip("\"'").replace("\\", "/")
        if ".codex/skills/" in normalized and normalized.endswith("/scripts/cli.py"):
            paths.append(normalized)
    return paths


def _resolve_cli_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return WORKSPACE_ROOT / raw_path


def _load_supported_stages() -> tuple[list[str], str]:
    try:
        add_skill_src_paths()
        from sector_research_orchestrator.stage_runner import SUPPORTED_STAGES
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)
    return list(SUPPORTED_STAGES), ""


def _check_schema_root(data: dict[str, Any], findings: list[AuditFinding], file: str) -> None:
    routing = data.get("skill_cli_routing", {}) or {}
    if not isinstance(routing, dict):
        _add(
            findings,
            "HIGH",
            "SKILL_CLI_ROUTING_INVALID",
            "skill_cli_routing must be a mapping.",
            file,
            location="skill_cli_routing",
        )
    elif routing.get("preferred_interface") != "skill_cli":
        _add(
            findings,
            "HIGH",
            "SKILL_CLI_ROUTING_INTERFACE_INVALID",
            "skill_cli_routing.preferred_interface must be skill_cli.",
            file,
            location="skill_cli_routing.preferred_interface",
        )
    if isinstance(routing, dict) and "stages" in routing:
        _add(
            findings,
            "HIGH",
            "DUPLICATE_STAGE_ROUTE_MAP",
            "skill_cli_routing.stages must not duplicate the canonical stages map.",
            file,
            recommendation="Keep preferred_cli inside each stages.<stage_name> mapping.",
        )

    for key in ["stage_order", "warning_only_rules", "global_forbidden_outputs", "stages"]:
        if key not in data:
            _add(
                findings,
                "HIGH",
                "WORKFLOW_SCHEMA_KEY_MISSING",
                f"workflow_stages.yaml is missing top-level key: {key}",
                file,
                location=key,
                recommendation="Keep stage_order, warning_only_rules, global_forbidden_outputs, and stages in the canonical schema.",
            )


def _check_stage_order(data: dict[str, Any], findings: list[AuditFinding], file: str) -> tuple[list[str], dict[str, Any]]:
    stage_order = data.get("stage_order", [])
    stages = data.get("stages", {})

    if not isinstance(stage_order, list) or not all(isinstance(item, str) and item for item in stage_order):
        _add(
            findings,
            "HIGH",
            "STAGE_ORDER_INVALID",
            "stage_order must be a non-empty list of stage names.",
            file,
            location="stage_order",
        )
        stage_order = []

    if not isinstance(stages, dict) or not stages:
        _add(
            findings,
            "HIGH",
            "STAGES_INVALID",
            "stages must be a non-empty mapping.",
            file,
            location="stages",
        )
        stages = {}

    stage_keys = list(stages.keys())
    if list(stage_order) != stage_keys:
        missing_from_stages = [stage for stage in stage_order if stage not in stages]
        missing_from_order = [stage for stage in stage_keys if stage not in stage_order]
        _add(
            findings,
            "HIGH",
            "STAGE_ORDER_MISMATCH",
            (
                "stage_order must match stages.keys() exactly and in order; "
                f"missing_from_stages={missing_from_stages}, missing_from_order={missing_from_order}"
            ),
            file,
            location="stage_order",
            recommendation="Reorder stages or update stage_order so both sequences are identical.",
        )
    else:
        _add(
            findings,
            "INFO",
            "STAGE_ORDER_OK",
            "stage_order matches stages.keys() exactly.",
            file,
            location="stage_order",
        )

    return list(stage_order), stages


def _check_stage_definitions(stages: dict[str, Any], data: dict[str, Any], findings: list[AuditFinding], file: str) -> None:
    warning_rules = data.get("warning_only_rules", {}) or {}
    global_forbidden_outputs = data.get("global_forbidden_outputs", []) or []
    if not isinstance(warning_rules, dict):
        _add(findings, "HIGH", "WARNING_ONLY_RULES_INVALID", "warning_only_rules must be a mapping.", file)
        warning_rules = {}
    if not isinstance(global_forbidden_outputs, list):
        _add(findings, "HIGH", "GLOBAL_FORBIDDEN_OUTPUTS_INVALID", "global_forbidden_outputs must be a list.", file)

    for stage_name, stage in stages.items():
        location = f"stages.{stage_name}"
        if not isinstance(stage, dict):
            _add(findings, "HIGH", "STAGE_DEFINITION_INVALID", f"{stage_name} must be a mapping.", file, location=location)
            continue

        missing = sorted(REQUIRED_STAGE_FIELDS - set(stage.keys()))
        if missing:
            _add(
                findings,
                "HIGH",
                "STAGE_REQUIRED_FIELDS_MISSING",
                f"{stage_name} is missing required field(s): {missing}",
                file,
                location=location,
            )

        writes = stage.get("writes", {})
        if not isinstance(writes, dict):
            _add(findings, "HIGH", "STAGE_WRITES_INVALID", f"{stage_name}.writes must be a mapping.", file, location=f"{location}.writes")
        else:
            for write_key in ["allowed", "forbidden"]:
                if not isinstance(writes.get(write_key), list):
                    _add(
                        findings,
                        "HIGH",
                        "STAGE_WRITES_KEY_INVALID",
                        f"{stage_name}.writes.{write_key} must be a list.",
                        file,
                        location=f"{location}.writes.{write_key}",
                    )

        commands = _command_strings(stage.get("preferred_cli"))
        if not commands:
            _add(
                findings,
                "HIGH",
                "PREFERRED_CLI_MISSING",
                f"{stage_name} has no preferred_cli command.",
                file,
                location=f"{location}.preferred_cli",
            )
        for command in commands:
            cli_paths = _extract_skill_cli_paths(command)
            if not cli_paths:
                _add(
                    findings,
                    "HIGH",
                    "PREFERRED_CLI_NOT_SKILL_CLI",
                    f"{stage_name} preferred_cli does not point to a skill scripts/cli.py file: {command}",
                    file,
                    location=f"{location}.preferred_cli",
                )
                continue
            for raw_path in cli_paths:
                cli_path = _resolve_cli_path(raw_path)
                if not cli_path.exists():
                    _add(
                        findings,
                        "HIGH",
                        "PREFERRED_CLI_FILE_MISSING",
                        f"{stage_name} preferred_cli file does not exist: {raw_path}",
                        file,
                        location=f"{location}.preferred_cli",
                        recommendation="Fix the skill CLI path or create the referenced CLI file.",
                    )

        if stage.get("formal_output_write") is True and stage.get("requires_manual_confirmation") is not True:
            _add(
                findings,
                "HIGH",
                "FORMAL_WRITE_WITHOUT_CONFIRMATION",
                f"{stage_name} sets formal_output_write=true without requires_manual_confirmation=true.",
                file,
                location=location,
            )

        for rule_name in stage.get("warning_only_rules", []) or []:
            if rule_name not in warning_rules:
                _add(
                    findings,
                    "HIGH",
                    "UNKNOWN_WARNING_ONLY_RULE",
                    f"{stage_name} references unknown warning_only_rules entry: {rule_name}",
                    file,
                    location=f"{location}.warning_only_rules",
                )


def _check_publish_sector_card_only(stages: dict[str, Any], findings: list[AuditFinding], file: str) -> None:
    stage = stages.get("publish_sector_card_only")
    if not isinstance(stage, dict):
        _add(
            findings,
            "HIGH",
            "PUBLISH_SECTOR_CARD_ONLY_STAGE_MISSING",
            "publish_sector_card_only stage is missing or invalid.",
            file,
            location="stages.publish_sector_card_only",
        )
        return

    problems: list[str] = []
    if stage.get("publish_scope") != "sector_card_only":
        problems.append("publish_scope must be sector_card_only")
    if stage.get("no_overwrite_required") is not True:
        problems.append("no_overwrite_required must be true")
    if problems:
        _add(
            findings,
            "HIGH",
            "PUBLISH_SECTOR_CARD_ONLY_CONTRACT_FAILED",
            f"publish_sector_card_only contract issue(s): {problems}",
            file,
            location="stages.publish_sector_card_only",
        )
    else:
        _add(
            findings,
            "INFO",
            "PUBLISH_SECTOR_CARD_ONLY_OK",
            "publish_sector_card_only is sector-card-only and requires no-overwrite.",
            file,
            location="stages.publish_sector_card_only",
        )


def _check_stage_runner_alignment(stage_order: list[str], findings: list[AuditFinding], file: str) -> None:
    supported_stages, error = _load_supported_stages()
    if error:
        _add(
            findings,
            "HIGH",
            "SUPPORTED_STAGES_IMPORT_FAILED",
            f"Could not import stage_runner.SUPPORTED_STAGES: {error}",
            ".codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/stage_runner.py",
        )
        return

    if supported_stages != stage_order:
        _add(
            findings,
            "HIGH",
            "SUPPORTED_STAGES_MISMATCH",
            f"stage_runner.SUPPORTED_STAGES must match YAML stage_order; supported={supported_stages}, stage_order={stage_order}",
            ".codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/stage_runner.py",
            recommendation="Update SUPPORTED_STAGES or workflow_stages.yaml so the sequences are identical.",
        )
    else:
        _add(
            findings,
            "INFO",
            "SUPPORTED_STAGES_OK",
            "stage_runner.SUPPORTED_STAGES matches YAML stage_order.",
            ".codex/skills/sector-research-orchestrator/src/sector_research_orchestrator/stage_runner.py",
        )


def _counts(findings: list[AuditFinding]) -> dict[str, int]:
    return {
        severity: sum(1 for finding in findings if finding.severity == severity)
        for severity in ["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]
    }


def _build_next_steps(counts: dict[str, int]) -> list[dict[str, str]]:
    if counts["BLOCKER"] or counts["HIGH"]:
        return [
            {
                "severity": "HIGH",
                "title": "Fix workflow stage contract",
                "description": "Repair duplicate YAML keys, stage ordering, CLI routes, publish safeguards, or runner alignment.",
            }
        ]
    return [
        {
            "severity": "info",
            "title": "Workflow stage contract is clean",
            "description": "No blocking workflow stage contract issues found.",
        }
    ]


def run_audit(project_id: str) -> tuple[list[AuditFinding], dict[str, Any]]:
    findings: list[AuditFinding] = []
    path = _workflow_stage_path(project_id)
    file = _rel(path)

    data = _load_yaml_without_duplicate_keys(path, findings)
    if data is not None:
        _check_schema_root(data, findings, file)
        stage_order, stages = _check_stage_order(data, findings, file)
        _check_stage_definitions(stages, data, findings, file)
        _check_publish_sector_card_only(stages, findings, file)
        _check_stage_runner_alignment(stage_order, findings, file)

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
    print(f" Workflow Stage Contract - {summary['project_id']}")
    print(f" Total findings: {summary['total_findings']}")
    print("=" * 70)

    for severity in ["BLOCKER", "HIGH", "MEDIUM", "LOW", "INFO"]:
        rows = [finding for finding in findings if finding.severity == severity]
        if not rows:
            continue
        print(f"\n[{severity}] ({len(rows)})")
        by_file: dict[str, list[AuditFinding]] = {}
        for finding in rows:
            by_file.setdefault(finding.file or "(project)", []).append(finding)
        for file, file_rows in by_file.items():
            print(f"  {file}:")
            for finding in file_rows:
                suffix = f" ({finding.location})" if finding.location else ""
                print(f"    [{finding.code}]{suffix} {finding.message}")
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
    parser = argparse.ArgumentParser(description="Audit the project workflow stage contract.")
    parser.add_argument("--project", default="tech_ai_semiconductor")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    findings, summary = run_audit(args.project)
    if args.json:
        print(json.dumps({"summary": summary, "findings": [finding.to_dict() for finding in findings]}, ensure_ascii=False, indent=2))
    else:
        print_audit_report(findings, summary)
    return 1 if summary["BLOCKER_count"] or summary["HIGH_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
