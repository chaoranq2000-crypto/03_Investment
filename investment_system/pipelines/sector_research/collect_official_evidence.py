"""Collect official-source raw evidence into a source manifest.

This helper standardizes the handoff between raw official materials and
evidence YAML authoring. It does not write formal outputs and does not generate
sector cards. The first supported collection mode indexes local files and can
optionally extract PDF text when pdfplumber or pypdf is available.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from investment_system.pipelines.sector_research.load_project import (
    WORKSPACE_ROOT,
    get_sector,
    load_project,
)


SOURCE_TYPE_CODES = {
    "annual_report": "AR",
    "interim_report": "IRPT",
    "quarterly_report": "QR",
    "announcement": "ANN",
    "investor_relations": "IR",
    "exchange_qa": "QA",
    "financial_data": "FIN",
    "market_data": "MKT",
    "data_cache": "CACHE",
}


@dataclass
class SourceRecord:
    source_id: str
    project_id: str
    sector_id: str
    source_type: str
    evidence_level: str
    company_code: str
    company_name: str
    title: str
    publisher: str
    source_date: str
    source_url: str
    local_path: str
    text_path: str
    file_sha256: str
    file_size: int
    access_method: str
    parser: str
    parser_status: str
    metadata_sidecar_key: str
    metadata_missing_fields: list[str]
    notes: str


def _workspace_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()
    except ValueError:
        return str(path)


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", text.upper()).strip("-")
    return value or "UNKNOWN"


def _infer_company_code(path: Path) -> str:
    match = re.search(r"(\d{6}\.(?:SZ|SH|BJ))", path.name, re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _infer_source_type(path: Path, default: str) -> str:
    lower = path.name.lower()
    if "annual_report" in lower or "年度报告" in lower:
        return "annual_report"
    if path.suffix.lower() == ".json" and "tushare" in str(path).lower():
        return "data_cache"
    return default


def _infer_publisher(path: Path, default: str) -> str:
    lower = str(path).lower()
    if "cninfo" in lower:
        return "巨潮资讯/CNINFO"
    if "tushare" in lower:
        return "Tushare Pro"
    return default


def _load_metadata(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    metadata_path = _resolve_path(path)
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _metadata_for(path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    row, _key = _metadata_for_with_key(path, metadata)
    return row


def _metadata_for_with_key(path: Path, metadata: dict[str, Any]) -> tuple[dict[str, Any], str]:
    files = metadata.get("files", metadata) if isinstance(metadata, dict) else {}
    keys = [
        path.name,
        path.as_posix(),
        _workspace_relative(path),
    ]
    for key in keys:
        value = files.get(key) if isinstance(files, dict) else None
        if isinstance(value, dict):
            return value, key
    return {}, ""


def _metadata_required_fields(source_type: str) -> list[str]:
    if source_type in {"annual_report", "interim_report", "quarterly_report", "announcement", "investor_relations", "exchange_qa"}:
        return ["title", "source_date", "company_code", "company_name", "source_url"]
    if source_type in {"financial_data", "market_data", "data_cache"}:
        return ["title", "source_date"]
    return ["title"]


def _missing_metadata_fields(record: dict[str, Any], source_type: str) -> list[str]:
    aliases = {
        "source_date": ["source_date", "date"],
        "source_url": ["source_url", "url"],
    }
    missing: list[str] = []
    for field in _metadata_required_fields(source_type):
        candidates = aliases.get(field, [field])
        if not any(str(record.get(name) or "").strip() for name in candidates):
            missing.append(field)
    return missing


def _discover_files(local_dirs: list[str], local_files: list[str], extensions: list[str]) -> list[Path]:
    wanted = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
    discovered: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        if resolved.suffix.lower() not in wanted:
            return
        seen.add(resolved)
        discovered.append(resolved)

    for raw in local_files:
        path = _resolve_path(raw)
        if path.exists() and path.is_file():
            add(path)

    for raw in local_dirs:
        root = _resolve_path(raw)
        if not root.exists() or not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            if path.is_file():
                add(path)

    return sorted(discovered)


def _is_companion_text(path: Path, all_files: set[Path]) -> bool:
    if path.suffix.lower() not in {".txt", ".md"}:
        return False
    return any((path.with_suffix(ext)).resolve() in all_files for ext in [".pdf", ".PDF"])


def _extract_text_from_pdf(pdf_path: Path) -> tuple[Path, str]:
    text_path = pdf_path.with_suffix(".txt")
    try:
        import pdfplumber  # type: ignore

        parts: list[str] = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                parts.append(f"\n\n--- page {i + 1} ---\n{text}")
        text_path.write_text("".join(parts).strip() + "\n", encoding="utf-8")
        return text_path, "pdfplumber"
    except Exception:
        pass

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            parts.append(f"\n\n--- page {i + 1} ---\n{text}")
        text_path.write_text("".join(parts).strip() + "\n", encoding="utf-8")
        return text_path, "pypdf"
    except Exception as exc:
        raise RuntimeError(f"PDF text extraction failed for {pdf_path}: {exc}") from exc


def _find_text_path(path: Path, extract_pdf_text: bool, write_outputs: bool) -> tuple[str, str, str]:
    if path.suffix.lower() in {".txt", ".md"}:
        return _workspace_relative(path), "existing_text", "ok"
    if path.suffix.lower() != ".pdf":
        return "", "not_applicable", "not_applicable"

    text_path = path.with_suffix(".txt")
    if text_path.exists():
        return _workspace_relative(text_path), "existing_text", "ok"
    if not extract_pdf_text:
        return "", "not_requested", "missing_text"
    if not write_outputs:
        return _workspace_relative(text_path), "planned_pdf_text_extraction", "planned"

    extracted_path, parser = _extract_text_from_pdf(path)
    return _workspace_relative(extracted_path), parser, "ok"


def _source_id(
    *,
    publisher: str,
    source_type: str,
    sector_id: str,
    company_code: str,
    path: Path,
    run_date: str,
) -> str:
    provider = "CNINFO" if "cninfo" in publisher.lower() or "巨潮" in publisher else "LOCAL"
    if "tushare" in publisher.lower():
        provider = "TUSHARE"
    code = SOURCE_TYPE_CODES.get(source_type, "SRC")
    subject = company_code.replace(".", "-") if company_code else _slug(path.stem)[:32]
    return f"{provider}-{code}-{_slug(sector_id)}-{_slug(subject)}-{run_date.replace('-', '')}"


def build_manifest(
    *,
    project_id: str,
    sector_id: str,
    local_dirs: list[str],
    local_files: list[str],
    extensions: list[str],
    source_type: str,
    evidence_level: str,
    publisher: str,
    source_date: str,
    source_set: str,
    metadata: dict[str, Any],
    extract_pdf_text: bool,
    write_outputs: bool,
    run_date: str,
) -> dict[str, Any]:
    config = load_project(project_id, create_dirs=False, strict=False, silent=True)
    canonical_sector_id = get_sector(config, sector_id).get("sector_id", "")
    files = _discover_files(local_dirs, local_files, extensions)
    all_files = {path.resolve() for path in files}
    primary_files = [path for path in files if not _is_companion_text(path, all_files)]

    records: list[SourceRecord] = []
    for path in primary_files:
        meta, metadata_key = _metadata_for_with_key(path, metadata)
        row_source_type = str(meta.get("source_type") or _infer_source_type(path, source_type))
        row_publisher = str(meta.get("publisher") or _infer_publisher(path, publisher))
        row_company_code = str(meta.get("company_code") or _infer_company_code(path))
        row_source_date = str(meta.get("source_date") or meta.get("date") or source_date)
        row_title = str(meta.get("title") or path.stem)
        row_url = str(meta.get("source_url") or meta.get("url") or "")
        row_company_name = str(meta.get("company_name") or "")
        row_evidence_level = str(meta.get("evidence_level") or evidence_level)
        text_path, parser, parser_status = _find_text_path(path, extract_pdf_text, write_outputs)
        records.append(
            SourceRecord(
                source_id=_source_id(
                    publisher=row_publisher,
                    source_type=row_source_type,
                    sector_id=canonical_sector_id,
                    company_code=row_company_code,
                    path=path,
                    run_date=run_date,
                ),
                project_id=project_id,
                sector_id=canonical_sector_id,
                source_type=row_source_type,
                evidence_level=row_evidence_level,
                company_code=row_company_code,
                company_name=row_company_name,
                title=row_title,
                publisher=row_publisher,
                source_date=row_source_date,
                source_url=row_url,
                local_path=_workspace_relative(path),
                text_path=text_path,
                file_sha256=_sha256(path),
                file_size=path.stat().st_size,
                access_method="local_cache",
                parser=parser,
                parser_status=parser_status,
                metadata_sidecar_key=metadata_key,
                metadata_missing_fields=_missing_metadata_fields(
                    {
                        **meta,
                        "title": row_title,
                        "source_date": row_source_date,
                        "company_code": row_company_code,
                        "company_name": row_company_name,
                        "source_url": row_url,
                    },
                    row_source_type,
                ),
                notes=str(meta.get("notes") or f"Collected in source_set={source_set}; not yet converted to evidence YAML."),
            )
        )

    return {
        "manifest_version": "1.0",
        "source_metadata_sidecar_standard": {
            "accepted_lookup_keys": ["file name", "absolute path", "workspace-relative path"],
            "official_source_required_fields": ["title", "source_date", "company_code", "company_name", "source_url"],
            "data_cache_required_fields": ["title", "source_date"],
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "sector_id": canonical_sector_id,
        "source_set": source_set,
        "run_date": run_date,
        "record_count": len(records),
        "records": [asdict(record) for record in records],
    }


def _default_manifest_path(project_id: str, sector_id: str, source_set: str, run_date: str) -> Path:
    safe_source_set = _slug(source_set).lower()
    return (
        WORKSPACE_ROOT
        / "investment_system"
        / "data"
        / "raw"
        / "official_evidence"
        / project_id
        / sector_id
        / run_date
        / f"source_manifest_{sector_id}_{safe_source_set}_{run_date}.json"
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Collect official evidence cache files into a source manifest.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sector-id", required=True)
    parser.add_argument("--local-dir", action="append", default=[])
    parser.add_argument("--local-file", action="append", default=[])
    parser.add_argument("--extensions", default=".pdf,.txt,.md,.json")
    parser.add_argument("--source-type", default="annual_report")
    parser.add_argument("--evidence-level", default="strong")
    parser.add_argument("--publisher", default="")
    parser.add_argument("--source-date", default="")
    parser.add_argument("--source-set", default="official_evidence")
    parser.add_argument("--metadata-json", default=None)
    parser.add_argument("--extract-pdf-text", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--manifest-path", default=None)
    parser.add_argument("--run-date", default=date.today().isoformat())
    args = parser.parse_args(argv)

    if not args.local_dir and not args.local_file:
        print("ERROR: provide at least one --local-dir or --local-file.")
        return 2

    try:
        metadata = _load_metadata(args.metadata_json)
        extensions = [item.strip() for item in args.extensions.split(",") if item.strip()]
        manifest = build_manifest(
            project_id=args.project,
            sector_id=args.sector_id,
            local_dirs=args.local_dir,
            local_files=args.local_file,
            extensions=extensions,
            source_type=args.source_type,
            evidence_level=args.evidence_level,
            publisher=args.publisher,
            source_date=args.source_date,
            source_set=args.source_set,
            metadata=metadata,
            extract_pdf_text=args.extract_pdf_text,
            write_outputs=args.write_manifest,
            run_date=args.run_date,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    manifest_path = _resolve_path(args.manifest_path) if args.manifest_path else _default_manifest_path(
        args.project,
        manifest["sector_id"],
        args.source_set,
        args.run_date,
    )
    if args.write_manifest:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Official evidence source manifest")
    print(f"project_id: {manifest['project_id']}")
    print(f"sector_id: {manifest['sector_id']}")
    print(f"source_set: {manifest['source_set']}")
    print(f"record_count: {manifest['record_count']}")
    print(f"write_manifest: {args.write_manifest}")
    print(f"manifest_path: {manifest_path}")
    for record in manifest["records"]:
        print(f"- {record['source_id']} | {record['source_type']} | {record['local_path']} | parser={record['parser_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
