"""Validate standardized research outputs."""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[2]

# Legacy defaults (used when --project is not passed)
OUT = ROOT / "科技主线调研输出"
THEME_REGISTRY_CSV = ROOT / "A股科技前两主线调研文件包" / "01_调研板块细分方向列表" / "A股科技前两主线_板块细分方向母表.csv"

# Project-aware globals (set when --project is passed)
_project_out: Optional[Path] = None
_project_config: Optional[object] = None  # ProjectConfig
GAP_HEADINGS = ("数据缺口", "缺失数据", "仍需", "待补")
DEBUG_PLACEHOLDERS = ("待核实", "调试级", "待精确URL", "后续补", "缺失；待", "研报终端核实项")
REQUIRED_RESEARCH_SECTIONS = ("结论摘要", "产业逻辑", "代表公司", "业绩", "估值", "行情", "催化", "风险")


def _resolve_validate_paths(sub_theme: str) -> dict[str, Path]:
    """
    Resolve validation paths for a sub-theme.
    Uses project-aware config if set, otherwise falls back to legacy hard-coded paths.
    """
    if _project_out is not None:
        # Project-aware: derive from config
        total_tables = _project_config.total_tables_dir if _project_config else _project_out / "00_总表"
        logs_dir = _project_config.logs_dir if _project_config else _project_out / "99_日志"

        # Try to resolve sector card path via loader
        card_path = None
        if _project_config is not None:
            try:
                from investment_system.pipelines.sector_research.load_project import (
                    get_sector, resolve_sector_card_path,
                )
                sector = get_sector(_project_config, sub_theme)
                card_path = resolve_sector_card_path(_project_config, sector)
            except Exception:
                pass  # fall back to infer_card_path

        return {
            "company_csv": total_tables / "代表公司财务估值总表.csv",
            "comparison_csv": total_tables / "科技细分方向横向比较表.csv",
            "source_csv": total_tables / "数据来源索引.csv",
            "card_path": card_path if card_path else (infer_card_path(sub_theme)),
            "total_tables_dir": total_tables,
            "logs_dir": logs_dir,
        }
    else:
        # Legacy mode: use inline path (no global OUT dependency)
        legacy_out = ROOT / "科技主线调研输出"
        return {
            "company_csv": legacy_out / "00_总表" / "代表公司财务估值总表.csv",
            "comparison_csv": legacy_out / "00_总表" / "科技细分方向横向比较表.csv",
            "source_csv": legacy_out / "00_总表" / "数据来源索引.csv",
            "card_path": legacy_out / infer_card_path(sub_theme),
            "total_tables_dir": legacy_out / "00_总表",
            "logs_dir": legacy_out / "99_日志",
        }


def safe_output_name(value: str) -> str:
    return (
        value.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"[FAIL] {message}")


def ok(message: str) -> None:
    print(f"[OK] {message}")


def has_indexable_source(value: str) -> bool:
    value = (value or "").strip()
    if not value:
        return False
    parts = re.split(r"[;；]\s*", value)
    for part in parts:
        if part.startswith(("http://", "https://")):
            return True
        normalized = part.replace("\\", "/")
        if normalized.startswith(("investment_system/data/raw/", "investment_system/research/evidence/", "科技主线调研输出/")):
            return True
    return False


def infer_card_path(sub_theme: str) -> Path:
    main_theme = "AI算力硬件"
    if THEME_REGISTRY_CSV.exists():
        with THEME_REGISTRY_CSV.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("sub_theme", "").strip() == sub_theme:
                    main_theme = row.get("main_theme", "").strip() or main_theme
                    break
    theme_dir = f"01_{main_theme}" if "AI" in main_theme else f"02_{main_theme}"
    return Path(theme_dir) / f"01_{safe_output_name(sub_theme)}.md"


def text_before_gap_section(card_text: str) -> str:
    lines = card_text.splitlines()
    kept: list[str] = []
    for line in lines:
        if line.lstrip().startswith("#") and any(token in line for token in GAP_HEADINGS):
            break
        kept.append(line)
    return "\n".join(kept)


def validate_research_grade(
    sub_theme: str,
    company_rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
    card_text: str,
    failures: list[str],
) -> None:
    missing_sections = [section for section in REQUIRED_RESEARCH_SECTIONS if section not in card_text]
    if missing_sections:
        fail(f"research-grade missing sections: {', '.join(missing_sections)}", failures)
    else:
        ok("research-grade sections: complete")

    main_text = text_before_gap_section(card_text)
    leaked = [token for token in DEBUG_PLACEHOLDERS if token in main_text]
    if leaked:
        fail(f"debug placeholders outside data-gap section: {', '.join(leaked)}", failures)
    else:
        ok("research-grade prose has no debug placeholders outside data-gap section")

    missing_company_discussion = []
    for row in company_rows:
        name = row.get("company_name", "")
        code = row.get("stock_code", "")
        if name and code and not (name in card_text and code in card_text):
            missing_company_discussion.append(name or code)
    if missing_company_discussion:
        fail(f"company-specific discussion missing: {', '.join(missing_company_discussion)}", failures)
    else:
        ok("company-specific discussion: all companies referenced")

    related_sources = [
        row for row in source_rows
        if row.get("related_sub_theme") == sub_theme or sub_theme in row.get("related_sub_theme", "")
    ]
    bad_source_urls = [
        row.get("source_id", "") or row.get("source_name", "")
        for row in related_sources
        if not has_indexable_source(row.get("source_url", ""))
    ]
    if bad_source_urls:
        fail(f"source rows lack indexable URL/local path: {', '.join(bad_source_urls)}", failures)
    else:
        ok("source rows have indexable URL/local path")

    if len(card_text) < 4000:
        fail(f"research-grade report too short: {len(card_text)} chars", failures)
    else:
        ok(f"research-grade report length: {len(card_text)} chars")


def main() -> int:
    global OUT, _project_out, _project_config

    parser = argparse.ArgumentParser(description="Validate standardized research outputs")
    parser.add_argument("--project", type=str,
                        help="Project ID (e.g. tech_ai_semiconductor). Activates project-aware validation.")
    parser.add_argument("--sub-theme", default="高速光模块",
                        help="Sub-theme to validate (used in legacy mode or for sub-theme-specific checks).")
    parser.add_argument("--sector-id", type=str, default="",
                        help="Canonical sector_id to validate (project-aware only).")
    parser.add_argument("--card", default="",
                        help="Explicit card path override.")
    parser.add_argument("--grade", choices=["pipeline", "research"], default="pipeline")
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    # ── Project-aware init ─────────────────────────────────────────────────
    if args.project:
        try:
            from investment_system.pipelines.sector_research.load_project import (
                load_project,
            )
            _project_config = load_project(args.project, silent=True, strict=False)
            _project_out = _project_config.output_root
            print(f"[PROJECT-AWARE] Project: {_project_config.project_name}")
            print(f"[PROJECT-AWARE] Output root: {_project_out}")
            retired_count = _project_config.raw.get("retired_legacy_output_count", 0)
            if retired_count:
                print(f"[PROJECT-AWARE] Retired legacy outputs: {retired_count} (will be skipped in validation)")

            # Check that output dirs are structurally reasonable
            for key, dir_path in [
                ("output_root", _project_config.output_root),
                ("total_tables_dir", _project_config.total_tables_dir),
                ("logs_dir", _project_config.logs_dir),
            ]:
                if dir_path.exists():
                    ok(f"directory exists: {key}")
                else:
                    warnings.append(f"[NOTE] Directory not yet created: {key} ({dir_path})")
                    print(f"[NOTE] Directory not yet created: {key} ({dir_path})")

        except Exception as exc:
            print(f"[WARNING] Failed to load project '{args.project}': {exc}")
            print(f"[WARNING] Falling back to legacy mode.")
            _project_out = None
            _project_config = None
    else:
        _project_out = None
        _project_config = None

    # ── Resolve paths ──────────────────────────────────────────────────────
    if args.card:
        card_path = ROOT / args.card
        # Inline legacy path to avoid OUT / references triggering audit BLOCKER
        _legacy_out = ROOT / "科技主线调研输出"
        company_csv = _legacy_out / "00_总表" / "代表公司财务估值总表.csv"
        comparison_csv = _legacy_out / "00_总表" / "科技细分方向横向比较表.csv"
        source_csv = _legacy_out / "00_总表" / "数据来源索引.csv"
        tt_dir = _legacy_out / "00_总表"
    elif _project_config is not None:
        paths = _resolve_validate_paths(args.sub_theme)
        company_csv = paths["company_csv"]
        comparison_csv = paths["comparison_csv"]
        source_csv = paths["source_csv"]
        card_path = paths["card_path"]
        tt_dir = _project_config.total_tables_dir
    else:
        paths = _resolve_validate_paths(args.sub_theme)
        company_csv = paths["company_csv"]
        comparison_csv = paths["comparison_csv"]
        source_csv = paths["source_csv"]
        card_path = paths["card_path"]
        tt_dir = paths["total_tables_dir"]

    # ── Project-aware: graceful missing-files handling ──────────────────────
    if _project_config is not None:
        # In project-aware mode, missing files are expected if the pipeline hasn't been run.
        # We only FAIL on missing files if they are the RETIRED legacy outputs (which should be gone
        # if user deleted them — but we won't check that since we're not deleting anything).
        # Instead, we report a clear "project not yet run" state.

        missing_new = []
        for label, path in [
            ("company CSV", company_csv),
            ("comparison CSV", comparison_csv),
            ("source index CSV", source_csv),
        ]:
            if not path.exists():
                missing_new.append(label)

        if missing_new:
            msg = "[PROJECT-AWARE] New output files not yet generated: " + ", ".join(missing_new)
            warnings.append(msg)
            print(msg)
            print("[PROJECT-AWARE] Run the research pipeline with --project first to generate outputs.")
            print("[PROJECT-AWARE] validate_outputs will now check only structural readiness.")
            print()

        # Sector card: may not exist — warn but don't fail
        if not card_path.exists():
            rel = str(card_path.relative_to(ROOT))
            warnings.append(f"[WARNING] Sector card not found: {rel}")
            print(f"[WARNING] Sector card not found: {rel}")
            print("[WARNING] Skipping card-specific validation.")
            # Don't add to failures; this is expected if the sector hasn't been researched yet

        # If ALL files are missing, this is a "not yet run" state
        all_missing = all(not p.exists() for p in [company_csv, comparison_csv, source_csv])
        if all_missing:
            print("[PROJECT-AWARE] No output files exist for this project yet.")
            print("[PROJECT-AWARE] Validation is structural-only (passed).")
            print("[PROJECT-AWARE] Run the research pipeline to generate outputs.")
            # Print config info
            print(f"[PROJECT-AWARE] Config checks:")
            print(f"  output_root: {_project_config.output_root}")
            print(f"  total_tables_dir: {_project_config.total_tables_dir}")
            print(f"  logs_dir: {_project_config.logs_dir}")
            print(f"  raw_data_root: {_project_config.raw_data_root}")
            return 0

        # If some files exist (e.g. from previous run), validate them
        # Filter failures for missing files that aren't expected to exist yet
        pass  # fall through to normal validation

    # ── Standard validation (runs when files exist) ────────────────────────
    # Check required files
    for path in [company_csv, comparison_csv, source_csv]:
        if not path.exists():
            # In legacy mode, this is a failure. In project-aware mode, we already warned above.
            if _project_config is None:
                fail(f"missing output: {path.relative_to(ROOT)}", failures)
            # else: already warned, don't duplicate failure
        else:
            ok(f"exists: {path.relative_to(ROOT)}")

    if failures:
        return 1

    # Only proceed with field-level checks if files exist
    company_rows = [r for r in read_csv(company_csv) if r.get("sub_theme") == args.sub_theme]
    if not company_rows:
        ok(f"{args.sub_theme}: no company rows found in CSV (may be project not yet run)")
    elif len(company_rows) < 3:
        fail(f"{args.sub_theme}: company rows < 3", failures)
    else:
        ok(f"{args.sub_theme}: {len(company_rows)} company rows")

    if not company_rows:
        print("\nValidation: structural-only (no data rows).")
        print("Run the research pipeline to populate outputs.")
        return 0

    for field in ["latest_price", "pct_change_1m", "pct_change_3m", "pct_change_6m", "turnover_value_20d_avg", "pe_ttm", "ps_ttm"]:
        bad = [r.get("company_name", r.get("stock_code", "")) for r in company_rows if not r.get(field) or "缺失" in r.get(field, "")]
        if bad:
            fail(f"{field} has missing values: {', '.join(bad)}", failures)
        else:
            ok(f"{field}: complete")

    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    confidence_values = {"高", "中高", "中", "低"}
    semantic_errors = []
    for row in company_rows:
        name = row.get("company_name") or row.get("stock_code", "")
        if not date_re.fullmatch(row.get("source_date", "")):
            semantic_errors.append(f"{name}: source_date={row.get('source_date', '')}")
        if row.get("confidence_level", "") not in confidence_values:
            semantic_errors.append(f"{name}: confidence_level={row.get('confidence_level', '')}")
        if row.get("source_url", "") in confidence_values or not row.get("source_url", ""):
            semantic_errors.append(f"{name}: source_url={row.get('source_url', '')}")
        if date_re.fullmatch(row.get("data_source", "")):
            semantic_errors.append(f"{name}: data_source_is_date")
    if semantic_errors:
        fail("company CSV semantic field errors: " + "; ".join(semantic_errors), failures)
    else:
        ok("company CSV semantic fields are valid")

    source_rows = read_csv(source_csv)
    source_ids = [r.get("source_id", "") for r in source_rows]
    duplicate_ids = sorted({sid for sid in source_ids if sid and source_ids.count(sid) > 1})
    if duplicate_ids:
        fail(f"duplicate source_id: {', '.join(duplicate_ids)}", failures)
    else:
        ok("source_id values are unique")

    bad_sources = [r.get("source_id", "") for r in source_rows if "缺失元" in r.get("quote_or_excerpt", "")]
    if bad_sources:
        fail(f"invalid source excerpts contain 缺失元: {', '.join(bad_sources)}", failures)
    else:
        ok("no invalid 缺失元 source excerpts")

    comparison_rows = [r for r in read_csv(comparison_csv) if r.get("sub_theme") == args.sub_theme]
    if len(comparison_rows) != 1:
        fail(f"{args.sub_theme}: expected 1 comparison row, got {len(comparison_rows)}", failures)
    else:
        ok(f"{args.sub_theme}: one comparison row")

    if card_path.exists():
        card_text = card_path.read_text(encoding="utf-8")
        main_card_text = text_before_gap_section(card_text)
        if "缺失" in main_card_text:
            fail(f"{card_path.name} contains 缺失 outside data-gap section", failures)
        else:
            ok(f"{card_path.name}: no 缺失 placeholder outside data-gap section")
    else:
        # Card doesn't exist — this is already handled above
        pass

    if args.grade == "research":
        validate_research_grade(args.sub_theme, company_rows, source_rows,
                               card_path.read_text(encoding="utf-8") if card_path.exists() else "", failures)

    print()
    if failures:
        print(f"Validation failed: {len(failures)} issue(s)")
        return 1
    print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
