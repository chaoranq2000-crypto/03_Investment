"""Run one standardized sector-research workflow stage.

This runner keeps the current workflow steps intact while making the command
sequence explicit and repeatable. It delegates business checks to the existing
gate scripts instead of duplicating their logic.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from investment_system.core.constants import WORKSPACE_ROOT
from investment_system.core.skill_module_loader import skill_subprocess_env


SECTOR_CARD_ONLY = "sector_card_only"
ALL_OUTPUTS_REHEARSAL = "all_outputs_rehearsal"
SUPPORTED_STAGES = [
    "scope_check",
    "evidence_collect",
    "evidence_draft",
    "evidence_register",
    "evidence_gate",
    "generate_candidate",
    "candidate_gate",
    "publish_gate",
    "publish_sector_card_only",
    "post_publish_check",
]


@dataclass
class StepResult:
    name: str
    command: list[str]
    exit_code: int
    blocking: bool
    output: str


@dataclass
class StagePolicy:
    stage: str
    configured: bool
    description: str = ""
    allowed_writes: list[str] | None = None
    forbidden_writes: list[str] | None = None
    warning_only_rules: list[dict[str, object]] | None = None
    requires_sector_id: bool = True
    requires_manual_confirmation: bool = False
    formal_output_write: bool = False


def _workflow_stage_path(project: str) -> Path:
    from investment_system.core.project_loader import PROJECTS_ROOT

    return PROJECTS_ROOT / project / "workflow_stages.yaml"


def _load_stage_policy(project: str, stage: str) -> StagePolicy:
    path = _workflow_stage_path(project)
    if not path.exists():
        return StagePolicy(stage=stage, configured=False)

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    stages = data.get("stages", {}) or {}
    stage_data = stages.get(stage, {}) or {}
    global_rules = data.get("warning_only_rules", {}) or {}
    rule_names = stage_data.get("warning_only_rules", []) or []
    warning_rules = [
        global_rules[name]
        for name in rule_names
        if name in global_rules
    ]
    writes = stage_data.get("writes", {}) or {}
    return StagePolicy(
        stage=stage,
        configured=bool(stage_data),
        description=str(stage_data.get("description", "") or ""),
        allowed_writes=list(writes.get("allowed", []) or []),
        forbidden_writes=list(writes.get("forbidden", []) or []),
        warning_only_rules=warning_rules,
        requires_sector_id=bool(stage_data.get("requires_sector_id", True)),
        requires_manual_confirmation=bool(stage_data.get("requires_manual_confirmation", False)),
        formal_output_write=bool(stage_data.get("formal_output_write", False)),
    )


def _run_module(module: str, *args: str) -> StepResult:
    command = [sys.executable, "-m", module, *args]
    proc = subprocess.run(
        command,
        cwd=str(WORKSPACE_ROOT),
        env=skill_subprocess_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return StepResult(
        name=module.rsplit(".", 1)[-1],
        command=command,
        exit_code=proc.returncode,
        blocking=proc.returncode != 0,
        output=proc.stdout or "",
    )


def _print_step(result: StepResult) -> None:
    print("=" * 72)
    print(f"step: {result.name}")
    print(f"exit_code: {result.exit_code}")
    print(f"blocking: {result.blocking}")
    print("command:", " ".join(result.command))
    if result.output.strip():
        print("-" * 72)
        print(result.output.rstrip())


def _print_policy(policy: StagePolicy) -> None:
    print("=" * 72)
    print(f"stage_policy_configured: {policy.configured}")
    print(f"stage_description: {policy.description or '(none)'}")
    print(f"requires_sector_id: {policy.requires_sector_id}")
    print(f"requires_manual_confirmation: {policy.requires_manual_confirmation}")
    print(f"formal_output_write: {policy.formal_output_write}")
    print("allowed_writes:")
    for item in policy.allowed_writes or []:
        print(f"  - {item}")
    print("forbidden_writes:")
    for item in policy.forbidden_writes or []:
        print(f"  - {item}")


def _coverage_ok_for_sector(output: str, sector_id: str) -> bool:
    if not sector_id:
        return False
    pattern = re.compile(rf"\]\s+{re.escape(sector_id)}:\s+coverage OK\b")
    return bool(pattern.search(output))


def _load_project_warning_only(output: str) -> bool:
    return '"errors": []' in output and '"_load_status": "warning"' in output


def _release_manifest_from_output(output: str) -> str | None:
    for line in output.splitlines():
        if line.startswith("release_manifest:"):
            return line.split(":", 1)[1].strip()
    return None


def _mark_coverage_warning_only(result: StepResult, sector_id: str) -> StepResult:
    if result.exit_code in {1, 3} and _coverage_ok_for_sector(result.output, sector_id):
        result.blocking = False
    return result


def _mark_load_warning_only(result: StepResult) -> StepResult:
    if result.exit_code != 0 and _load_project_warning_only(result.output):
        result.blocking = False
    return result


def _detector_passes(detector: str, result: StepResult, sector_id: str) -> bool:
    if detector == "load_project_warning_only":
        return _load_project_warning_only(result.output)
    if detector == "target_coverage_ok":
        return _coverage_ok_for_sector(result.output, sector_id)
    return False


def _apply_stage_policy(results: list[StepResult], policy: StagePolicy, sector_id: str) -> None:
    for result in results:
        for rule in policy.warning_only_rules or []:
            if str(rule.get("step", "")) != result.name:
                continue
            exit_codes = set(rule.get("exit_codes", []) or [])
            if result.exit_code not in exit_codes:
                continue
            detector = str(rule.get("detector", "") or "")
            if _detector_passes(detector, result, sector_id):
                result.blocking = False


def _run_scope_check(project: str) -> list[StepResult]:
    return [
        _mark_load_warning_only(_run_module("investment_system.core.project_loader", "--project", project, "--json")),
        _run_module("quality_auditor.runtime_contract_check", "--project", project),
        _run_module("quality_auditor.validate_outputs", "--project", project),
    ]


def _run_evidence_gate(project: str, sector_id: str) -> list[StepResult]:
    results = [
        _run_module("quality_auditor.evidence_bindings", "--project", project),
        _run_module("quality_auditor.evidence_schema", "--project", project),
        _mark_coverage_warning_only(
            _run_module("quality_auditor.evidence_coverage", "--project", project),
            sector_id,
        ),
    ]
    return results


def _run_evidence_register(
    project: str,
    sector_id: str,
    evidence_path: str | None,
    evidence_file_id: str | None,
    evidence_status: str,
    evidence_action: str,
    registration_notes: str,
    allow_missing: bool,
    apply_registration: bool,
) -> list[StepResult]:
    if not evidence_path:
        return [
            StepResult(
                name="register_evidence_file",
                command=[],
                exit_code=2,
                blocking=True,
                output="ERROR: --evidence-path is required for evidence_register.",
            )
        ]

    args = [
        "--project",
        project,
        "--sector-id",
        sector_id,
        "--path",
        evidence_path,
        "--status",
        evidence_status,
        "--action",
        evidence_action,
    ]
    if evidence_file_id:
        args.extend(["--evidence-file-id", evidence_file_id])
    if registration_notes:
        args.extend(["--notes", registration_notes])
    if allow_missing:
        args.append("--allow-missing")
    if not apply_registration:
        args.append("--dry-run")
    return [_run_module("evidence_miner.register", *args)]


def _run_evidence_collect(args: argparse.Namespace) -> list[StepResult]:
    if not args.local_dir and not args.local_file:
        return [
            StepResult(
                name="collect_official_evidence",
                command=[],
                exit_code=2,
                blocking=True,
                output="ERROR: provide at least one --local-dir or --local-file for evidence_collect.",
            )
        ]
    command_args = [
        "--project",
        args.project,
        "--sector-id",
        args.sector_id,
        "--extensions",
        args.extensions,
        "--source-type",
        args.source_type,
        "--evidence-level",
        args.evidence_level,
        "--publisher",
        args.publisher,
        "--source-date",
        args.source_date,
        "--source-set",
        args.source_set,
        "--run-date",
        args.run_date,
    ]
    for path in args.local_dir:
        command_args.extend(["--local-dir", path])
    for path in args.local_file:
        command_args.extend(["--local-file", path])
    if args.metadata_json:
        command_args.extend(["--metadata-json", args.metadata_json])
    if args.manifest_path:
        command_args.extend(["--manifest-path", args.manifest_path])
    if args.extract_pdf_text:
        command_args.append("--extract-pdf-text")
    if args.write_manifest:
        command_args.append("--write-manifest")
    return [_run_module("evidence_miner.source_manifest", *command_args)]


def _run_evidence_draft(args: argparse.Namespace) -> list[StepResult]:
    if not args.source_manifest:
        return [
            StepResult(
                name="build_evidence_skeleton",
                command=[],
                exit_code=2,
                blocking=True,
                output="ERROR: provide at least one --source-manifest for evidence_draft.",
            )
        ]
    command_args = [
        "--project",
        args.project,
        "--sector-id",
        args.sector_id,
        "--run-date",
        args.run_date,
    ]
    for path in args.source_manifest:
        command_args.extend(["--source-manifest", path])
    if args.evidence_file_id:
        command_args.extend(["--evidence-file-id", args.evidence_file_id])
    if args.output_path:
        command_args.extend(["--output-path", args.output_path])
    if args.write_draft:
        command_args.append("--write-draft")
    return [_run_module("evidence_miner.draft_skeleton", *command_args)]


def _run_generate_candidate(project: str, sector_id: str, run_id: str | None) -> list[StepResult]:
    args = ["--project", project, "--sector-id", sector_id, "--candidate-only"]
    if run_id:
        args.extend(["--run-id", run_id])
    return [_run_module("research_writer.candidate_outputs", *args)]


def _run_candidate_gate(project: str, sector_id: str) -> list[StepResult]:
    return [_run_module("quality_auditor.candidate_outputs", "--project", project, "--sector-id", sector_id)]


def _run_publish_gate(project: str, sector_id: str, publish_scope: str) -> list[StepResult]:
    prepare = _run_module(
        "sector_research_orchestrator.publish",
        "--project",
        project,
        "--sector-id",
        sector_id,
        "--publish-scope",
        publish_scope,
        "--dry-run",
        "--no-overwrite",
    )
    if prepare.exit_code != 0:
        return [prepare]

    args = ["--project", project, "--sector-id", sector_id, "--publish-scope", publish_scope]
    manifest = _release_manifest_from_output(prepare.output)
    if manifest:
        args.extend(["--release-manifest", manifest])
    readiness = _run_module("quality_auditor.publish_readiness", *args)
    return [prepare, readiness]


def _run_publish_sector_card_only(project: str, sector_id: str, confirm_publish: bool) -> list[StepResult]:
    if not confirm_publish:
        return [
            StepResult(
                name="publish_sector_card_only",
                command=[],
                exit_code=2,
                blocking=True,
                output="ERROR: --confirm-publish is required for publish_sector_card_only.",
            )
        ]
    return [
        _run_module(
            "sector_research_orchestrator.publish",
            "--project",
            project,
            "--sector-id",
            sector_id,
            "--publish-scope",
            SECTOR_CARD_ONLY,
            "--confirm-publish",
            "--no-overwrite",
        )
    ]


def _run_post_publish_check(project: str, sector_id: str) -> list[StepResult]:
    return [
        _run_module("quality_auditor.publish_result", "--project", project, "--sector-id", sector_id),
        _run_module("quality_auditor.validate_outputs", "--project", project),
        _run_module("quality_auditor.runtime_contract_check", "--project", project),
    ]


def _run_stage(args: argparse.Namespace) -> list[StepResult]:
    if args.stage == "scope_check":
        return _run_scope_check(args.project)
    if args.stage == "evidence_collect":
        return _run_evidence_collect(args)
    if args.stage == "evidence_draft":
        return _run_evidence_draft(args)
    if args.stage == "evidence_register":
        return _run_evidence_register(
            project=args.project,
            sector_id=args.sector_id,
            evidence_path=args.evidence_path,
            evidence_file_id=args.evidence_file_id,
            evidence_status=args.evidence_status,
            evidence_action=args.evidence_action,
            registration_notes=args.registration_notes,
            allow_missing=args.allow_missing_evidence,
            apply_registration=args.apply_registration,
        )
    if args.stage == "evidence_gate":
        return _run_evidence_gate(args.project, args.sector_id)
    if args.stage == "generate_candidate":
        return _run_generate_candidate(args.project, args.sector_id, args.run_id)
    if args.stage == "candidate_gate":
        return _run_candidate_gate(args.project, args.sector_id)
    if args.stage == "publish_gate":
        return _run_publish_gate(args.project, args.sector_id, args.publish_scope)
    if args.stage == "publish_sector_card_only":
        return _run_publish_sector_card_only(args.project, args.sector_id, args.confirm_publish)
    if args.stage == "post_publish_check":
        return _run_post_publish_check(args.project, args.sector_id)
    raise ValueError(f"unsupported stage: {args.stage}")


def _write_summary(project: str, sector_id: str, stage: str, results: list[StepResult], policy: StagePolicy) -> Path:
    from investment_system.core.project_loader import PROJECTS_ROOT

    audit_dir = PROJECTS_ROOT / project / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    sector_label = sector_id or "project"
    path = audit_dir / f"stage_run_{stage}_{sector_label}.md"
    blocking_count = sum(1 for row in results if row.blocking)
    lines = [
        f"# Stage Run - {stage}",
        "",
        f"- project_id: `{project}`",
        f"- sector_id: `{sector_id or '(not required)'}`",
        f"- stage: `{stage}`",
        f"- stage_policy_configured: {policy.configured}",
        f"- formal_output_write: {policy.formal_output_write}",
        f"- requires_manual_confirmation: {policy.requires_manual_confirmation}",
        f"- step_count: {len(results)}",
        f"- blocking_count: {blocking_count}",
        "",
        "## Steps",
    ]
    for row in results:
        lines.extend(
            [
                "",
                f"### {row.name}",
                f"- exit_code: {row.exit_code}",
                f"- blocking: {row.blocking}",
                f"- command: `{' '.join(row.command)}`",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Run one standardized sector-research workflow stage.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", default="")
    parser.add_argument(
        "--stage",
        required=True,
        choices=[
            *SUPPORTED_STAGES,
        ],
    )
    parser.add_argument("--publish-scope", default=SECTOR_CARD_ONLY, choices=[SECTOR_CARD_ONLY, ALL_OUTPUTS_REHEARSAL])
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--evidence-path", default=None)
    parser.add_argument("--evidence-file-id", default=None)
    parser.add_argument("--evidence-status", default="schema_normalized")
    parser.add_argument("--evidence-action", default="index_only")
    parser.add_argument("--registration-notes", default="")
    parser.add_argument("--allow-missing-evidence", action="store_true")
    parser.add_argument("--apply-registration", action="store_true")
    parser.add_argument("--local-dir", action="append", default=[])
    parser.add_argument("--local-file", action="append", default=[])
    parser.add_argument("--extensions", default=".pdf,.txt,.md,.json")
    parser.add_argument("--source-type", default="annual_report")
    parser.add_argument("--evidence-level", default="strong")
    parser.add_argument("--publisher", default="")
    parser.add_argument("--source-date", default="")
    parser.add_argument("--source-set", default="official_evidence")
    parser.add_argument("--metadata-json", default=None)
    parser.add_argument("--manifest-path", default=None)
    parser.add_argument("--source-manifest", action="append", default=[])
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--run-date", default=None)
    parser.add_argument("--extract-pdf-text", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--write-draft", action="store_true")
    parser.add_argument("--confirm-publish", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args(argv)
    if args.run_date is None:
        from datetime import date

        args.run_date = date.today().isoformat()

    try:
        policy = _load_stage_policy(args.project, args.stage)
        requires_sector_id = policy.requires_sector_id if policy.configured else args.stage != "scope_check"
        if requires_sector_id and not args.sector_id:
            print(f"ERROR: --sector-id is required for stage {args.stage}.")
            return 1
        results = _run_stage(args)
        _apply_stage_policy(results, policy, args.sector_id)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    _print_policy(policy)
    for result in results:
        _print_step(result)

    blocking_count = sum(1 for row in results if row.blocking)
    if args.write_summary:
        path = _write_summary(args.project, args.sector_id, args.stage, results, policy)
        print("=" * 72)
        print(f"stage_summary: {path}")
    print("=" * 72)
    print(f"stage: {args.stage}")
    print(f"step_count: {len(results)}")
    print(f"blocking_count: {blocking_count}")
    return 1 if blocking_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
