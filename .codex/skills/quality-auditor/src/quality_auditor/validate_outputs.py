"""Validate project-aware research outputs."""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def read_csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        return next(reader, [])


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"[FAIL] {message}")


def ok(message: str) -> None:
    print(f"[OK] {message}")


def validate_csv_contract(
    output_type: str,
    path: Path,
    contract: dict,
    failures: list[str],
) -> None:
    header = read_csv_header(path)
    required = contract.get("required_fields", []) or []
    missing = [field for field in required if field not in header]
    if missing:
        fail(f"{output_type}: missing required fields: {', '.join(missing)}", failures)
    else:
        ok(f"{output_type}: required fields present")

    if output_type == "company_table":
        for field in ("project_id", "sector_id", "stock_code"):
            if field not in header:
                fail(f"company_table: canonical key missing: {field}", failures)

    if output_type == "sector_comparison_table":
        if "sector_id" not in header:
            fail("sector_comparison_table: canonical sector_id missing", failures)
        score_fields = [field for field in header if field.endswith("_score") and field != "total_score"]
        missing_reasons = [
            field.replace("_score", "_reason")
            for field in score_fields
            if field.replace("_score", "_reason") not in header
        ]
        if missing_reasons:
            fail(f"sector_comparison_table: score reason fields missing: {', '.join(missing_reasons)}", failures)

    if output_type == "source_index" and "source_id" not in header:
        fail("source_index: source_id missing", failures)

    if not failures:
        ok(f"{output_type}: output contract header check passed")


def _inside_formal_output(path: Path, output_root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = output_root.resolve()
    return str(resolved_path).startswith(str(resolved_root))


def _validate_mock_audit_files(project_config: Any, failures: list[str], warnings: list[str]) -> dict[str, int]:
    from research_writer.mock_outputs import (
        CSV_OUTPUT_TYPES,
        MOCK_FILENAMES,
        MOCK_MARKER,
        get_mock_output_dir,
    )
    from investment_system.core.project_loader import get_output_contract

    mock_dir = get_mock_output_dir(project_config)
    checked = 0
    if not mock_dir.exists():
        warnings.append(f"[MOCK] mock audit directory not found: {mock_dir}")
        print(f"[MOCK] mock audit directory not found: {mock_dir}")
        return {"mock_files_checked": 0}

    for output_type in CSV_OUTPUT_TYPES:
        path = mock_dir / MOCK_FILENAMES[output_type]
        if not path.exists():
            warnings.append(f"[MOCK] missing mock file: {path}")
            print(f"[MOCK] missing mock file: {path}")
            continue
        checked += 1
        if _inside_formal_output(path, project_config.output_root):
            fail(f"mock file is inside formal output root: {path}", failures)
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if MOCK_MARKER not in text:
            fail(f"mock file missing marker {MOCK_MARKER}: {path}", failures)
        validate_csv_contract(output_type, path, get_output_contract(project_config, output_type), failures)

    card_path = mock_dir / MOCK_FILENAMES["sector_card"]
    if card_path.exists():
        checked += 1
        if _inside_formal_output(card_path, project_config.output_root):
            fail(f"mock file is inside formal output root: {card_path}", failures)
        card_text = card_path.read_text(encoding="utf-8", errors="ignore")
        for token in ("---", "project_id:", "sector_id:", "source_ids:", "mock_only: true", MOCK_MARKER):
            if token not in card_text:
                fail(f"mock sector_card front matter missing token: {token}", failures)
    else:
        warnings.append(f"[MOCK] missing mock file: {card_path}")
        print(f"[MOCK] missing mock file: {card_path}")

    return {"mock_files_checked": checked}


def _validate_generator_preview_files(project_config: Any, failures: list[str], warnings: list[str]) -> dict[str, int]:
    from investment_system.core.project_loader import get_output_contract
    from research_writer.output_writers import (
        CSV_OUTPUT_TYPES,
        GENERATOR_PREVIEW_FILENAMES,
        PREVIEW_MARKER,
        PREVIEW_RATING,
        get_generator_preview_dir,
    )

    preview_dir = get_generator_preview_dir(project_config)
    checked = 0
    if not preview_dir.exists():
        warnings.append(f"[PREVIEW] generator preview directory not found: {preview_dir}")
        print(f"[PREVIEW] generator preview directory not found: {preview_dir}")
        return {"generator_preview_files_checked": 0}

    for output_type in CSV_OUTPUT_TYPES:
        path = preview_dir / GENERATOR_PREVIEW_FILENAMES[output_type]
        if not path.exists():
            warnings.append(f"[PREVIEW] missing generator preview file: {path}")
            print(f"[PREVIEW] missing generator preview file: {path}")
            continue
        checked += 1
        if _inside_formal_output(path, project_config.output_root):
            fail(f"generator preview file is inside formal output root: {path}", failures)
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if PREVIEW_MARKER not in text:
            fail(f"generator preview file missing marker {PREVIEW_MARKER}: {path}", failures)
        if output_type in {"sector_comparison_table", "score_table"} and PREVIEW_RATING not in text:
            fail(f"generator preview file missing rating {PREVIEW_RATING}: {path}", failures)
        validate_csv_contract(output_type, path, get_output_contract(project_config, output_type), failures)

    card_path = preview_dir / GENERATOR_PREVIEW_FILENAMES["sector_card"]
    if card_path.exists():
        checked += 1
        if _inside_formal_output(card_path, project_config.output_root):
            fail(f"generator preview file is inside formal output root: {card_path}", failures)
        card_text = card_path.read_text(encoding="utf-8", errors="ignore")
        for token in ("---", "project_id:", "sector_id:", "source_ids:", "preview_only: true", PREVIEW_MARKER):
            if token not in card_text:
                fail(f"generator preview sector_card front matter missing token: {token}", failures)
    else:
        warnings.append(f"[PREVIEW] missing generator preview file: {card_path}")
        print(f"[PREVIEW] missing generator preview file: {card_path}")

    if project_config.output_root.exists():
        for path in project_config.output_root.rglob("preview_*"):
            fail(f"generator preview file found in formal output root: {path}", failures)

    return {"generator_preview_files_checked": checked}


def _resolve_card_path(project_config: Any, sector_id: str, explicit_card: str) -> Path | None:
    if explicit_card:
        return ROOT / explicit_card
    if not sector_id:
        return None

    from investment_system.core.project_loader import (
        get_sector,
        resolve_sector_card_path,
    )
    sector = get_sector(project_config, sector_id)
    return resolve_sector_card_path(project_config, sector)


def _validate_log_markers(project_config: Any, failures: list[str]) -> None:
    missing_log = project_config.logs_dir / "缺失数据清单.md"
    conflict_log = project_config.logs_dir / "冲突数据清单.md"
    if missing_log.exists():
        text = missing_log.read_text(encoding="utf-8")
        for token in ("output_type", "sector_id", "missing_field", "severity", "reason"):
            if token not in text:
                fail(f"missing_data_log: required marker missing: {token}", failures)
    if conflict_log.exists():
        text = conflict_log.read_text(encoding="utf-8")
        for token in ("output_type", "sector_id", "field", "conflicting_values", "source_ids"):
            if token not in text:
                fail(f"conflict_data_log: required marker missing: {token}", failures)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate project-aware research outputs")
    parser.add_argument("--project", required=True, help="Project ID, e.g. tech_ai_semiconductor.")
    parser.add_argument(
        "--sector-id",
        default="",
        help="Canonical sector_id to validate. If omitted, checks shared outputs only.",
    )
    parser.add_argument("--card", default="", help="Explicit sector card path override.")
    parser.add_argument(
        "--include-mock-audit-files",
        action="store_true",
        help="Also validate audits/mock_outputs files without treating them as formal outputs.",
    )
    parser.add_argument(
        "--include-generator-previews",
        action="store_true",
        help="Also validate audits/generator_previews files without treating them as formal outputs.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    try:
        from investment_system.core.project_loader import (
            get_output_contract,
            list_output_types,
            load_project,
        )
        project_config = load_project(args.project, silent=True, strict=False)
    except Exception as exc:
        print(f"[ERROR] Failed to load project '{args.project}': {exc}")
        return 1

    print(f"[PROJECT-AWARE] Project: {project_config.project_name}")
    print(f"[PROJECT-AWARE] Output root: {project_config.output_root}")
    print(f"[PROJECT-AWARE] Output contract loaded: {len(list_output_types(project_config))} output types")
    retired_count = project_config.raw.get("retired_output_count", 0)
    if retired_count:
        print(f"[PROJECT-AWARE] Retired historical outputs: {retired_count} (skipped in validation)")

    for key, dir_path in [
        ("output_root", project_config.output_root),
        ("total_tables_dir", project_config.total_tables_dir),
        ("logs_dir", project_config.logs_dir),
    ]:
        if dir_path.exists():
            ok(f"directory exists: {key}")
        else:
            warnings.append(f"[NOTE] Directory not yet created: {key} ({dir_path})")
            print(f"[NOTE] Directory not yet created: {key} ({dir_path})")

    company_csv = project_config.total_tables_dir / "代表公司财务估值总表.csv"
    comparison_csv = project_config.total_tables_dir / "科技细分方向横向比较表.csv"
    source_csv = project_config.total_tables_dir / "数据来源索引.csv"
    card_path = _resolve_card_path(project_config, args.sector_id, args.card)

    missing_outputs = []
    for label, path in [
        ("company CSV", company_csv),
        ("comparison CSV", comparison_csv),
        ("source index CSV", source_csv),
    ]:
        if path.exists():
            ok(f"exists: {path.relative_to(ROOT)}")
        else:
            missing_outputs.append(label)

    if missing_outputs:
        msg = "[PROJECT-AWARE] Formal output files not yet generated: " + ", ".join(missing_outputs)
        warnings.append(msg)
        print(msg)

    if card_path is None:
        print("[PROJECT-AWARE] No --sector-id provided; skipping sector-card-specific validation.")
    elif card_path.exists():
        ok(f"exists: {card_path.relative_to(ROOT)}")
    else:
        warnings.append(f"[WARNING] Sector card not found: {card_path}")
        print(f"[WARNING] Sector card not found: {card_path}")

    contract_files = [
        ("company_table", company_csv),
        ("sector_comparison_table", comparison_csv),
        ("source_index", source_csv),
    ]
    for output_type, path in contract_files:
        if path.exists():
            validate_csv_contract(output_type, path, get_output_contract(project_config, output_type), failures)

    _validate_log_markers(project_config, failures)

    mock_stats = {"mock_files_checked": 0}
    preview_stats = {"generator_preview_files_checked": 0}
    if args.include_mock_audit_files:
        print("[PROJECT-AWARE] Checking mock audit files only under audits/mock_outputs.")
        mock_stats = _validate_mock_audit_files(project_config, failures, warnings)
    if args.include_generator_previews:
        print("[PROJECT-AWARE] Checking generator previews only under audits/generator_previews.")
        preview_stats = _validate_generator_preview_files(project_config, failures, warnings)

    formal_found = sum(1 for path in [company_csv, comparison_csv, source_csv] if path.exists())
    print(f"[PROJECT-AWARE] mock_files_checked: {mock_stats['mock_files_checked']}")
    print(f"[PROJECT-AWARE] generator_preview_files_checked: {preview_stats['generator_preview_files_checked']}")
    print(f"[PROJECT-AWARE] formal_outputs_checked: {formal_found}")
    print(f"[PROJECT-AWARE] formal_outputs_found: {formal_found}")
    print(f"[PROJECT-AWARE] warnings: {len(warnings)}")

    if failures:
        print(f"Validation failed: {len(failures)} issue(s)")
        return 1

    print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
