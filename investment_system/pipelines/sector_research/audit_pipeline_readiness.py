"""
Pipeline Readiness Audit — Phase 1D.

Static audit of legacy pipeline files against the new project-aware schema.
Does NOT modify any files. Outputs findings grouped by severity.

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
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ── Path resolution (must work whether running as `python -m ...` or direct script) ──

def _resolve_workaround() -> Path:
    """
    Resolve the audit script path, working around __file__ issues when
    Python is invoked as `python -m package.module`.
    """
    me_mod = sys.modules[__name__]
    spec = getattr(me_mod, "__spec__", None)
    if spec and spec.origin:
        return Path(spec.origin).resolve()
    # Fallback: __file__ should give the real path
    return Path(__file__).resolve()

_AUDIT_PATH = _resolve_workaround()
# audit_pipeline_readiness.py is 3 levels below project root:
#   audit_pipeline_readiness.py → sector_research → pipelines → investment_system → project
WORKSPACE_ROOT = _AUDIT_PATH.parents[3]
PROJECTS_ROOT = WORKSPACE_ROOT / "investment_system" / "research" / "projects"


# ── Severity tiers ─────────────────────────────────────────────────────────

@dataclass
class AuditFinding:
    file: str
    category: str
    severity: str  # BLOCKER | HIGH | MEDIUM | LOW
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


# ── Hardcoded string patterns to scan ──────────────────────────────────────

HARDCODED_PATH_PATTERNS = {
    "科技主线调研输出": "output root directory",
    "A股科技前两主线调研文件包": "legacy research package",
    "01_AI算力硬件": "legacy sector group directory",
    "02_半导体国产替代": "legacy sector group directory",
    "高速光模块": "legacy sub-theme name (now cpo_optical_module_silicon_photonics)",
    "光器件/FAU/精密光学": "legacy sub-theme name (now optical_chip_components)",
    "cpo_optical_module": "legacy sector_id (now cpo_optical_module_silicon_photonics)",
    "optical_components": "legacy sector_id (now optical_chip_components)",
    "THEME_REGISTRY_CSV": "hardcoded reference to legacy mother-table CSV",
    "KNOWN_COMPANIES": "hardcoded inline company list (should come from stock_universe.yaml)",
    "OUT_DIR = ROOT /": "hardcoded OUT_DIR definition",
    "LOG_DIR =": "hardcoded LOG_DIR definition",
    "RAW_DIR =": "hardcoded RAW_DIR definition",
}


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
    """Load comparison_table_schema.yaml and source_index_schema.yaml if present."""
    schema_dir = WORKSPACE_ROOT / "investment_system" / "research" / "schemas"
    schemas = {}
    for fname in ["comparison_table_schema.yaml", "source_index_schema.yaml"]:
        p = schema_dir / fname
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                schemas[fname] = yaml.safe_load(f) or {}
    return schemas


def scan_hardcoded_strings(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    """Scan a file for hardcoded path/string patterns."""
    for pattern, description in HARDCODED_PATH_PATTERNS.items():
        for i, line in enumerate(content.splitlines(), 1):
            # Only flag lines that are actual code/assignment, not comments explaining the issue
            if pattern in line and not line.strip().startswith("#"):
                # Determine severity based on pattern type
                if pattern in ("cpo_optical_module", "optical_components"):
                    sev = "HIGH"
                elif pattern in ("THEME_REGISTRY_CSV", "KNOWN_COMPANIES", "OUT_DIR = ROOT /",
                                  "LOG_DIR =", "RAW_DIR ="):
                    sev = "HIGH"
                elif pattern in ("高速光模块", "光器件/FAU/精密光学",
                                  "科技主线调研输出", "A股科技前两主线调研文件包",
                                  "01_AI算力硬件", "02_半导体国产替代"):
                    sev = "MEDIUM"
                else:
                    sev = "MEDIUM"

                findings.append(AuditFinding(
                    file=rel_path,
                    category="hardcoded_strings",
                    severity=sev,
                    code="HARDCODED_STRING",
                    message=f"Found hardcoded string '{pattern}' ({description})",
                    location=f"line {i}",
                    recommendation=(
                        f"Replace with value from project config via load_project() API"
                    ),
                ))


def scan_field_mismatches(
    file_path: Path,
    content: str,
    rel_path: str,
    output_spec: dict[str, Any],
    findings: list[AuditFinding],
) -> None:
    """Check COMPANY_TABLE_FIELDS, COMPARISON_FIELDS, SOURCE_FIELDS vs schema."""
    if "COMPANY_TABLE_FIELDS" in content:
        # Extract the list from the source
        match = re.search(
            r"COMPANY_TABLE_FIELDS\s*=\s*\[(.*?)\]",
            content, re.DOTALL
        )
        if match:
            fields_str = match.group(1)
            # Extract quoted field names
            current_fields = re.findall(r'"(\w+)"', fields_str)
            expected_fields = [
                f.get("field") for f in output_spec.get("company_table_fields", [])
                if f.get("field")
            ]
            missing_in_current = [f for f in expected_fields if f not in current_fields]
            extra_in_current = [f for f in current_fields if f not in expected_fields]

            # Check for legacy fields that should be renamed
            legacy_mappings = {
                "main_theme": "parent_chain (moved to comparison table)",
                "sub_theme": "sector_id (canonical identifier)",
            }
            for old, new in legacy_mappings.items():
                if old in current_fields:
                    findings.append(AuditFinding(
                        file=rel_path,
                        category="field_schema",
                        severity="HIGH",
                        code="LEGACY_FIELD_NAME",
                        message=f"COMPANY_TABLE_FIELDS contains legacy field '{old}' "
                                f"(should be replaced with {new})",
                        location="COMPANY_TABLE_FIELDS definition",
                        recommendation="Align with output_spec.company_table_fields",
                    ))

            if extra_in_current:
                findings.append(AuditFinding(
                    file=rel_path,
                    category="field_schema",
                    severity="MEDIUM",
                    code="EXTRA_FIELDS",
                    message=f"COMPANY_TABLE_FIELDS contains fields not in "
                            f"output_spec: {extra_in_current}",
                    location="COMPANY_TABLE_FIELDS definition",
                    recommendation="Remove or align with output_spec.company_table_fields",
                ))

    if "COMPARISON_FIELDS" in content:
        match = re.search(
            r"COMPARISON_FIELDS\s*=\s*\[(.*?)\]",
            content, re.DOTALL
        )
        if match:
            fields_str = match.group(1)
            current_fields = re.findall(r'"(\w+)"', fields_str)
            expected_fields = [
                f.get("field") for f in output_spec.get("comparison_table_fields", [])
                if f.get("field")
            ]
            extra_in_current = [f for f in current_fields if f not in expected_fields]
            if extra_in_current:
                findings.append(AuditFinding(
                    file=rel_path,
                    category="field_schema",
                    severity="MEDIUM",
                    code="EXTRA_COMPARISON_FIELDS",
                    message=f"COMPARISON_FIELDS contains fields not in "
                            f"output_spec: {extra_in_current}",
                    location="COMPARISON_FIELDS definition",
                    recommendation="Align with output_spec.comparison_table_fields",
                ))

    if "SOURCE_FIELDS" in content:
        match = re.search(
            r"SOURCE_FIELDS\s*=\s*\[(.*?)\]",
            content, re.DOTALL
        )
        if match:
            fields_str = match.group(1)
            current_fields = re.findall(r'"(\w+)"', fields_str)
            expected_fields = [
                f.get("field") for f in output_spec.get("source_index_fields", [])
                if f.get("field")
            ]
            extra_in_current = [f for f in current_fields if f not in expected_fields]
            if extra_in_current:
                findings.append(AuditFinding(
                    file=rel_path,
                    category="field_schema",
                    severity="MEDIUM",
                    code="EXTRA_SOURCE_FIELDS",
                    message=f"SOURCE_FIELDS contains fields not in "
                            f"output_spec: {extra_in_current}",
                    location="SOURCE_FIELDS definition",
                    recommendation="Align with output_spec.source_index_fields",
                ))


def scan_subtheme_hardcoding(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    """Detect inline sub-theme / theme name strings instead of sector_id references."""
    # Patterns like "高速光模块" as dict keys or string literals in company lookups
    for line in content.splitlines():
        if '"高速光模块"' in line or "'高速光模块'" in line:
            findings.append(AuditFinding(
                file=rel_path,
                category="theme_hardcoding",
                severity="HIGH",
                code="THEME_NAME_HARDCODED",
                message=(
                    "Found inline theme name '高速光模块' used as dict key. "
                    "This should use sector_id 'cpo_optical_module_silicon_photonics' "
                    "or read from stock_universe.yaml"
                ),
                location=rel_path,
                recommendation="Replace with canonical sector_id via stock_universe lookup",
            ))
        if '"光器件/FAU/精密光学"' in line or "'光器件/FAU/精密光学'" in line:
            findings.append(AuditFinding(
                file=rel_path,
                category="theme_hardcoding",
                severity="HIGH",
                code="THEME_NAME_HARDCODED",
                message=(
                    "Found inline theme name '光器件/FAU/精密光学' used as dict key. "
                    "This should use sector_id 'optical_chip_components' "
                    "or read from stock_universe.yaml"
                ),
                location=rel_path,
                recommendation="Replace with canonical sector_id via stock_universe lookup",
            ))


def scan_card_path_generation(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    """Detect manual card path construction that bypasses output_spec."""
    # Pattern: os.path.join with hardcoded "01_" or "02_" prefixes
    if re.search(r'["\']01_', content) or re.search(r'["\']02_', content):
        if not re.search(r"output_spec|sector_card_path_template", content):
            findings.append(AuditFinding(
                file=rel_path,
                category="path_generation",
                severity="BLOCKER",
                code="HARDCODED_CARD_PATH",
                message=(
                    "Card path appears to use hardcoded prefix (01_/02_). "
                    "This bypasses output_spec.directories.sector_cards.path_template "
                    "and will write to wrong directory under new project structure."
                ),
                location=rel_path,
                recommendation=(
                    "Use resolve_sector_card_path() from load_project API, "
                    "or respect output_spec.directories.sector_cards.path_template"
                ),
            ))

    # Pattern: "01_" + sub_theme or theme name in path construction
    if re.search(r'["\']01_["\'].*\{', content) or re.search(r'f["\']01_', content):
        findings.append(AuditFinding(
            file=rel_path,
            category="path_generation",
            severity="BLOCKER",
            code="HARDCODED_THEME_DIR",
            message=(
                "Card path uses hardcoded theme directory prefix (e.g. '01_AI算力硬件'). "
                "New project uses {group_order}_{group_name} template from output_spec."
            ),
            location=rel_path,
            recommendation="Use resolve_sector_card_path(config, sector) instead",
        ))


def scan_evidence_overrides(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    """Audit evidence_overrides.py for project-unaware patterns."""
    if "THEME_EVIDENCE_FILES" in content:
        match = re.search(
            r"THEME_EVIDENCE_FILES\s*=\s*\{(.*?)\}",
            content, re.DOTALL
        )
        if match:
            body = match.group(1)
            theme_keys = re.findall(r'"([^"]+)"\s*:', body)
            for key in theme_keys:
                if "/" in key or key in ("高速光模块", "光器件/FAU/精密光学"):
                    findings.append(AuditFinding(
                        file=rel_path,
                        category="evidence_hardcoding",
                        severity="HIGH",
                        code="THEME_KEY_LEGACY",
                        message=(
                            f"THEME_EVIDENCE_FILES uses legacy theme name as key: '{key}'. "
                            f"Should use canonical sector_id as key."
                        ),
                        location="THEME_EVIDENCE_FILES dict",
                        recommendation=(
                            f"Use sector_id as key (e.g. 'cpo_optical_module_silicon_photonics'). "
                            f"Evidence files should be looked up via "
                            f"resolve_evidence_files_for_sector(config, sector_id)."
                        ),
                    ))

    if "EVIDENCE_DIR = ROOT" in content and "EVIDENCE_DIR" in content:
        findings.append(AuditFinding(
            file=rel_path,
            category="evidence_path",
            severity="MEDIUM",
            code="HARDCODED_EVIDENCE_DIR",
            message="EVIDENCE_DIR is hardcoded relative to ROOT. "
                    "Should come from output_spec.directories.evidence.path",
            location="EVIDENCE_DIR definition",
            recommendation="Read evidence_dir from output_spec.directories.evidence.path",
        ))


def scan_validate_outputs(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    """Audit validate_outputs.py for project-unaware patterns."""
    # Check for hardcoded OUT = ROOT / "科技主线调研输出"
    # NOTE: This is OK if OUT is only used as a legacy fallback default (never referenced
    # in path resolution). The BLOCKER fires only if OUT is actively used in paths.
    has_hardcoded_out = (
        'OUT = ROOT / "科技主线调研输出"' in content
        or "OUT = ROOT / '科技主线调研输出'" in content
        or re.search(r'OUT\s*=\s*ROOT\s*/\s*["\']科技主线调研输出["\']', content) is not None
    )
    # Additional check: is OUT actually used in the body for path construction?
    out_used_in_paths = (
        re.search(r'OUT\s*/\s*["\']', content) is not None  # OUT / "..."
    )
    if has_hardcoded_out and out_used_in_paths:
        findings.append(AuditFinding(
            file=rel_path,
            category="output_path",
            severity="BLOCKER",
            code="HARDCODED_OUT_DIR",
            message='OUT is hardcoded to ROOT / "科技主线调研输出". '
                    'Should use config.output_root from load_project().',
            location="OUT definition",
            recommendation="Import load_project and use config.output_root",
        ))

    if "THEME_REGISTRY_CSV" in content:
        findings.append(AuditFinding(
            file=rel_path,
            category="legacy_reference",
            severity="MEDIUM",
            code="HARDCODED_THEME_REGISTRY",
            message="validate_outputs.py references THEME_REGISTRY_CSV. "
                    "Sub-theme to sector mapping should come from sector_universe.yaml.",
            location="THEME_REGISTRY_CSV reference",
            recommendation="Read sub_theme from sector_universe.yaml via load_project()",
        ))

    # Check for sub_theme field usage vs sector_id
    if 'get("sub_theme")' in content or "sub_theme" in content:
        findings.append(AuditFinding(
            file=rel_path,
            category="field_schema",
            severity="MEDIUM",
            code="SUB_THEME_FIELD_REFERENCE",
            message="validate_outputs.py references 'sub_theme' field. "
                    "New schema uses 'sector_id' as canonical identifier.",
            location="validate_outputs.py",
            recommendation="Filter by sector_id instead of sub_theme where applicable",
        ))


def scan_tools_file(
    file_path: Path,
    content: str,
    rel_path: str,
    findings: list[AuditFinding],
) -> None:
    """Audit tools/collect_high_speed_optical.py for project-unaware patterns."""
    if '"高速光模块"' in content or "'高速光模块'" in content:
        findings.append(AuditFinding(
            file=rel_path,
            category="theme_hardcoding",
            severity="HIGH",
            code="THEME_NAME_HARDCODED",
            message="'高速光模块' is hardcoded as dataset name. "
                    "Should use sector_id 'cpo_optical_module_silicon_photonics'.",
            location=rel_path,
            recommendation="Rename to canonical sector_id or read from stock_universe",
        ))

    if 'ROOT / "科技主线调研输出"' in content:
        findings.append(AuditFinding(
            file=rel_path,
            category="output_path",
            severity="MEDIUM",
            code="HARDCODED_OUTPUT_PATH",
            message="Output path hardcoded relative to ROOT. "
                    "Should use project config.",
            location=rel_path,
            recommendation="Use output_root from project config via load_project()",
        ))


def run_audit(project_id: str) -> tuple[list[AuditFinding], dict[str, Any]]:
    """Run all audit checks against the project."""
    findings: list[AuditFinding] = []

    files_to_scan = {
        "investment_system/pipelines/run_research.py": WORKSPACE_ROOT / "investment_system" / "pipelines" / "run_research.py",
        "investment_system/pipelines/validate_outputs.py": WORKSPACE_ROOT / "investment_system" / "pipelines" / "validate_outputs.py",
        "investment_system/pipelines/evidence_overrides.py": WORKSPACE_ROOT / "investment_system" / "pipelines" / "evidence_overrides.py",
        "tools/collect_high_speed_optical.py": WORKSPACE_ROOT / "tools" / "collect_high_speed_optical.py",
    }

    output_spec = load_output_spec(project_id)

    for rel_path, file_path in files_to_scan.items():
        if not file_path.exists():
            findings.append(AuditFinding(
                file=rel_path,
                category="file_missing",
                severity="LOW",
                code="FILE_NOT_FOUND",
                message=f"Audit target file does not exist: {rel_path}",
                recommendation="File may have been moved or renamed",
            ))
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")
        scan_hardcoded_strings(file_path, content, rel_path, findings)

        if rel_path == "investment_system/pipelines/run_research.py":
            scan_field_mismatches(file_path, content, rel_path, output_spec, findings)
            scan_subtheme_hardcoding(file_path, content, rel_path, findings)
            scan_card_path_generation(file_path, content, rel_path, findings)
        elif rel_path == "investment_system/pipelines/validate_outputs.py":
            scan_validate_outputs(file_path, content, rel_path, findings)
        elif rel_path == "investment_system/pipelines/evidence_overrides.py":
            scan_evidence_overrides(file_path, content, rel_path, findings)
        elif rel_path == "tools/collect_high_speed_optical.py":
            scan_tools_file(file_path, content, rel_path, findings)

    # Check for missing schema files
    schema_dir = WORKSPACE_ROOT / "investment_system" / "research" / "schemas"
    for fname in ["comparison_table_schema.yaml", "source_index_schema.yaml"]:
        p = schema_dir / fname
        if not p.exists():
            findings.append(AuditFinding(
                file=f"schemas/{fname}",
                category="schema",
                severity="LOW",
                code="SCHEMA_FILE_MISSING",
                message=f"Schema file schemas/{fname} not found. "
                        "Field-level validation cannot be performed.",
                recommendation=f"Create schemas/{fname} per output_spec schema definitions",
            ))

    # Build summary
    by_severity: dict[str, list[AuditFinding]] = {
        "BLOCKER": [], "HIGH": [], "MEDIUM": [], "LOW": [],
    }
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

    if blockers or high:
        steps.append({
            "phase": "1E-a",
            "title": "run_research 路径改为 project-aware",
            "description": (
                "Replace hardcoded OUT_DIR, LOG_DIR, RAW_DIR with config.output_root, "
                "config.sector_cards_root, config.total_tables_dir, config.logs_dir "
                "from load_project(). Replace {group_order}_{group_name} template with "
                "resolve_sector_card_path(config, sector_dict)."
            ),
            "severity": "BLOCKER" if blockers else "HIGH",
            "blocks": ["1E-b", "1E-c"],
        })

    # Check evidence issues
    ev_issues = [f for f in high + by_severity.get("MEDIUM", [])
                 if f.category in ("evidence_hardcoding", "evidence_path")]
    if ev_issues:
        steps.append({
            "phase": "1E-d",
            "title": "evidence 从 run_manifest + evidence_file_ids 读取",
            "description": (
                "Replace THEME_EVIDENCE_FILES dict with "
                "resolve_evidence_files_for_sector(config, sector_id). "
                "Replace legacy theme name keys with canonical sector_id. "
                "Read evidence_dir from output_spec.directories.evidence.path."
            ),
            "severity": "HIGH",
        })

    # Check field schema issues
    field_issues = [f for f in high + by_severity.get("MEDIUM", [])
                    if f.category == "field_schema"]
    if field_issues:
        steps.append({
            "phase": "1E-e",
            "title": "输出字段对齐 output_spec/schema",
            "description": (
                "COMPANY_TABLE_FIELDS / COMPARISON_FIELDS / SOURCE_FIELDS "
                "must match output_spec.company_table_fields, "
                "output_spec.comparison_table_fields, "
                "output_spec.source_index_fields. "
                "Replace 'main_theme'/'sub_theme' with canonical fields."
            ),
            "severity": "HIGH",
        })

    # Check validate_outputs issues
    vo_issues = [f for f in blockers + high
                 if "validate_outputs" in f.file or "validate" in f.category]
    if vo_issues:
        steps.append({
            "phase": "1E-f",
            "title": "validate_outputs 改为 project-aware",
            "description": (
                "Replace hardcoded OUT = ROOT / '科技主线调研输出' with "
                "load_project(). Validate against output_spec field schemas. "
                "Filter by sector_id instead of sub_theme."
            ),
            "severity": "BLOCKER",
        })

    if not steps:
        steps.append({
            "phase": "1E",
            "title": "进入 1E 阶段",
            "description": "No critical blockers. Proceed with project-aware pipeline改造.",
            "severity": "info",
        })

    return steps


def print_audit_report(findings: list[AuditFinding], summary: dict[str, Any]) -> None:
    print(f"=" * 70)
    print(f" Pipeline Readiness Audit — {summary['project_id']}")
    print(f" Files scanned: {summary['files_scanned']}  |  Total findings: {summary['total_findings']}")
    print(f"=" * 70)

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
    parser = argparse.ArgumentParser(
        description="Audit legacy pipeline files for project-aware readiness.",
    )
    parser.add_argument("--project", default="tech_ai_semiconductor")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings, summary = run_audit(args.project)

    if args.json:
        result = {
            "summary": summary,
            "findings": [f.to_dict() for f in findings],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_audit_report(findings, summary)

    blockers = summary["BLOCKER_count"]
    return 1 if blockers > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
