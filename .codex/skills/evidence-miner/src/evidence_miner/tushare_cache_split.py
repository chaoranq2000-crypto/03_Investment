"""Split a bundled Tushare cache into dataset-level source manifest records."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from investment_system.core.project_loader import WORKSPACE_ROOT, get_sector, load_project


DATASET_SOURCE_TYPES = {
    "income": "financial_data",
    "balancesheet": "financial_data",
    "cashflow": "financial_data",
    "daily_basic": "market_data",
    "daily": "market_data",
}


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _workspace_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()
    except ValueError:
        return str(path)


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text.upper()).strip("-") or "UNKNOWN"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dataset_names(cache: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for payload in cache.values():
        if isinstance(payload, dict):
            names.update(str(key) for key in payload)
    return sorted(names)


def _dataset_payload(cache: dict[str, Any], dataset: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for stock_code, payload in cache.items():
        if isinstance(payload, dict) and dataset in payload:
            result[str(stock_code)] = payload[dataset]
    return result


def _record(
    *,
    project_id: str,
    sector_id: str,
    dataset: str,
    output_path: Path,
    payload_bytes: bytes,
    run_date: str,
    source_date: str,
    original_cache_path: Path,
) -> dict[str, Any]:
    compact_date = run_date.replace("-", "")
    return {
        "source_id": f"TUSHARE-CACHE-{_slug(sector_id)}-{_slug(dataset)}-{compact_date}",
        "project_id": project_id,
        "sector_id": sector_id,
        "source_type": DATASET_SOURCE_TYPES.get(dataset, "data_cache"),
        "evidence_level": "strong",
        "company_code": "",
        "company_name": "",
        "title": f"Tushare {dataset} cache split for {sector_id}",
        "publisher": "Tushare Pro",
        "source_date": source_date or run_date,
        "source_url": "",
        "local_path": _workspace_relative(output_path),
        "text_path": "",
        "file_sha256": _sha256_bytes(payload_bytes),
        "file_size": len(payload_bytes),
        "access_method": "local_cache",
        "parser": "json_splitter",
        "parser_status": "ok",
        "metadata_sidecar_key": dataset,
        "metadata_missing_fields": [],
        "notes": (
            f"Split from {_workspace_relative(original_cache_path)} dataset={dataset}. "
            "Use evidence_draft before manual curation into active evidence."
        ),
    }


def build_split_manifest(
    *,
    project_id: str,
    sector_id: str,
    cache_path: Path,
    output_dir: Path,
    run_date: str,
    source_date: str,
    write_split: bool,
) -> tuple[dict[str, Any], list[tuple[Path, bytes]]]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    canonical_sector_id = str(get_sector(config, sector_id).get("sector_id") or sector_id)
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(cache, dict):
        raise ValueError(f"Tushare cache must be a JSON object keyed by stock code: {cache_path}")

    files_to_write: list[tuple[Path, bytes]] = []
    records: list[dict[str, Any]] = []
    for dataset in _dataset_names(cache):
        payload = _dataset_payload(cache, dataset)
        if not payload:
            continue
        output_path = output_dir / f"{cache_path.stem}_{dataset}.json"
        payload_bytes = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if write_split:
            files_to_write.append((output_path, payload_bytes))
        records.append(
            _record(
                project_id=project_id,
                sector_id=canonical_sector_id,
                dataset=dataset,
                output_path=output_path,
                payload_bytes=payload_bytes,
                run_date=run_date,
                source_date=source_date,
                original_cache_path=cache_path,
            )
        )

    manifest = {
        "manifest_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "sector_id": canonical_sector_id,
        "source_set": "tushare_cache_split",
        "run_date": run_date,
        "original_cache_path": _workspace_relative(cache_path),
        "record_count": len(records),
        "records": records,
    }
    return manifest, files_to_write


def _default_output_dir(project_id: str, sector_id: str, run_date: str) -> Path:
    return WORKSPACE_ROOT / "investment_system" / "data" / "raw" / "tushare" / "cache_splits" / project_id / sector_id / run_date


def _default_manifest_path(output_dir: Path, sector_id: str, run_date: str) -> Path:
    return output_dir / f"source_manifest_{sector_id}_tushare_cache_split_{run_date}.json"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Split a bundled Tushare JSON cache into dataset-level source records.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--cache-path", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--manifest-path", default="")
    parser.add_argument("--run-date", default=date.today().isoformat())
    parser.add_argument("--source-date", default="")
    parser.add_argument("--write-split", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args(argv)

    try:
        cache_path = _resolve_path(args.cache_path)
        output_dir = _resolve_path(args.output_dir) if args.output_dir else _default_output_dir(args.project, args.sector_id, args.run_date)
        manifest_path = _resolve_path(args.manifest_path) if args.manifest_path else _default_manifest_path(output_dir, args.sector_id, args.run_date)
        manifest, files_to_write = build_split_manifest(
            project_id=args.project,
            sector_id=args.sector_id,
            cache_path=cache_path,
            output_dir=output_dir,
            run_date=args.run_date,
            source_date=args.source_date,
            write_split=args.write_split,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.write_split:
        output_dir.mkdir(parents=True, exist_ok=True)
        for path, payload in files_to_write:
            path.write_bytes(payload)
    if args.write_manifest:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Tushare cache split manifest")
    print(f"project_id: {manifest['project_id']}")
    print(f"sector_id: {manifest['sector_id']}")
    print(f"record_count: {manifest['record_count']}")
    print(f"write_split: {args.write_split}")
    print(f"write_manifest: {args.write_manifest}")
    print(f"manifest_path: {manifest_path}")
    for record in manifest["records"]:
        print(f"- {record['source_id']} | {record['source_type']} | {record['local_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
