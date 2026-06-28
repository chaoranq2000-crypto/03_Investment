"""
Stock Universe Coverage Audit — Phase 1E-c-a.

Audits the stock_universe.yaml for a project:
  - Per-sector coverage counts (listed / pending / reference)
  - Duplicate code/name checks
  - Invalid sector refs in stocks and pending entries
  - Orphan stock checks (stocks with no sector)
  - Over-broad stock checks (>3 sectors)
  - P0/P1 coverage thresholds (>=5 for P0/P1, >=3 for P2)
  - Observation_only sector coverage exemption

Usage:
    python .codex/skills/quality-auditor/scripts/cli.py stock-universe --project tech_ai_semiconductor
    python .codex/skills/quality-auditor/scripts/cli.py stock-universe --project tech_ai_semiconductor --json
    python .codex/skills/quality-auditor/scripts/cli.py stock-universe --project tech_ai_semiconductor --include-pending

Exit codes:
    0  audit complete, ERROR=0
    1  ERRORs found (invalid refs, duplicates)
    2  audit itself failed
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

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


# ── Coverage thresholds ───────────────────────────────────────────────────────

P0_P1_MIN_LISTED = 5
P2_P3_MIN_LISTED = 3


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class AuditIssue:
    severity: str          # ERROR | WARNING | INFO
    code: str
    sector_id: str
    message: str
    stock_name: str = ""
    stock_code: str = ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "code": self.code,
            "sector_id": self.sector_id,
            "stock_name": self.stock_name,
            "stock_code": self.stock_code,
            "message": self.message,
        }


@dataclass
class SectorCoverage:
    sector_id: str
    sector_name: str
    priority: str
    scoring_enabled: bool
    is_observation_only: bool
    listed_count: int
    pending_count: int
    reference_count: int
    coverage_status: str          # ok | thin | missing | exempt
    listed_stocks: list[dict] = field(default_factory=list)
    pending_stocks: list[dict] = field(default_factory=list)
    issues: list[AuditIssue] = field(default_factory=list)


@dataclass
class AuditResult:
    project_id: str
    total_listed: int
    total_pending: int
    total_reference: int
    total_sectors: int
    sectors_with_coverage: int
    sectors_missing: int
    sectors_thin: int
    sectors_exempt: int
    error_count: int
    warning_count: int
    info_count: int
    issues: list[AuditIssue]
    sector_coverages: list[SectorCoverage]
    orphan_stocks: list[dict]
    overbroad_stocks: list[dict]

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "total_listed": self.total_listed,
            "total_pending": self.total_pending,
            "total_reference": self.total_reference,
            "total_sectors": self.total_sectors,
            "sectors_with_coverage": self.sectors_with_coverage,
            "sectors_missing": self.sectors_missing,
            "sectors_thin": self.sectors_thin,
            "sectors_exempt": self.sectors_exempt,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [i.to_dict() for i in self.issues],
            "sector_coverages": [
                {
                    "sector_id": sc.sector_id,
                    "sector_name": sc.sector_name,
                    "priority": sc.priority,
                    "scoring_enabled": sc.scoring_enabled,
                    "is_observation_only": sc.is_observation_only,
                    "listed_count": sc.listed_count,
                    "pending_count": sc.pending_count,
                    "reference_count": sc.reference_count,
                    "coverage_status": sc.coverage_status,
                    "listed_stocks": [s.get("name", "?") for s in sc.listed_stocks],
                    "pending_stocks": [s.get("name", "?") for s in sc.pending_stocks],
                    "issues": [i.to_dict() for i in sc.issues],
                }
                for sc in self.sector_coverages
            ],
            "orphan_stocks": [s.get("name", "?") for s in self.orphan_stocks],
            "overbroad_stocks": [
                {"name": s.get("name", "?"), "code": s.get("code", ""), "sectors": s.get("sectors", [])}
                for s in self.overbroad_stocks
            ],
        }


# ── YAML loading ─────────────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


# ── Core audit logic ──────────────────────────────────────────────────────────

STOCK_CODE_PATTERN = re.compile(r"^\d{6}\.(SH|SZ|BJ)$")


def run_audit(
    project_id: str,
    *,
    include_pending: bool = False,
) -> AuditResult:
    project_dir = PROJECTS_ROOT / project_id
    stock_yaml = load_yaml(project_dir / "stock_universe.yaml")
    sector_yaml = load_yaml(project_dir / "sector_universe.yaml")
    manifest_yaml = load_yaml(project_dir / "run_manifest.yaml")

    stocks_raw = stock_yaml.get("stocks", [])
    pending_raw = stock_yaml.get("pending_code_resolution", [])
    reference_raw = stock_yaml.get("reference_companies", [])
    sectors_raw = sector_yaml.get("sectors", [])
    research_groups_raw = sector_yaml.get("research_groups", [])

    # Build valid sector_id set
    valid_sector_ids = {s["sector_id"] for s in sectors_raw if s.get("sector_id")}

    # Build observation_only set
    observation_group_ids = {"peripheral_observation"}
    observation_sector_ids = {
        s["sector_id"] for s in sectors_raw
        if s.get("research_group_id") in observation_group_ids
    }

    # Build sector -> [stock_names] map (listed)
    sector_listed_map: dict[str, list[dict]] = defaultdict(list)
    # Build stock -> [sector_ids] map (for orphan/overbroad checks)
    stock_sector_map: dict[str, list[str]] = defaultdict(list)

    issues: list[AuditIssue] = []

    # ── Pass 1: Listed stocks ───────────────────────────────────────────────
    seen_codes: dict[str, str] = {}
    seen_names: dict[str, str] = {}

    for stk in stocks_raw:
        code = stk.get("code", "")
        name = stk.get("name", "?")
        raw_sectors = stk.get("sectors", []) or stk.get("sector_ids", []) or []

        # Validate code format
        if code and not STOCK_CODE_PATTERN.match(code):
            issues.append(AuditIssue(
                severity="ERROR",
                code="MALFORMED_STOCK_CODE",
                sector_id="",
                stock_name=name,
                stock_code=code,
                message=f"Stock code '{code}' does not match pattern ^\\d{{6}}\\.(SH|SZ|BJ)$. "
                        f"Use full exchange suffix (e.g. 300308.SZ).",
            ))

        # Duplicate code check
        if code and code in seen_codes:
            issues.append(AuditIssue(
                severity="ERROR",
                code="DUPLICATE_STOCK_CODE",
                sector_id="",
                stock_name=name,
                stock_code=code,
                message=f"Stock code '{code}' appears twice: first='{seen_codes[code]}', "
                        f"second='{name}'. Codes must be unique.",
            ))
        elif code:
            seen_codes[code] = name

        # Duplicate name check
        if name in seen_names and name not in ("?", ""):
            issues.append(AuditIssue(
                severity="WARNING",
                code="DUPLICATE_STOCK_NAME",
                sector_id="",
                stock_name=name,
                stock_code=code,
                message=f"Stock name '{name}' appears multiple times (code '{code}' and "
                        f"'{seen_names[name]}'). Verify these are distinct companies.",
            ))
        else:
            seen_names[name] = code

        # Invalid sector refs
        for sid in raw_sectors:
            if sid not in valid_sector_ids:
                issues.append(AuditIssue(
                    severity="ERROR",
                    code="STOCK_BAD_SECTOR_REF",
                    sector_id=str(sid),
                    stock_name=name,
                    stock_code=code,
                    message=f"Stock '{name}' (code={code}) references sector_id='{sid}' "
                            f"which does not exist in sector_universe.yaml.",
                ))

        # Track sector coverage
        for sid in raw_sectors:
            if sid in valid_sector_ids and code:
                sector_listed_map[sid].append(stk)
                stock_sector_map[code].append(sid)

    # ── Pass 2: Pending stocks ──────────────────────────────────────────────
    seen_pending_names: dict[str, str] = {}
    for pen in pending_raw:
        name = pen.get("name", "?")
        raw_sectors = pen.get("suggested_sectors", [])

        # Duplicate name check (within pending)
        if name in seen_pending_names:
            issues.append(AuditIssue(
                severity="WARNING",
                code="DUPLICATE_PENDING_NAME",
                sector_id="",
                stock_name=name,
                stock_code="",
                message=f"pending_code_resolution contains '{name}' multiple times. "
                        f"Remove duplicate entry.",
            ))
        else:
            seen_pending_names[name] = name

        # Invalid sector refs in pending
        for sid in raw_sectors:
            if sid not in valid_sector_ids:
                issues.append(AuditIssue(
                    severity="ERROR",
                    code="PENDING_BAD_SECTOR_REF",
                    sector_id=str(sid),
                    stock_name=name,
                    stock_code="",
                    message=f"pending_code_resolution '{name}' references sector_id='{sid}' "
                            f"which does not exist in sector_universe.yaml.",
                ))

        # Track sector coverage
        for sid in raw_sectors:
            if sid in valid_sector_ids:
                stock_sector_map[f"__pending:{name}"].append(sid)

    # ── Pass 3: Sector-by-sector coverage ───────────────────────────────────
    sector_coverages: list[SectorCoverage] = []

    for s in sectors_raw:
        sid = s["sector_id"]
        is_obs = sid in observation_sector_ids
        priority = s.get("priority", "P9")
        scoring = s.get("scoring_enabled", False)

        listed = sector_listed_map.get(sid, [])
        # Count pending that reference this sector
        pending = [
            p for p in pending_raw
            if sid in p.get("suggested_sectors", [])
        ]
        # Reference companies for this sector
        ref_count = sum(
            1 for r in reference_raw
            if sid in r.get("related_sectors", [])
        )

        # Determine coverage status
        if is_obs:
            status = "exempt"
        elif len(listed) == 0:
            status = "missing"
        elif priority in ("P0", "P1") and len(listed) < P0_P1_MIN_LISTED:
            status = "thin"
            if len(pending) > 0:
                issues.append(AuditIssue(
                    severity="WARNING",
                    code="P0_P1_THIN_COVERAGE",
                    sector_id=sid,
                    message=f"Sector '{sid}' is P0/P1 but has only {len(listed)} listed stock(s) "
                            f"(need >= {P0_P1_MIN_LISTED}). {len(pending)} pending candidate(s) available "
                            f"(see pending_code_resolution).",
                ))
            else:
                issues.append(AuditIssue(
                    severity="WARNING",
                    code="P0_P1_THIN_COVERAGE",
                    sector_id=sid,
                    message=f"Sector '{sid}' is P0/P1 but has only {len(listed)} listed stock(s) "
                            f"(need >= {P0_P1_MIN_LISTED}). No pending candidates found.",
                ))
        elif scoring and len(listed) < P2_P3_MIN_LISTED:
            status = "thin"
            issues.append(AuditIssue(
                severity="WARNING",
                code="SCORING_THIN_COVERAGE",
                sector_id=sid,
                message=f"Sector '{sid}' is scoring_enabled but has only {len(listed)} listed stock(s) "
                        f"(need >= {P2_P3_MIN_LISTED}).",
            ))
        elif not scoring and not is_obs and len(listed) < P2_P3_MIN_LISTED:
            status = "thin"
            issues.append(AuditIssue(
                severity="INFO",
                code="SECTOR_THIN_COVERAGE",
                sector_id=sid,
                message=f"Sector '{sid}' has only {len(listed)} listed stock(s) "
                        f"(threshold: {P2_P3_MIN_LISTED}).",
            ))
        else:
            status = "ok"

        sc_issues = [
            i for i in issues
            if i.sector_id == sid
        ]
        sector_coverages.append(SectorCoverage(
            sector_id=sid,
            sector_name=s.get("sector_name", sid),
            priority=priority,
            scoring_enabled=scoring,
            is_observation_only=is_obs,
            listed_count=len(listed),
            pending_count=len(pending),
            reference_count=ref_count,
            coverage_status=status,
            listed_stocks=listed,
            pending_stocks=pending,
            issues=sc_issues,
        ))

    # ── Pass 4: Orphan stocks (no sector reference) ─────────────────────────
    orphan_stocks = [
        stk for stk in stocks_raw
        if not (stk.get("sectors", []) or stk.get("sector_ids", []))
    ]
    for stk in orphan_stocks:
        issues.append(AuditIssue(
            severity="WARNING",
            code="ORPHAN_STOCK",
            sector_id="",
            stock_name=stk.get("name", "?"),
            stock_code=stk.get("code", ""),
            message=f"Stock '{stk.get('name', '?')}' (code={stk.get('code', '')}) "
                    f"has no sector references (empty sectors[]). Add at least one sector_id.",
        ))

    # ── Pass 5: Over-broad stocks (>3 sectors) ─────────────────────────────
    overbroad_stocks = []
    for stk in stocks_raw:
        code = stk.get("code", "")
        raw_sectors = stk.get("sectors", []) or stk.get("sector_ids", [])
        valid_sectors = [s for s in raw_sectors if s in valid_sector_ids]
        if len(valid_sectors) > 3:
            overbroad_stocks.append(stk)
            issues.append(AuditIssue(
                severity="WARNING",
                code="OVERBROAD_STOCK",
                sector_id="",
                stock_name=stk.get("name", "?"),
                stock_code=code,
                message=f"Stock '{stk.get('name', '?')}' (code={code}) references {len(valid_sectors)} sectors: "
                        f"{valid_sectors}. Manually verify this is correct and not "
                        f"accidentally over-classified.",
            ))

    # ── Summary counts ──────────────────────────────────────────────────────
    sectors_missing = sum(1 for sc in sector_coverages if sc.coverage_status == "missing")
    sectors_thin = sum(1 for sc in sector_coverages if sc.coverage_status == "thin")
    sectors_exempt = sum(1 for sc in sector_coverages if sc.coverage_status == "exempt")
    sectors_with_coverage = sum(1 for sc in sector_coverages if sc.coverage_status == "ok")

    total_listed = len(stocks_raw)
    total_pending = len(pending_raw)
    total_reference = len(reference_raw)

    return AuditResult(
        project_id=project_id,
        total_listed=total_listed,
        total_pending=total_pending,
        total_reference=total_reference,
        total_sectors=len(sectors_raw),
        sectors_with_coverage=sectors_with_coverage,
        sectors_missing=sectors_missing,
        sectors_thin=sectors_thin,
        sectors_exempt=sectors_exempt,
        error_count=sum(1 for i in issues if i.severity == "ERROR"),
        warning_count=sum(1 for i in issues if i.severity == "WARNING"),
        info_count=sum(1 for i in issues if i.severity == "INFO"),
        issues=issues,
        sector_coverages=sector_coverages,
        orphan_stocks=orphan_stocks,
        overbroad_stocks=overbroad_stocks,
    )


# ── Output formatting ────────────────────────────────────────────────────────

def print_audit_report(result: AuditResult) -> None:
    print("=" * 72)
    print(f" Stock Universe Coverage Audit — {result.project_id}")
    print("=" * 72)

    print(f"\n  Universe status: seed_pool / incomplete")
    print(f"  Total sectors  : {result.total_sectors}")
    print(f"  Listed stocks  : {result.total_listed}")
    print(f"  Pending stocks : {result.total_pending}")
    print(f"  Reference cos  : {result.total_reference}")

    print(f"\n  Coverage summary:")
    print(f"    ok      : {result.sectors_with_coverage} sectors")
    print(f"    thin    : {result.sectors_thin} sectors")
    print(f"    missing : {result.sectors_missing} sectors")
    print(f"    exempt  : {result.sectors_exempt} sectors")

    p0_p1 = [sc for sc in result.sector_coverages if sc.priority in ("P0", "P1")]
    p0_p1_ok = [sc for sc in p0_p1 if sc.coverage_status == "ok"]
    p0_p1_thin = [sc for sc in p0_p1 if sc.coverage_status == "thin"]
    p0_p1_missing = [sc for sc in p0_p1 if sc.coverage_status == "missing"]
    promoted_count = sum(
        1
        for sc in result.sector_coverages
        for stk in sc.listed_stocks
        if stk.get("source") == "promoted_from_pending_1E_c_b"
    )
    duplicate_errors = [i for i in result.issues if i.code in ("DUPLICATE_STOCK_CODE", "DUPLICATE_STOCK_NAME")]
    invalid_ref_errors = [i for i in result.issues if i.code in ("STOCK_BAD_SECTOR_REF", "PENDING_BAD_SECTOR_REF")]

    print(f"\n  P0/P1 coverage summary:")
    print(f"    reached_threshold : {len(p0_p1_ok)} sectors")
    print(f"    still_thin        : {len(p0_p1_thin)} sectors")
    print(f"    still_missing     : {len(p0_p1_missing)} sectors")
    print(f"    promoted_from_pending_1E_c_b: {promoted_count} stock-sector link(s)")
    if p0_p1_ok:
        print("    sectors_reached_threshold:")
        for sc in sorted(p0_p1_ok, key=lambda x: (x.priority, x.sector_id)):
            print(f"      [{sc.priority}] {sc.sector_id} ({sc.listed_count} listed)")
    if p0_p1_thin:
        print("    sectors_still_thin:")
        for sc in sorted(p0_p1_thin, key=lambda x: (x.priority, x.sector_id)):
            print(f"      [{sc.priority}] {sc.sector_id} ({sc.listed_count} listed, {sc.pending_count} pending)")
    if p0_p1_missing:
        print("    sectors_still_missing:")
        for sc in sorted(p0_p1_missing, key=lambda x: (x.priority, x.sector_id)):
            print(f"      [{sc.priority}] {sc.sector_id} ({sc.pending_count} pending)")
    print(f"    duplicate code/name issues : {len(duplicate_errors)}")
    print(f"    invalid sector ref issues : {len(invalid_ref_errors)}")
    print(f"    over-broad stocks         : {len(result.overbroad_stocks)}")

    pending_by_sector = [
        sc for sc in result.sector_coverages
        if sc.pending_stocks
    ]
    if pending_by_sector:
        print(f"\n  Pending candidates by sector:")
        for sc in sorted(pending_by_sector, key=lambda x: (x.priority, x.sector_id)):
            names = ", ".join(p.get("name", "?") for p in sc.pending_stocks)
            print(f"    [{sc.priority}] {sc.sector_id}: {names}")

    # ── Sector table ─────────────────────────────────────────────────────────
    print(f"\n{'─' * 72}")
    print(f" Per-sector stock coverage:")
    print(f"  {'Priority':<6} {'Sector ID':<42} {'Listed':>6} {'Pending':>7} {'Status':<9}")
    print(f"  {'─'*6} {'─'*42} {'─'*6} {'─'*7} {'─'*9}")

    for sc in sorted(result.sector_coverages, key=lambda x: (x.priority, x.sector_id)):
        status_label = f"[{sc.coverage_status}]"
        print(f"  {sc.priority:<6} {sc.sector_id:<42} {sc.listed_count:>6} {sc.pending_count:>7} {status_label:<9}")

    # ── P0/P1 thin coverage detail ────────────────────────────────────────────
    p0_p1_thin = [sc for sc in result.sector_coverages
                   if sc.priority in ("P0", "P1") and sc.listed_count < P0_P1_MIN_LISTED]
    if p0_p1_thin:
        print(f"\n{'─' * 72}")
        print(f" P0/P1 coverage below threshold (<{P0_P1_MIN_LISTED} listed stocks):")
        for sc in sorted(p0_p1_thin, key=lambda x: x.priority):
            names = [s.get("name", "?") for s in sc.listed_stocks]
            pending_names = [s.get("name", "?") for s in sc.pending_stocks]
            print(f"  [{sc.priority}] {sc.sector_id}")
            print(f"    Listed: {', '.join(names) if names else '(none)'}")
            if pending_names:
                print(f"    Pending: {', '.join(pending_names)}")
            print(f"    Gap: need {P0_P1_MIN_LISTED - sc.listed_count} more listed stocks")

    # ── All issues ────────────────────────────────────────────────────────────
    if result.issues:
        print(f"\n{'─' * 72}")
        print(f" Issues ({len(result.issues)} total):")
        for sev in ("ERROR", "WARNING", "INFO"):
            items = [i for i in result.issues if i.severity == sev]
            if not items:
                continue
            print(f"\n  [{sev}] ({len(items)})")
            by_code: dict = defaultdict(list)
            for i in items:
                by_code[i.code].append(i)
            for code, items_list in by_code.items():
                first = items_list[0]
                extra = f" (+{len(items_list)-1} similar)" if len(items_list) > 1 else ""
                print(f"    [{code}] {first.message}{extra}")

    # ── Summary counts ────────────────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print(f" Counts:")
    print(f"   ERROR  : {result.error_count}")
    print(f"   WARNING: {result.warning_count}")
    print(f"   INFO   : {result.info_count}")

    print(f"\n{'=' * 72}")
    if result.error_count > 0:
        print(f" RESULT: FAILED — {result.error_count} ERROR(s) found.")
        print(f"         Errors must be fixed before entering 1E-c-b.")
    elif result.warning_count > 0:
        print(f" RESULT: PASSED with warnings — stock_universe is seed_pool/incomplete.")
        print(f"         WARNING(s) are expected; no ERRORs.")
        print(f"         Do NOT enter formal research production until coverage improves.")
    else:
        print(f" RESULT: PASSED — no issues found.")
    print()


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit stock_universe.yaml coverage and integrity.",
        epilog=(
            "Examples:\n"
            "  python .codex/skills/quality-auditor/scripts/cli.py stock-universe "
            "--project tech_ai_semiconductor\n"
            "  python .codex/skills/quality-auditor/scripts/cli.py stock-universe "
            "--project tech_ai_semiconductor --json\n"
            "  python .codex/skills/quality-auditor/scripts/cli.py stock-universe "
            "--project tech_ai_semiconductor --include-pending\n"
        ),
    )
    parser.add_argument("--project", default="tech_ai_semiconductor")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--include-pending",
        action="store_true",
        help="Count pending_code_resolution stocks as coverage (informational)",
    )
    args = parser.parse_args()

    try:
        result = run_audit(args.project, include_pending=args.include_pending)
    except Exception as exc:
        print(f"[ERROR] Audit failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_audit_report(result)

    return 0 if result.error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
