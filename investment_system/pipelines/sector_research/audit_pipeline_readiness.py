"""
Pipeline Readiness Audit — Phase 1E-c-a.

Static audit of legacy pipeline files against the new project-aware schema.
Does NOT modify any files. Outputs findings grouped by severity.

Phase 1E-c-a changes:
  - KNOWN_COMPANIES in project-aware scope → HIGH (blocked by design)
  - KNOWN_COMPANIES in legacy-only scope → LOW (acceptable)
  - scan_hardcoded_strings distinguishes project-aware vs legacy blocks
  - _is_in_project_aware_block() helper added
  - _build_next_steps updated for 1E-c-a readiness
  - BLOCKER target maintained: BLOCKER=0

Usage:
    python -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor
    python -m investment_system.pipelines.sector_research.audit_pipeline_readiness --project tech_ai_semiconductor --json

Exit codes:
    0  audit complete (findings are informational, not blocking)
    1  critical blockers found
    2  unexpected error during audit
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

def _resolve_workaround() -> Path:
    me_mod = sys.modules[__name__]
    spec = getattr(me_mod, "__spec__", None)
    if spec and spec.origin:
        return Path(spec.origin).resolve()
    return Path(__file__).resolve()

_AUDIT_PATH = _resolve_workaround()
WORKSPACE_ROOT = _AUDIT_PATH.parents[3]
PROJECTS_ROOT = WORKSPACE_ROOT / "investment_system" / "research" / "projects"


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


# Post-1E-c-a severities:
# THEME_REGISTRY_CSV / KNOWN_COMPANIES in LEGACY scope → LOW
# THEME_REGISTRY_CSV / KNOWN_COMPANIES in PROJECT-AWARE scope → HIGH (must not use)
# OUT_DIR/LOG_DIR/RAW_DIR globals → MEDIUM (in project-aware scope)
HARDCODED_PATH_PATTERNS = {
    "科技主线调研输出": "output root directory",
    "A股科技前两主线调研文件包": "legacy research package",
    "THEME_REGISTRY_CSV": "legacy-only after 1E-b: project-aware uses loader API (LOW)",
    "KNOWN_COMPANIES": "legacy-only after 1E-b: project-aware uses stock_universe.yaml (LOW)",
    "OUT_DIR = ROOT /": "legacy-only globals (MEDIUM in project-aware scope)",
    "LOG_DIR =": "legacy-only globals (MEDIUM in project-aware scope)",
    "RAW_DIR =": "legacy-only globals (MEDIUM in project-aware scope)",
}


def scan_project_aware_canonical(
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    if rel_path != "investment_system/pipelines/run_research.py":
        return

    if "class SectorContext" not in content:
        findings.append(AuditFinding(
            file=rel_path, category="canonical_sector_id", severity="HIGH",
            code="MISSING_SECTOR_CONTEXT",
            message="SectorContext dataclass not found. Project-aware mode needs canonical sector resolution.",
            recommendation="Add SectorContext dataclass and resolve_sector_context().",
        ))

    if "def resolve_sector_context" in content:
        if not re.search(r"get_sector|legacy_sector_map|_lp_get_sector", content):
            findings.append(AuditFinding(
                file=rel_path, category="canonical_sector_id", severity="HIGH",
                code="NO_LOADER_API_IN_RESOLVER",
                message="resolve_sector_context does not call loader API.",
                recommendation="Call get_sector() via load_project module.",
            ))

    if "elif args.project and args.batch:" in content:
        if "list_project_sectors_by_priority" not in content:
            findings.append(AuditFinding(
                file=rel_path, category="canonical_sector_id", severity="HIGH",
                code="BATCH_USES_LEGACY_POOL",
                message="Project-aware batch mode does not use list_project_sectors_by_priority().",
                recommendation="Use list_project_sectors_by_priority() + get_stocks_for_sector().",
            ))

    if "--dry-run-resolve" not in content:
        findings.append(AuditFinding(
            file=rel_path, category="canonical_sector_id", severity="MEDIUM",
            code="NO_DRY_RUN_RESOLVE",
            message="--dry-run-resolve flag not found.",
            recommendation="Add --dry-run-resolve CLI flag.",
        ))

    if "was_legacy_alias" not in content:
        findings.append(AuditFinding(
            file=rel_path, category="canonical_sector_id", severity="MEDIUM",
            code="NO_LEGACY_WARNING",
            message="No was_legacy_alias flag found.",
            recommendation="Print warning when input is resolved via legacy alias.",
        ))


def _is_in_legacy_only_block(line_idx: int, lines: list[str]) -> bool:
    """Check if current line is inside a legacy-only code block."""
    for j in range(line_idx - 1, -1, -1):
        stripped = lines[j].strip()
        if stripped.startswith("#"):
            continue
        if "not args.project" in lines[j] or "elif not args.project" in lines[j]:
            return True
        if stripped.startswith("def ") or stripped.startswith("class "):
            break
        if any(kw in lines[j] for kw in ("elif ", "else:", "if args.project")):
            break
    return False


def _is_in_project_aware_block(line_idx: int, lines: list[str]) -> bool:
    """Check if current line is inside a project-aware code block."""
    in_project_block = False
    brace_depth = 0
    for j in range(line_idx, -1, -1):
        stripped = lines[j].strip()
        if stripped.startswith("#"):
            continue
        if "if args.project" in lines[j] and "not" not in lines[j]:
            in_project_block = True
        if stripped.startswith("def ") or stripped.startswith("class "):
            break
        if "not args.project" in lines[j] or "elif not args.project" in lines[j]:
            break
    return in_project_block


def scan_subtheme_hardcoding(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    if rel_path != "investment_system/pipelines/run_research.py":
        for line in content.splitlines():
            if '"高速光模块"' in line or "'高速光模块'" in line:
                findings.append(AuditFinding(
                    file=rel_path, category="theme_hardcoding", severity="MEDIUM",
                    code="THEME_NAME_HARDCODED",
                    message="Found legacy theme name '高速光模块' hardcoded.",
                    location=rel_path,
                    recommendation="Keep as legacy collector only; project-aware pipeline should not call this path.",
                ))
            if '"光器件/FAU/精密光学"' in line or "'光器件/FAU/精密光学'" in line:
                findings.append(AuditFinding(
                    file=rel_path, category="theme_hardcoding", severity="MEDIUM",
                    code="THEME_NAME_HARDCODED",
                    message="Found legacy theme name '光器件/FAU/精密光学' hardcoded.",
                    location=rel_path,
                    recommendation="Keep as legacy collector only; project-aware pipeline should not call this path.",
                ))
        return

    lines = content.splitlines()
    for i, line in enumerate(lines):
        is_legacy = _is_in_legacy_only_block(i, lines)
        ctx_start = max(0, i - 20)
        ctx_end = min(len(lines), i + 5)
        ctx = "\n".join(lines[ctx_start:ctx_end])
        in_known_companies = "KNOWN_COMPANIES" in ctx or "load_theme_registry" in ctx
        in_module_doc = i < 25

        if '"高速光模块"' in line or "'高速光模块'" in line:
            severity = "LOW" if (is_legacy or in_known_companies or in_module_doc) else "HIGH"
            findings.append(AuditFinding(
                file=rel_path, category="theme_hardcoding", severity=severity,
                code="LEGACY_THEME_NAME_IN_RUN_RESEARCH",
                message=f"Found '高速光模块' ({'in legacy-only scope' if (is_legacy or in_module_doc) else 'in project-aware scope'}).",
                location=f"line {i + 1}",
                recommendation="In project-aware mode: use canonical sector_id via resolve_sector_context().",
            ))
        if '"光器件/FAU/精密光学"' in line or "'光器件/FAU/精密光学'" in line:
            severity = "LOW" if (is_legacy or in_known_companies or in_module_doc) else "HIGH"
            findings.append(AuditFinding(
                file=rel_path, category="theme_hardcoding", severity=severity,
                code="LEGACY_THEME_NAME_IN_RUN_RESEARCH",
                message=f"Found '光器件/FAU/精密光学' ({'in legacy-only scope' if (is_legacy or in_module_doc) else 'in project-aware scope'}).",
                location=f"line {i + 1}",
                recommendation="In project-aware mode: use canonical sector_id via resolve_sector_context().",
            ))


def scan_hardcoded_strings(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    lines = content.splitlines()
    for pattern, description in HARDCODED_PATH_PATTERNS.items():
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern not in line:
                continue

            if pattern in ("THEME_REGISTRY_CSV", "KNOWN_COMPANIES"):
                # Distinguish project-aware vs legacy usage
                in_project = _is_in_project_aware_block(i, lines)
                in_legacy = _is_in_legacy_only_block(i, lines)
                if in_project:
                    sev = "HIGH"  # project-aware mode must not use legacy stock pool
                    recommendation = (
                        f"'{pattern}' is project-aware active usage. "
                        "Use stock_universe.yaml via get_stocks_for_sector() instead."
                    )
                elif in_legacy:
                    sev = "LOW"   # legacy-only scope, acceptable
                    recommendation = f"'{pattern}' is legacy-only (OK in no --project mode)."
                else:
                    sev = "MEDIUM"  # outside clearly-labeled blocks
                    recommendation = f"'{pattern}' outside clear scope. Verify it is legacy-only."
                findings.append(AuditFinding(
                    file=rel_path, category="hardcoded_strings", severity=sev,
                    code="HARDCODED_STRING",
                    message=f"Found hardcoded string '{pattern}' ({description})",
                    location=f"line {i + 1}",
                    recommendation=recommendation,
                ))
            else:
                sev = "MEDIUM"
                findings.append(AuditFinding(
                    file=rel_path, category="hardcoded_strings", severity=sev,
                    code="HARDCODED_STRING",
                    message=f"Found hardcoded string '{pattern}' ({description})",
                    location=f"line {i + 1}",
                    recommendation=f"'{pattern}' is {description}. In project-aware mode, use loader API.",
                ))


def scan_field_mismatches(
    file_path: Path,
    content: str,
    rel_path: str,
    output_spec: dict[str, Any],
    findings: list[AuditFinding],
) -> None:
    schema_path = WORKSPACE_ROOT / "investment_system" / "research" / "schemas" / "output.schema.yaml"
    output_schema: dict[str, Any] = {}
    if schema_path.exists():
        with schema_path.open("r", encoding="utf-8") as f:
            output_schema = yaml.safe_load(f) or {}

    def contract_fields(output_type: str, fallback_key: str) -> set[str]:
        contract = (output_schema.get("output_types", {}) or {}).get(output_type, {})
        fields = set(contract.get("required_fields", []) or [])
        fields.update(contract.get("optional_fields", []) or [])
        fields.update(contract.get("legacy_display_fields", []) or [])
        if not fields:
            fields.update(f.get("field") for f in output_spec.get(fallback_key, []) if f.get("field"))
        return fields

    def extract_list_constant(name: str) -> list[str]:
        try:
            tree = ast.parse(content)
        except Exception:
            return []
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                return []
            return [str(item) for item in value if isinstance(item, str)]
        return []

    if "COMPANY_TABLE_FIELDS" in content:
        current_fields = extract_list_constant("COMPANY_TABLE_FIELDS")
        if current_fields:
            expected_fields = contract_fields("company_table", "company_table_fields")
            extra_in_current = [f for f in current_fields if f not in expected_fields]
            for old in ("main_theme", "sub_theme"):
                if old in current_fields:
                    new = "parent_chain" if old == "main_theme" else "sector_id"
                    findings.append(AuditFinding(
                        file=rel_path, category="field_schema", severity="HIGH",
                        code="LEGACY_FIELD_NAME",
                        message=f"COMPANY_TABLE_FIELDS contains legacy field '{old}' (should be {new})",
                        location="COMPANY_TABLE_FIELDS definition",
                        recommendation="Align with output_spec.company_table_fields",
                    ))
            if extra_in_current:
                findings.append(AuditFinding(
                    file=rel_path, category="field_schema", severity="MEDIUM",
                    code="EXTRA_FIELDS",
                    message=f"COMPANY_TABLE_FIELDS contains fields not in output_spec: {extra_in_current}",
                    location="COMPANY_TABLE_FIELDS definition",
                    recommendation="Remove or align with output_spec.",
                ))

    if "COMPARISON_FIELDS" in content:
        current_fields = extract_list_constant("COMPARISON_FIELDS")
        if current_fields:
            expected = contract_fields("sector_comparison_table", "comparison_table_fields")
            extra = [f for f in current_fields if f not in expected]
            if extra:
                findings.append(AuditFinding(
                    file=rel_path, category="field_schema", severity="MEDIUM",
                    code="EXTRA_COMPARISON_FIELDS",
                    message=f"COMPARISON_FIELDS has extra fields: {extra}",
                    location="COMPARISON_FIELDS definition",
                    recommendation="Align with output_spec.comparison_table_fields",
                ))

    if "SOURCE_FIELDS" in content:
        current_fields = extract_list_constant("SOURCE_FIELDS")
        if current_fields:
            expected = contract_fields("source_index", "source_index_fields")
            extra = [f for f in current_fields if f not in expected]
            if extra:
                findings.append(AuditFinding(
                    file=rel_path, category="field_schema", severity="MEDIUM",
                    code="EXTRA_SOURCE_FIELDS",
                    message=f"SOURCE_FIELDS has extra fields: {extra}",
                    location="SOURCE_FIELDS definition",
                    recommendation="Align with output_spec.source_index_fields",
                ))


def scan_card_path_generation(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    """Detect hardcoded card path prefixes that bypass output_spec.

    After 1E-b fixes:
      - "01_" in directory path constants (THEME_REGISTRY_CSV etc.) → exempt
      - "01_" in legacy-only else branch (_legacy_prefix) → exempt
      - "01_" in project-aware path construction → BLOCKER
    """
    lines = content.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if not (re.search(r'["\']01_', line) or re.search(r'["\']02_', line)):
            continue

        # Skip directory path constants (e.g. THEME_REGISTRY_CSV = ROOT / "A股科技前两主线调研文件包" / "01_调研板块细分方向列表")
        if "ROOT /" in line or "_DIR" in stripped:
            continue

        # Skip legacy-only branch (contains OUT_DIR and _legacy_prefix = "01_")
        if "_legacy_prefix" in line:
            continue

        # Skip if already referencing output_spec
        if "output_spec" in line or "sector_card_path_template" in line:
            continue

        findings.append(AuditFinding(
            file=rel_path, category="path_generation", severity="BLOCKER",
            code="HARDCODED_CARD_PATH",
            message="Card path uses hardcoded 01_/02_ prefix that bypasses output_spec.",
            location=f"line {i + 1}",
            recommendation="Use resolve_sector_card_path() from load_project API.",
        ))


def scan_evidence_overrides(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    legacy_only = "LEGACY_ONLY_EVIDENCE_REGISTRY = True" in content
    if "THEME_EVIDENCE_FILES" in content:
        match = re.search(r"THEME_EVIDENCE_FILES\s*=\s*\{(.*?)\}", content, re.DOTALL)
        if match:
            theme_keys = re.findall(r'"([^"]+)"\s*:', match.group(1))
            for key in theme_keys:
                if "/" in key or key in ("高速光模块", "光器件/FAU/精密光学"):
                    findings.append(AuditFinding(
                        file=rel_path,
                        category="evidence_hardcoding",
                        severity="LOW" if legacy_only else "HIGH",
                        code="THEME_KEY_LEGACY",
                        message=(
                            f"THEME_EVIDENCE_FILES uses legacy theme name as key: '{key}'"
                            + (" (legacy-only adapter)." if legacy_only else ".")
                        ),
                        location="THEME_EVIDENCE_FILES dict",
                        recommendation=(
                            "Keep this legacy-only; project-aware evidence must use "
                            "resolve_evidence_files_for_sector()."
                        ),
                    ))

    if "EVIDENCE_DIR = ROOT" in content and "EVIDENCE_DIR" in content:
        findings.append(AuditFinding(
            file=rel_path,
            category="evidence_path",
            severity="LOW" if legacy_only else "MEDIUM",
            code="HARDCODED_EVIDENCE_DIR",
            message=(
                "EVIDENCE_DIR is hardcoded relative to ROOT"
                + (" in legacy-only adapter." if legacy_only else ".")
            ),
            location="EVIDENCE_DIR definition",
            recommendation="Project-aware evidence should resolve via load_project.py.",
        ))


def scan_evidence_schema_readiness(
    project_id: str,
    findings: list[AuditFinding],
) -> None:
    """Check active evidence YAML schema/source_id readiness."""
    try:
        from investment_system.pipelines.sector_research.audit_evidence_schema import (
            audit_project as audit_evidence_schema_project,
        )
    except Exception as exc:  # noqa: BLE001 - readiness audit should surface import failures
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/audit_evidence_schema.py",
            category="evidence_schema",
            severity="HIGH",
            code="EVIDENCE_SCHEMA_AUDIT_UNAVAILABLE",
            message=f"Cannot import evidence schema audit: {exc}",
            recommendation="Ensure audit_evidence_schema.py is present and importable.",
        ))
        return

    schema_findings, summary = audit_evidence_schema_project(project_id, write_report=False)
    blocking_codes = {"SEED_DOCUMENT_AS_EVIDENCE", "RETIRED_OUTPUT_AS_EVIDENCE"}
    high_codes = {
        "EVIDENCE_SCHEMA_FIELD_MISSING",
        "EVIDENCE_FILE_ID_MISMATCH",
        "SOURCE_ID_MISSING",
        "SOURCE_ID_DUPLICATE",
        "EVIDENCE_ID_MISSING",
        "EVIDENCE_ID_DUPLICATE",
        "CLAIM_WITHOUT_SOURCE_ID",
        "EVIDENCE_ITEM_SOURCE_ID_UNRESOLVED",
        "EVIDENCE_ITEM_SECTOR_ID_LEGACY",
        "EVIDENCE_ITEM_SECTOR_ID_INVALID",
        "CANONICAL_SECTOR_ID_IS_LEGACY",
        "CANONICAL_SECTOR_ID_INVALID",
    }

    for item in schema_findings:
        severity = "LOW"
        if item.code in blocking_codes:
            severity = "BLOCKER"
        elif item.severity == "ERROR" or item.code in high_codes:
            severity = "HIGH"
        elif item.severity == "WARNING":
            severity = "MEDIUM"

        findings.append(AuditFinding(
            file=item.file or "investment_system/research/evidence",
            category="evidence_schema",
            severity=severity,
            code=item.code,
            message=item.message,
            location="active evidence YAML",
            recommendation="Run audit_evidence_schema.py and fix schema/source_id references before evidence-dependent generation.",
        ))

    if not [f for f in schema_findings if f.severity == "ERROR"]:
        findings.append(AuditFinding(
            file="investment_system/research/evidence",
            category="evidence_schema",
            severity="LOW",
            code="EVIDENCE_SCHEMA_READY",
            message=(
                f"Active evidence schema/source_id audit has ERROR=0 "
                f"(files={summary.get('evidence_file_count')}, "
                f"sources={summary.get('source_count')}, "
                f"items={summary.get('evidence_item_count')})."
            ),
            location="active evidence YAML",
            recommendation="Proceed to the next phase after reviewing remaining warnings.",
        ))


def scan_output_schema_readiness(
    project_id: str,
    findings: list[AuditFinding],
) -> None:
    """Check output contract/schema readiness through the dedicated audit."""
    try:
        from investment_system.pipelines.sector_research.audit_output_schema import (
            audit_project as audit_output_schema_project,
        )
    except Exception as exc:  # noqa: BLE001
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/audit_output_schema.py",
            category="output_schema",
            severity="HIGH",
            code="OUTPUT_SCHEMA_AUDIT_UNAVAILABLE",
            message=f"Cannot import output schema audit: {exc}",
            recommendation="Ensure audit_output_schema.py is present and importable.",
        ))
        return

    output_findings, summary = audit_output_schema_project(project_id, write_report=False)
    for item in output_findings:
        severity = "LOW"
        if item.severity == "ERROR":
            severity = "HIGH"
        elif item.severity == "WARNING":
            severity = "MEDIUM"
        findings.append(AuditFinding(
            file=item.file or "investment_system/research/schemas/output.schema.yaml",
            category="output_schema",
            severity=severity,
            code=item.code,
            message=item.message,
            location="output schema audit",
            recommendation="Run audit_output_schema.py and resolve project-aware output contract issues.",
        ))

    if not [f for f in output_findings if f.severity == "ERROR"]:
        findings.append(AuditFinding(
            file="investment_system/research/schemas/output.schema.yaml",
            category="output_schema",
            severity="LOW",
            code="OUTPUT_SCHEMA_READY",
            message=(
                f"Output schema audit has ERROR=0 "
                f"(types={summary.get('output_type_count')}, "
                f"company_table={summary.get('company_table_contract_status')}, "
                f"validate_outputs={summary.get('validate_outputs_contract_status')})."
            ),
            location="output schema audit",
            recommendation="Proceed to generator dry-run alignment after reviewing warnings.",
        ))


def scan_mock_output_readiness(
    project_id: str,
    findings: list[AuditFinding],
) -> None:
    """Check mock output generation readiness through the dedicated audit."""
    try:
        from investment_system.pipelines.sector_research.audit_mock_outputs import (
            audit_project as audit_mock_outputs_project,
        )
    except Exception as exc:  # noqa: BLE001
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/audit_mock_outputs.py",
            category="mock_output",
            severity="HIGH",
            code="MOCK_OUTPUT_AUDIT_UNAVAILABLE",
            message=f"Cannot import mock output audit: {exc}",
            recommendation="Ensure audit_mock_outputs.py is present and importable.",
        ))
        return

    _, summary = audit_mock_outputs_project(project_id, write_report=False)
    if summary.get("formal_output_write_violation_count", 0):
        findings.append(AuditFinding(
            file="investment_system/research/projects/tech_ai_semiconductor/audits/mock_outputs",
            category="mock_output",
            severity="BLOCKER",
            code="MOCK_OUTPUT_FORMAL_ROOT_WRITE",
            message="Mock output audit found mock files inside the formal output root.",
            location="mock output audit",
            recommendation="Remove manually after explicit approval and keep mock writes under audits/mock_outputs only.",
        ))

    if summary.get("record_shape_fail_count", 0) or summary.get("deprecated_field_violation_count", 0):
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/build_mock_outputs.py",
            category="mock_output",
            severity="HIGH",
            code="MOCK_OUTPUT_RECORD_SHAPE_FAILED",
            message=(
                f"Mock output shape failures={summary.get('record_shape_fail_count')} "
                f"deprecated violations={summary.get('deprecated_field_violation_count')}."
            ),
            location="mock output audit",
            recommendation="Fix mock records until validate_output_record_shape passes for all output types.",
        ))

    if summary.get("mock_record_count") != summary.get("output_type_count"):
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/build_mock_outputs.py",
            category="mock_output",
            severity="MEDIUM",
            code="MOCK_OUTPUT_TYPE_COVERAGE_INCOMPLETE",
            message=(
                f"Mock records cover {summary.get('mock_record_count')} of "
                f"{summary.get('output_type_count')} output types."
            ),
            location="mock output audit",
            recommendation="Add mock records for every output_type before formal generator wiring.",
        ))
    elif not summary.get("record_shape_fail_count") and not summary.get("formal_output_write_violation_count"):
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/build_mock_outputs.py",
            category="mock_output",
            severity="LOW",
            code="MOCK_OUTPUT_BASELINE_READY",
            message=(
                f"Mock output records pass for {summary.get('output_type_count')} output types; "
                "formal generator preview readiness is checked separately."
            ),
            location="mock output audit",
            recommendation="Keep mock files as audit-only fixtures.",
        ))

    findings.append(AuditFinding(
        file="investment_system/research/projects/tech_ai_semiconductor/audits/mock_outputs",
        category="mock_output",
        severity="LOW",
        code="MOCK_OUTPUT_AUDIT_READY",
        message=(
            f"Mock output audit summary: ERROR={summary.get('ERROR')}, "
            f"records={summary.get('mock_record_count')}, files={summary.get('mock_file_count')}."
        ),
        location="mock output audit",
        recommendation="Use mock files only for audit validation; do not treat them as formal research outputs.",
    ))


def scan_generator_preview_readiness(
    project_id: str,
    findings: list[AuditFinding],
) -> None:
    """Check formal generator contract readiness through audit-only previews."""
    try:
        from investment_system.pipelines.sector_research.audit_generator_previews import (
            audit_project as audit_generator_previews_project,
        )
    except Exception as exc:  # noqa: BLE001
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/audit_generator_previews.py",
            category="generator_preview",
            severity="HIGH",
            code="GENERATOR_PREVIEW_AUDIT_UNAVAILABLE",
            message=f"Cannot import generator preview audit: {exc}",
            recommendation="Ensure audit_generator_previews.py is present and importable.",
        ))
        return

    _, summary = audit_generator_previews_project(project_id, write_report=False)
    if summary.get("formal_output_write_violation_count", 0):
        findings.append(AuditFinding(
            file="investment_system/research/projects/tech_ai_semiconductor/audits/generator_previews",
            category="generator_preview",
            severity="BLOCKER",
            code="GENERATOR_PREVIEW_FORMAL_ROOT_WRITE",
            message="Generator preview audit found preview files inside the formal output root.",
            location="generator preview audit",
            recommendation="Remove manually after explicit approval and keep previews under audits/generator_previews only.",
        ))

    if summary.get("record_shape_fail_count", 0) or summary.get("investment_conclusion_violation_count", 0):
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/output_writers.py",
            category="generator_preview",
            severity="HIGH",
            code="GENERATOR_PREVIEW_RECORD_SHAPE_FAILED",
            message=(
                f"Generator preview shape failures={summary.get('record_shape_fail_count')} "
                f"investment conclusion violations={summary.get('investment_conclusion_violation_count')}."
            ),
            location="generator preview audit",
            recommendation="Fix preview writer records before production gate work.",
        ))

    expected_files = summary.get("output_type_count", 0)
    if summary.get("preview_file_count", 0) < expected_files:
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/output_writers.py",
            category="generator_preview",
            severity="MEDIUM",
            code="GENERATOR_PREVIEW_TYPE_COVERAGE_INCOMPLETE",
            message=(
                f"Generator previews cover {summary.get('preview_file_count')} files for "
                f"{summary.get('output_type_count')} output types."
            ),
            location="generator preview audit",
            recommendation="Run --dry-run-generate --write-audit-preview for a canonical sector and re-audit.",
        ))

    writer_path = WORKSPACE_ROOT / "investment_system" / "pipelines" / "sector_research" / "output_writers.py"
    writer_content = writer_path.read_text(encoding="utf-8", errors="replace") if writer_path.exists() else ""
    has_score_placeholder_gate = all(
        token in writer_content
        for token in (
            "FORMAL_SCORING_DISABLED",
            "def build_score_placeholder_record",
            "def write_score_placeholder",
            "allow_formal_output",
            "_assert_formal_output_path",
            "_reject_preview_markers",
        )
    )
    has_canonical_log_writer = all(
        token in writer_content
        for token in (
            "def write_canonical_log_records",
            '"missing_data_log", "conflict_data_log"',
            "allow_formal_output",
            "_assert_formal_output_path",
        )
    )

    if summary.get("preview_score_table_pass_count", 0) and not has_score_placeholder_gate:
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/output_writers.py",
            category="generator_preview",
            severity="MEDIUM",
            code="SCORE_TABLE_PREVIEW_ONLY",
            message="score_table has a contract-aligned preview writer, but no production scoring calculator is enabled.",
            location="score_table preview writer",
            recommendation="Add production gate/no-data safe mode before formal scoring output generation.",
        ))
    elif summary.get("preview_score_table_pass_count", 0):
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/output_writers.py",
            category="generator_preview",
            severity="LOW",
            code="SCORE_TABLE_PRODUCTION_GATE_READY",
            message="score_table has a formal no-data-safe placeholder writer gated by allow_formal_output.",
            location="score_table formal writer",
            recommendation="Keep formal scoring disabled until source-backed scoring inputs are complete.",
        ))

    if summary.get("canonical_missing_conflict_log_pass_count", 0) == 2 and not has_canonical_log_writer:
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/output_writers.py",
            category="generator_preview",
            severity="MEDIUM",
            code="CANONICAL_LOG_PREVIEW_READY_PRODUCTION_PENDING",
            message="missing/conflict logs have canonical preview shape; production DataTracker still needs explicit canonical writer routing.",
            location="missing/conflict preview writer",
            recommendation="Connect production log writer only after no-data safe mode is in place.",
        ))
    elif summary.get("canonical_missing_conflict_log_pass_count", 0) == 2:
        findings.append(AuditFinding(
            file="investment_system/pipelines/sector_research/output_writers.py",
            category="generator_preview",
            severity="LOW",
            code="CANONICAL_LOG_PRODUCTION_WRITER_READY",
            message="missing/conflict logs have a gated canonical production writer.",
            location="missing/conflict formal writer",
            recommendation="Use write_canonical_log_records for formal missing/conflict outputs.",
        ))

    findings.append(AuditFinding(
        file="investment_system/research/projects/tech_ai_semiconductor/audits/generator_previews",
        category="generator_preview",
        severity="LOW",
        code="GENERATOR_PREVIEW_AUDIT_READY",
        message=(
            f"Generator preview audit summary: ERROR={summary.get('ERROR')}, "
            f"files={summary.get('preview_file_count')}, record_pass={summary.get('record_shape_pass_count')}."
        ),
        location="generator preview audit",
        recommendation="Use preview files only for engineering validation; do not treat them as formal research outputs.",
    ))


def scan_validate_outputs(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    has_hardcoded_out = (
        'OUT = ROOT / "科技主线调研输出"' in content
        or "OUT = ROOT / '科技主线调研输出'" in content
        or re.search(r'OUT\s*=\s*ROOT\s*/\s*["\']科技主线调研输出["\']', content) is not None
    )
    out_used_in_paths = re.search(r'OUT\s*/\s*["\']', content) is not None
    if has_hardcoded_out and out_used_in_paths:
        findings.append(AuditFinding(
            file=rel_path, category="output_path", severity="BLOCKER",
            code="HARDCODED_OUT_DIR",
            message='OUT is hardcoded to ROOT / "科技主线调研输出" and used in paths.',
            location="OUT definition",
            recommendation="Import load_project and use config.output_root",
        ))

    if "THEME_REGISTRY_CSV" in content:
        findings.append(AuditFinding(
            file=rel_path, category="legacy_reference", severity="MEDIUM",
            code="HARDCODED_THEME_REGISTRY",
            message="validate_outputs.py references THEME_REGISTRY_CSV.",
            location="THEME_REGISTRY_CSV reference",
            recommendation="Read sub_theme from sector_universe.yaml via load_project()",
        ))

    if 'get("sub_theme")' in content or "sub_theme" in content:
        findings.append(AuditFinding(
            file=rel_path, category="field_schema", severity="MEDIUM",
            code="SUB_THEME_FIELD_REFERENCE",
            message="validate_outputs.py references 'sub_theme' field.",
            location="validate_outputs.py",
            recommendation="Filter by sector_id instead of sub_theme where applicable",
        ))


def run_audit(project_id: str) -> tuple[list[AuditFinding], dict[str, Any]]:
    findings: list[AuditFinding] = []

    files_to_scan = {
        "investment_system/pipelines/run_research.py": WORKSPACE_ROOT / "investment_system" / "pipelines" / "run_research.py",
        "investment_system/pipelines/validate_outputs.py": WORKSPACE_ROOT / "investment_system" / "pipelines" / "validate_outputs.py",
        "investment_system/pipelines/evidence_overrides.py": WORKSPACE_ROOT / "investment_system" / "pipelines" / "evidence_overrides.py",
    }

    output_spec = load_output_spec(project_id)

    for rel_path, file_path in files_to_scan.items():
        if not file_path.exists():
            findings.append(AuditFinding(
                file=rel_path, category="file_missing", severity="LOW",
                code="FILE_NOT_FOUND",
                message=f"Audit target file does not exist: {rel_path}",
                recommendation="File may have been moved or renamed",
            ))
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")
        scan_hardcoded_strings(file_path, content, rel_path, findings)

        if rel_path == "investment_system/pipelines/run_research.py":
            scan_project_aware_canonical(content, rel_path, findings)
            scan_field_mismatches(file_path, content, rel_path, output_spec, findings)
            scan_subtheme_hardcoding(file_path, content, rel_path, findings)
            scan_card_path_generation(file_path, content, rel_path, findings)
        elif rel_path == "investment_system/pipelines/validate_outputs.py":
            scan_validate_outputs(file_path, content, rel_path, findings)
        elif rel_path == "investment_system/pipelines/evidence_overrides.py":
            scan_evidence_overrides(file_path, content, rel_path, findings)

    schema_dir = WORKSPACE_ROOT / "investment_system" / "research" / "schemas"
    for fname in ["comparison_table_schema.yaml", "source_index_schema.yaml"]:
        p = schema_dir / fname
        if not p.exists():
            findings.append(AuditFinding(
                file=f"schemas/{fname}", category="schema", severity="LOW",
                code="SCHEMA_FILE_MISSING",
                message=f"Schema file schemas/{fname} not found.",
                recommendation=f"Create schemas/{fname} per output_spec schema definitions",
            ))

    scan_evidence_schema_readiness(project_id, findings)
    scan_output_schema_readiness(project_id, findings)
    scan_mock_output_readiness(project_id, findings)
    scan_generator_preview_readiness(project_id, findings)

    by_severity: dict[str, list[AuditFinding]] = {"BLOCKER": [], "HIGH": [], "MEDIUM": [], "LOW": []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)

    summary = {
        "project_id": project_id,
        "files_scanned": len(files_to_scan),
        "total_findings": len(findings),
        "BLOCKER_count": len(by_severity["BLOCKER"]),
        "HIGH_count": len(by_severity["HIGH"]),
        "MEDIUM_count": len(by_severity["MEDIUM"]),
        "LOW_count": len(by_severity["LOW"]),
        "next_steps": _build_next_steps(by_severity),
    }
    return findings, summary


def _build_next_steps(by_severity: dict[str, list[AuditFinding]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    blockers = by_severity.get("BLOCKER", [])
    high = by_severity.get("HIGH", [])

    if blockers:
        steps.append({
            "phase": "1E-c-a (verify fix)",
            "title": "BLOCKER found — resolve before production",
            "description": "Hardcoded card paths still bypass loader API.",
            "severity": "BLOCKER",
            "blocks": ["1E-c-b"],
        })

    # Check for project-aware KNOWN_COMPANIES usage (post 1E-c-a fix: should be gone)
    known_company_highs = [
        f for f in high
        if f.code == "HARDCODED_STRING"
        and "KNOWN_COMPANIES" in f.message
        and "project-aware" in f.recommendation.lower()
    ]
    if known_company_highs:
        steps.append({
            "phase": "1E-c-a (verify)",
            "title": "KNOWN_COMPANIES project-aware active usage",
            "description": "Some code paths still reference KNOWN_COMPANIES in project-aware context.",
            "severity": "HIGH",
        })
    else:
        steps.append({
            "phase": "1E-c-a",
            "title": "KNOWN_COMPANIES migrated to stock_universe.yaml",
            "description": "All project-aware stock sources use stock_universe.yaml. KNOWN_COMPANIES is legacy-only.",
            "severity": "info",
        })

    canonical_highs = [f for f in high if f.category == "canonical_sector_id"]
    if canonical_highs:
        steps.append({
            "phase": "1E-b (verify)",
            "title": "Canonical sector_id checks",
            "description": "Some project-aware canonical checks failed.",
            "severity": "HIGH",
        })

    ev_issues = [f for f in high + by_severity.get("MEDIUM", [])
                 if f.category in ("evidence_hardcoding", "evidence_path")]
    if ev_issues:
        steps.append({
            "phase": "1E-d",
            "title": "evidence_overrides.py 迁移",
            "description": "Replace THEME_EVIDENCE_FILES dict with resolve_evidence_files_for_sector(config, sector_id).",
            "severity": "HIGH",
        })
    else:
        steps.append({
            "phase": "1E-d-a",
            "title": "project-aware evidence resolver",
            "description": "evidence_overrides.py is legacy-only; project-aware evidence uses load_project resolver.",
            "severity": "info",
        })

    ev_schema_highs = [f for f in high if f.category == "evidence_schema"]
    ev_schema_mediums = [f for f in by_severity.get("MEDIUM", []) if f.category == "evidence_schema"]
    if ev_schema_highs:
        steps.append({
            "phase": "1E-d-b",
            "title": "evidence schema/source_id readiness",
            "description": "Active evidence YAML still has schema/source_id/evidence_id errors.",
            "severity": "HIGH",
        })
    elif ev_schema_mediums:
        steps.append({
            "phase": "1E-d-b",
            "title": "evidence schema/source_id warnings",
            "description": "Active evidence YAML has no schema ERROR, but source metadata warnings remain.",
            "severity": "MEDIUM",
        })
    else:
        steps.append({
            "phase": "1E-d-b",
            "title": "evidence schema/source_id normalized",
            "description": "Active evidence YAML has schema/source_id/evidence_id audit ERROR=0.",
            "severity": "info",
        })

    field_highs = [f for f in high if f.category == "field_schema"]
    field_mediums = [f for f in by_severity.get("MEDIUM", []) if f.category == "field_schema"]
    if field_highs:
        steps.append({
            "phase": "1E-e",
            "title": "输出字段对齐 output_spec/schema",
            "description": "COMPANY_TABLE_FIELDS / COMPARISON_FIELDS / SOURCE_FIELDS must match output_spec fields.",
            "severity": "HIGH",
        })
    elif field_mediums:
        steps.append({
            "phase": "1E-e",
            "title": "legacy validation field references",
            "description": "Output contract is aligned; validate_outputs still keeps legacy compatibility references.",
            "severity": "MEDIUM",
        })

    output_schema_highs = [f for f in high if f.category == "output_schema"]
    output_schema_mediums = [f for f in by_severity.get("MEDIUM", []) if f.category == "output_schema"]
    if output_schema_highs:
        steps.append({
            "phase": "1E-e-a",
            "title": "output schema readiness",
            "description": "Project-aware output contract still has ERROR-level issues.",
            "severity": "HIGH",
        })
    elif output_schema_mediums:
        steps.append({
            "phase": "1E-e-a",
            "title": "output schema warnings",
            "description": "Output contract is loadable with ERROR=0; legacy warnings remain.",
            "severity": "MEDIUM",
        })
    else:
        steps.append({
            "phase": "1E-e-a",
            "title": "output schema baseline ready",
            "description": "Output schema audit has ERROR=0 and validate_outputs loads the contract.",
            "severity": "info",
        })

    mock_highs = [f for f in high if f.category == "mock_output"]
    mock_mediums = [f for f in by_severity.get("MEDIUM", []) if f.category == "mock_output"]
    if mock_highs:
        steps.append({
            "phase": "1E-e-b",
            "title": "mock output shape failed",
            "description": "Mock output records or write-safety checks failed.",
            "severity": "HIGH",
        })
    elif mock_mediums:
        steps.append({
            "phase": "1E-e-c",
            "title": "formal generator contract wiring",
            "description": "Mock records pass; connect formal generators to the canonical output contract next.",
            "severity": "MEDIUM",
        })
    else:
        steps.append({
            "phase": "1E-e-b",
            "title": "mock output dry-run baseline ready",
            "description": "Mock output records cover the contract without shape failures.",
            "severity": "info",
        })

    generator_highs = [f for f in high if f.category == "generator_preview"]
    generator_mediums = [f for f in by_severity.get("MEDIUM", []) if f.category == "generator_preview"]
    if generator_highs:
        steps.append({
            "phase": "1E-e-c",
            "title": "generator preview shape failed",
            "description": "Generator previews still have shape, write-safety, or investment-conclusion violations.",
            "severity": "HIGH",
        })
    elif generator_mediums:
        steps.append({
            "phase": "1E-e-d",
            "title": "production gate / no-data safe mode",
            "description": "Generator previews pass; production writers remain gated until no-data safe mode is added.",
            "severity": "MEDIUM",
        })
    else:
        steps.append({
            "phase": "1E-e-c",
            "title": "generator preview contract ready",
            "description": "Canonical generator previews cover all output types without formal output writes.",
            "severity": "info",
        })

    if not [s for s in steps if s.get("severity") not in ("info",)]:
        steps.append({
            "phase": "1E-c-b",
            "title": "Enter 1E-c-b: 股票池补全",
            "description": "No BLOCKERs. Ready for 1E-c-b: pending_code_resolution处理 + 补全股票池.",
            "severity": "info",
        })

    return steps


def load_project_yaml(project_id: str) -> dict[str, Any]:
    path = PROJECTS_ROOT / project_id / "project.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_output_spec(project_id: str) -> dict[str, Any]:
    path = PROJECTS_ROOT / project_id / "output_spec.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_schemas(project_id: str) -> dict[str, dict[str, Any]]:
    schema_dir = WORKSPACE_ROOT / "investment_system" / "research" / "schemas"
    schemas = {}
    for fname in ["comparison_table_schema.yaml", "source_index_schema.yaml"]:
        p = schema_dir / fname
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                schemas[fname] = yaml.safe_load(f) or {}
    return schemas


def print_audit_report(findings: list[AuditFinding], summary: dict[str, Any]) -> None:
    print("=" * 70)
    print(f" Pipeline Readiness Audit — {summary['project_id']}")
    print(f" Files scanned: {summary['files_scanned']}  |  Total findings: {summary['total_findings']}")
    print("=" * 70)

    for sev in ["BLOCKER", "HIGH", "MEDIUM", "LOW"]:
        items = [f for f in findings if f.severity == sev]
        if not items:
            continue
        sep = "=" if sev == "BLOCKER" else "-"
        print(f"\n{sep * 70}")
        print(f" [{sev}] ({len(items)} findings)")
        print(sep * 70)
        by_file: dict[str, list[AuditFinding]] = {}
        for f in items:
            by_file.setdefault(f.file, []).append(f)
        for fname, flist in by_file.items():
            print(f"\n  {fname}:")
            for f in flist:
                loc = f"  [{f.code}] {f.message}"
                if f.location:
                    loc += f"  (at {f.location})"
                print(f"    {loc}")
                if f.recommendation:
                    print(f"      -> {f.recommendation}")

    print(f"\n{'=' * 70}")
    print(" Summary by severity:")
    print(f"   BLOCKER : {summary['BLOCKER_count']}")
    print(f"   HIGH    : {summary['HIGH_count']}")
    print(f"   MEDIUM  : {summary['MEDIUM_count']}")
    print(f"   LOW     : {summary['LOW_count']}")

    print(f"\n{'=' * 70}")
    print(" Recommended next steps:")
    for step in summary.get("next_steps", []):
        sev_tag = f"[{step['severity']}]" if step.get("severity") not in ("info",) else ""
        print(f"\n  Phase {step['phase']} {sev_tag} — {step['title']}")
        print(f"  {step['description']}")

    blockers = summary["BLOCKER_count"]
    if blockers > 0:
        print(f"\n  WARNING: {blockers} BLOCKER(s) found. Pipeline改造 must resolve these before running.")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit legacy pipeline files for project-aware readiness.")
    parser.add_argument("--project", default="tech_ai_semiconductor")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings, summary = run_audit(args.project)

    if args.json:
        print(json.dumps({"summary": summary, "findings": [f.to_dict() for f in findings]}, ensure_ascii=False, indent=2))
    else:
        print_audit_report(findings, summary)

    blockers = summary["BLOCKER_count"]
    return 1 if blockers > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
