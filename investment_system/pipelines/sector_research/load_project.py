"""
Project Loader for Sector Research Workspace.

Loads and validates a project configuration directory, returning a structured
dict with all project metadata. Used as the single entry point for all
project-aware pipeline scripts.

Usage (CLI):
    python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor
    python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --dry-run-paths
    python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --json
    python -m investment_system.pipelines.sector_research.load_project --project tech_ai_semiconductor --create-output-dirs

Usage (library):
    from investment_system.pipelines.sector_research.load_project import load_project, get_sector, list_scoring_sectors, get_stocks_for_sector, resolve_evidence_files_for_sector, resolve_output_paths
    config = load_project("tech_ai_semiconductor")
    # Access raw config:
    sectors = config.raw["sectors"]
    stocks  = config.raw["stock_universe"]

Exit codes:
    0  success, no warnings
    1  project not found
    2  validation error (error-severity issues found)
    3  warning (project loaded but with warnings)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# ── Constants ────────────────────────────────────────────────────────────────

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
PROJECTS_ROOT = WORKSPACE_ROOT / "investment_system" / "research" / "projects"
SCHEMAS_ROOT = WORKSPACE_ROOT / "investment_system" / "research" / "schemas"

REQUIRED_PROJECT_FILES = [
    "project.yaml",
    "sector_universe.yaml",
    "stock_universe.yaml",
    "scoring_rules.yaml",
    "output_spec.yaml",
    "run_manifest.yaml",
]

REQUIRED_OUTPUT_SPEC_FIELDS = [
    "directories",
    "company_table_fields",
    "comparison_table_fields",
    "source_index_fields",
]

SEED_FORBIDDEN_STATUSES = frozenset({
    "completed", "research-grade", "sector_card",
    "verified", "research",
})
SEED_FORBIDDEN_TYPES = frozenset({"sector_card", "company_financial_valuation_table"})
SEED_FORBIDDEN_ACTIONS = frozenset({"expand_into_sector_universe", "generated", "pending"})
STOCK_CODE_PATTERN = re.compile(r"^\d{6}\.(SH|SZ|BJ)$")
AI_APP_FORBIDDEN_PARENTCHAINS = frozenset({"AI算力硬件", "AI算力基础设施"})

# Directories excluded from unregistered MD scan
MD_SCAN_EXCLUDE_DIRS = frozenset({
    "docs", "templates", "schemas", ".git", ".conda",
    "node_modules", "__pycache__", ".codex",
    "projects",  # project config dirs are not sector seeds
    "pipelines", "scripts", "tools", "research",
    "decisions", "risk", "portfolio", "data",
})
# Files excluded from unregistered MD scan
MD_SCAN_EXCLUDE_FILES = frozenset({
    "AGENTS.md", "README.md", "README_CN.md",
    "调研日志.md", "缺失数据清单.md", "冲突数据清单.md",
    "run_manifest.yaml", "project.yaml", "sector_universe.yaml",
    "stock_universe.yaml", "scoring_rules.yaml", "output_spec.yaml",
})

# Seed document mandatory not_allowed_for items
SEED_MANDATORY_NOT_ALLOWED = frozenset({
    "evidence", "score", "rating", "investment_conclusion",
})


# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class ValidationWarning:
    code: str
    message: str
    severity: str = "warning"  # warning | error

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass
class ProjectConfig:
    project_id: str
    project_name: str
    research_type: str
    market: str
    version: str
    output_root: Path
    # ── Clean path fields ──────────────────────────────────────────────
    sector_cards_root: Path          # parent dir containing group sub-dirs
    sector_card_path_template: str   # e.g. "{group_order}_{group_name}/{priority}_{sector_name_safe}.md"
    sector_card_filename_pattern: str  # e.g. "{priority}_{sector_name_safe}.md"
    total_tables_dir: Path
    logs_dir: Path
    raw_data_root: Path
    # Legacy alias (kept for downstream compat)
    sectors_dir: Path               # = sector_cards_root
    # ── Counts ────────────────────────────────────────────────────────
    sector_count: int
    stock_count: int
    scoring_model: str
    weights: dict[str, float]
    quality_grade_target: str
    require_sources: bool
    allow_placeholders: bool
    existing_output_count: int
    seed_document_count: int
    planned_sector_count: int
    warnings: list[ValidationWarning] = field(default_factory=list)
    created_date: str = ""
    python_exe: str = ""
    scope_include: list[str] = field(default_factory=list)
    scope_exclude: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "research_type": self.research_type,
            "market": self.market,
            "version": self.version,
            "created_date": self.created_date,
            # ── Clean path fields ───────────────────────────────────────
            "output_root": str(self.output_root),
            "sector_cards_root": str(self.sector_cards_root),
            "sector_card_path_template": self.sector_card_path_template,
            "sector_card_filename_pattern": self.sector_card_filename_pattern,
            "total_tables_dir": str(self.total_tables_dir),
            "logs_dir": str(self.logs_dir),
            "raw_data_root": str(self.raw_data_root),
            # legacy alias
            "sectors_dir": str(self.sectors_dir),
            # ── Rest ────────────────────────────────────────────────────
            "scoring_model": self.scoring_model,
            "weights": self.weights,
            "quality_grade_target": self.quality_grade_target,
            "require_sources": self.require_sources,
            "allow_placeholders": self.allow_placeholders,
            "sector_count": self.sector_count,
            "stock_count": self.stock_count,
            "planned_sector_count": self.planned_sector_count,
            "existing_output_count": self.existing_output_count,
            "retired_legacy_output_count": self.raw.get("retired_legacy_output_count", 0),
            "seed_document_count": self.seed_document_count,
            "scope_include": self.scope_include,
            "scope_exclude": self.scope_exclude,
            "research_group_count": self.raw.get("research_group_count", 0),
            "scoring_enabled_sector_count": self.raw.get("scoring_enabled_sector_count", 0),
            "observation_only_sector_count": self.raw.get("observation_only_sector_count", 0),
            "listed_stock_count": self.raw.get("listed_stock_count", 0),
            "reference_company_count": self.raw.get("reference_company_count", 0),
            "pending_code_resolution_count": self.raw.get("pending_code_resolution_count", 0),
            "legacy_sector_map": self.raw.get("legacy_sector_map", {}),
            "sector_coverage": self.raw.get("sector_coverage", []),
            "evidence_file_count": self.raw.get("evidence_file_count", 0),
            "evidence_file_warnings": self.raw.get("evidence_file_warnings", []),
            "unregistered_md_warnings": self.raw.get("unregistered_md_warnings", []),
            "sample_sector_card_paths": self.raw.get("sample_sector_card_paths", []),
            "warnings": [w.to_dict() for w in self.warnings],
            "errors": [w.to_dict() for w in self.warnings if w.severity == "error"],
        }
        return d


# ── Path Resolution Utilities ─────────────────────────────────────────────────

def safe_filename(s: str) -> str:
    """Convert a string to a safe filename (ASCII-compatible)."""
    s = s.replace("/", "_").replace("\\", "_")
    s = s.replace(":", "_").replace("*", "_")
    s = s.replace("?", "_").replace('"', "_")
    s = s.replace("<", "_").replace(">", "_")
    s = s.replace("|", "_").replace(" ", "_")
    return s


def resolve_sector_card_path(
    config: ProjectConfig,
    sector_or_id: dict[str, Any] | str,
    output_spec: dict[str, Any] | None = None,
) -> Path:
    """
    Resolve the expected sector card path for a given sector.

    Supports two calling conventions:
      resolve_sector_card_path(config, sector_dict)
      resolve_sector_card_path(config, sector_id_string)

    When called with a sector dict, uses the path_template from output_spec (or config).
    When called with a sector_id string, resolves it via legacy_sector_map first.
    Returns the path WITHOUT creating any files.
    """
    # ── Resolve sector dict ────────────────────────────────────────────
    if isinstance(sector_or_id, str):
        # String: look up via get_sector helper
        sid = sector_or_id
        sector_dict = _get_sector_by_id(config, sid)
        if sector_dict is None:
            raise ValueError(
                f"sector_id '{sid}' not found in sector_universe.yaml "
                f"(checked legacy aliases as well)"
            )
    else:
        sector_dict = sector_or_id
        sid = sector_dict.get("sector_id", "")

    # ── Get output_spec (prefer arg, else from config) ─────────────────
    if output_spec is None:
        output_spec = config.raw.get("output_spec", {})

    # ── Build path ──────────────────────────────────────────────────────
    dirs = output_spec.get("directories", {})
    sc_cfg = dirs.get("sector_cards", {})

    path_template = sc_cfg.get("path_template", "{group_order}_{group_name}")
    filename_pattern = sc_cfg.get(
        "filename_pattern", "{priority}_{sector_name_safe}.md"
    )

    # Resolve group directory
    research_groups = config.raw.get("research_groups", [])
    rg_id = sector_dict.get("research_group_id", "")
    group_order = str(sector_dict.get("group_order", "99"))
    group_name = ""
    for g in research_groups:
        if g.get("group_id") == rg_id:
            group_name = g.get("group_name", "")
            break

    group_dir = (path_template
                 .replace("{group_order}", group_order)
                 .replace("{group_name}", group_name))

    # Resolve filename
    sector_name = sector_dict.get("sector_name", "")
    priority = sector_dict.get("priority", "P9")
    sector_name_safe = safe_filename(sector_name)
    filename = (filename_pattern
                .replace("{priority}", priority)
                .replace("{sector_name_safe}", sector_name_safe))

    return config.sector_cards_root / group_dir / filename


def resolve_output_paths(
    config: ProjectConfig,
    sector_id_or_legacy: str | None = None,
) -> dict[str, Any]:
    """
    Resolve output paths for the whole project or for a specific sector.

    If sector_id_or_legacy is provided, also returns sector_card_path and raw_data_dir.
    Always returns the shared paths (total_tables_dir, logs_dir, source_index, etc.).

    Returns:
        dict with keys: output_root, sector_cards_root, total_tables_dir, logs_dir,
                        raw_data_root, source_index_path, missing_data_log_path,
                        conflict_data_log_path, research_log_path,
                        and optionally (when sector given):
                        sector_card_path, raw_data_dir, sector_id_resolved
    """
    output_spec = config.raw.get("output_spec", {})
    dirs = output_spec.get("directories", {})

    result: dict[str, Any] = {
        "output_root": str(config.output_root),
        "sector_cards_root": str(config.sector_cards_root),
        "total_tables_dir": str(config.total_tables_dir),
        "logs_dir": str(config.logs_dir),
        "raw_data_root": str(config.raw_data_root),
    }

    # Total table files
    tt_cfg = dirs.get("total_tables", {})
    if isinstance(tt_cfg, dict):
        tt_path = tt_cfg.get("path", "00_总表")
        for f in tt_cfg.get("files", []):
            fname = f.get("name", "?")
            result[f"table_{fname}"] = str(config.total_tables_dir / fname)
        result["source_index_path"] = str(config.total_tables_dir / "数据来源索引.csv")
        result["company_table_path"] = str(config.total_tables_dir / "代表公司财务估值总表.csv")
        result["comparison_table_path"] = str(config.total_tables_dir / "科技细分方向横向比较表.csv")

    # Log files
    lg_cfg = dirs.get("logs", {})
    if isinstance(lg_cfg, dict):
        lg_path = lg_cfg.get("path", "99_日志")
        for f in lg_cfg.get("files", []):
            fname = f.get("name", "?")
            result[f"log_{fname}"] = str(config.logs_dir / fname)
        result["missing_data_log_path"] = str(config.logs_dir / "缺失数据清单.md")
        result["conflict_data_log_path"] = str(config.logs_dir / "冲突数据清单.md")
        result["research_log_path"] = str(config.logs_dir / "调研日志.md")

    # Sector-specific paths
    if sector_id_or_legacy:
        sector = _get_sector_by_id(config, sector_id_or_legacy)
        if sector:
            sector_id = sector.get("sector_id", sector_id_or_legacy)
            result["sector_id_resolved"] = sector_id
            result["sector_card_path"] = str(resolve_sector_card_path(config, sector, output_spec))

            # Raw data dir for this sector
            raw_cfg = dirs.get("raw_data", {})
            if isinstance(raw_cfg, dict):
                raw_path_template = raw_cfg.get(
                    "path_template", "00_原始数据/{sector_name_safe}"
                )
                sector_name_safe = safe_filename(sector.get("sector_name", sector_id))
                raw_subdir = raw_path_template.replace(
                    "{sector_name_safe}", sector_name_safe
                )
                result["raw_data_dir"] = str(config.output_root / raw_subdir)

    return result


# ── YAML Helpers ────────────────────────────────────────────────────────────

def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


def get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
    return data


# ── Legacy Sector Map ────────────────────────────────────────────────────────

def build_legacy_sector_map(sectors: list[dict]) -> dict[str, str]:
    """
    Build reverse mapping: legacy_id -> canonical sector_id.
    Collects from legacy_sector_ids[], aliases[], and legacy_theme_names[].
    """
    legacy_map: dict[str, str] = {}
    for s in sectors:
        sid = s.get("sector_id", "")
        for lid in s.get("legacy_sector_ids", []):
            legacy_map[str(lid)] = sid
        for alias in s.get("aliases", []):
            legacy_map[str(alias)] = sid
        for ltn in s.get("legacy_theme_names", []):
            legacy_map[str(ltn)] = sid
    return legacy_map


def resolve_sector_id(
    raw_id: str,
    valid_sector_ids: set[str],
    legacy_map: dict[str, str],
) -> tuple[str, bool]:
    """
    Resolve a sector ID (could be legacy or new).
    Returns (resolved_id, is_legacy).
    """
    if raw_id in valid_sector_ids:
        return raw_id, False
    if raw_id in legacy_map:
        return legacy_map[raw_id], True
    return raw_id, False  # unresolved


def _get_sector_by_id(config: ProjectConfig, sector_id: str) -> dict[str, Any] | None:
    """Internal lookup: try canonical then legacy map."""
    sectors = config.raw.get("sectors", [])
    valid_ids = {s.get("sector_id") for s in sectors}
    legacy_map = config.raw.get("legacy_sector_map", {})

    resolved, is_legacy = resolve_sector_id(sector_id, valid_ids, legacy_map)
    for s in sectors:
        if s.get("sector_id") == resolved:
            return s
    return None


# ── Public Downstream Helper APIs ───────────────────────────────────────────

def get_sector(config: ProjectConfig, sector_id_or_legacy: str) -> dict[str, Any]:
    """
    Look up a sector by canonical sector_id or legacy alias.

    Supports: canonical sector_id, legacy_sector_ids[], aliases[], legacy_theme_names[].

    Raises KeyError if not found.
    """
    sectors = config.raw.get("sectors", [])
    valid_ids = {s.get("sector_id") for s in sectors}
    legacy_map = config.raw.get("legacy_sector_map", {})

    resolved, is_legacy = resolve_sector_id(sector_id_or_legacy, valid_ids, legacy_map)
    for s in sectors:
        if s.get("sector_id") == resolved:
            return s

    raise KeyError(
        f"sector_id '{sector_id_or_legacy}' not found in sector_universe.yaml. "
        f"Valid canonical IDs: {sorted(valid_ids)}"
    )


def list_scoring_sectors(config: ProjectConfig) -> list[dict[str, Any]]:
    """Return all sectors where scoring_enabled=True."""
    return [
        s for s in config.raw.get("sectors", [])
        if s.get("scoring_enabled", False)
    ]


def _normalize_stock_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a stock entry to a consistent dict shape.

    The stock_universe.yaml uses field names:
      code, name, sectors, role, exposure_type, notes, verification_status, source

    The project schema expects at minimum: code, name, sectors, role, exposure_type, status, notes.
    We accept alternative field names and normalize them here so callers get a uniform shape.
    """
    code = entry.get("code", "")
    name = entry.get("name", code)

    # Accept 'status' or fall back to 'verification_status'
    status = entry.get("status") or entry.get("verification_status", "unverified")

    # Normalize sectors: may be in 'sectors', 'sector_ids', or 'sector'
    raw_sectors = entry.get("sectors") or entry.get("sector_ids") or entry.get("sector", [])
    if isinstance(raw_sectors, str):
        raw_sectors = [raw_sectors]

    # Normalize role/exposure_type
    role = entry.get("role", "")
    exposure = entry.get("exposure_type") or entry.get("exposure", "")

    return {
        "code": code,
        "name": name,
        "sectors": list(raw_sectors),
        "role": role,
        "exposure_type": exposure,
        "status": status,
        "notes": entry.get("notes", ""),
        "source": entry.get("source", ""),
        "_source": entry.get("_source", "stocks"),
        "pending": entry.get("pending", False),
    }


def _is_listed_stock(entry: dict[str, Any]) -> bool:
    """Return True if this entry represents a listed stock (has a valid code)."""
    code = entry.get("code", "")
    if not code or code in ("pending", "待查", ""):
        return False
    return True


def get_stocks_for_sector(
    config: ProjectConfig,
    sector_id_or_legacy: str,
    *,
    include_pending: bool = False,
) -> list[dict[str, Any]]:
    """
    Return stocks for a sector (canonical sector_id or legacy alias).

    Args:
        config: loaded ProjectConfig
        sector_id_or_legacy: sector identifier (canonical or legacy alias)
        include_pending: if True, also includes pending_code_resolution entries
                         that reference this sector, tagged as {pending: True}

    Returns:
        List of normalized stock dicts. Each dict has at minimum:
          code, name, sectors, role, exposure_type, status, notes, _source, pending

    Behavior:
      - sector_id is resolved to canonical before lookup.
      - Only returns listed stocks by default (pending/待查 codes are excluded).
      - Results are deduplicated by (code, canonical_sector_id).
      - If include_pending=True, adds pending items tagged with {pending: True}.
      - Reference companies are NOT included (they are separate in stock_universe.yaml).
      - Reference errors for invalid sector refs are raised by loader validators at load time.

    Raises:
        KeyError: if sector cannot be resolved.
    """
    sector = get_sector(config, sector_id_or_legacy)
    canonical_id = sector.get("sector_id", "")

    stocks_raw = config.raw.get("stocks", [])
    seen_keys: set[str] = set()
    result: list[dict[str, Any]] = []

    for entry in stocks_raw:
        entry_sectors = entry.get("sectors", []) or entry.get("sector_ids", []) or []
        if canonical_id not in entry_sectors:
            continue
        if not _is_listed_stock(entry):
            continue
        normalized = _normalize_stock_entry(entry)
        # Deduplicate by (code, canonical_id)
        dedup_key = (normalized["code"], canonical_id)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        result.append(normalized)

    if include_pending:
        pending_raw = config.raw.get("stock_universe", {}).get("pending_code_resolution", [])
        for item in pending_raw:
            item_sectors = item.get("suggested_sectors", [])
            if canonical_id not in item_sectors:
                continue
            normalized = _normalize_stock_entry(item)
            normalized["pending"] = True
            normalized["_source"] = "pending"
            normalized["status"] = "pending_code_resolution"
            # Pending items have no code — dedup key uses name
            dedup_key = (normalized.get("name", ""), canonical_id)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            result.append(normalized)

    return result


def resolve_evidence_files_for_sector(
    config: ProjectConfig,
    sector_id_or_legacy: str,
) -> list[dict[str, Any]]:
    """
    Return evidence file records associated with a sector.

    Project-aware evidence binding is keyed by canonical sector_id:
      1. Resolve the input through canonical/legacy sector aliases.
      2. Prefer sector_universe.yaml evidence_file_ids[] for that sector.
      3. Match run_manifest.yaml evidence_files[] by evidence_file_id or sector_id.
      4. Return normalized records with file existence metadata.

    This resolver intentionally ignores seed_documents and retired_legacy_outputs.
    """
    sector = get_sector(config, sector_id_or_legacy)
    canonical_id = sector.get("sector_id", "")
    ef_ids = set(sector.get("evidence_file_ids", []) or [])

    evidence_files = config.raw.get("evidence_files", [])
    legacy_map = config.raw.get("legacy_sector_map", {})
    valid_ids = {s.get("sector_id") for s in config.raw.get("sectors", []) if s.get("sector_id")}
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _resolve_path(raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return WORKSPACE_ROOT / path

    def _normalize_record(ef: dict[str, Any], match_type: str) -> dict[str, Any]:
        raw_path = str(ef.get("path", ""))
        resolved_path = _resolve_path(raw_path) if raw_path else WORKSPACE_ROOT
        legacy_sid = str(ef.get("legacy_sector_id", "") or "")
        legacy_resolved = ""
        legacy_is_alias = False
        if legacy_sid:
            legacy_resolved, legacy_is_alias = resolve_sector_id(legacy_sid, valid_ids, legacy_map)
        return {
            "evidence_file_id": ef.get("evidence_file_id", ""),
            "path": raw_path,
            "type": ef.get("type", ""),
            "sector_id": canonical_id,
            "legacy_sector_id": legacy_sid,
            "status": ef.get("status", ""),
            "action": ef.get("action", ""),
            "exists": bool(raw_path and resolved_path.exists()),
            "notes": ef.get("notes", ""),
            "_source": "run_manifest.yaml + sector_universe.yaml",
            "_match_type": match_type,
            "_manifest_sector_id": ef.get("sector_id", ""),
            "_resolved_path": str(resolved_path),
            "_legacy_resolved_sector_id": legacy_resolved if legacy_is_alias else "",
        }

    def _append_once(ef: dict[str, Any], match_type: str) -> None:
        ef_id = str(ef.get("evidence_file_id", "") or "")
        dedup_key = ef_id or str(ef.get("path", ""))
        if dedup_key in seen_ids:
            return
        seen_ids.add(dedup_key)
        result.append(_normalize_record(ef, match_type))

    for ef in evidence_files:
        ef_sid = ef.get("sector_id", "")
        ef_id = ef.get("evidence_file_id", "")

        # Prefer explicit evidence_file_ids from sector_universe.yaml.
        if ef_id and ef_id in ef_ids:
            _append_once(ef, "evidence_file_id")
            continue

        # Fall back to canonical sector_id in run_manifest.yaml.
        if ef_sid == canonical_id:
            _append_once(ef, "canonical_sector_id")
            continue

        # Check via legacy map
        resolved, is_legacy = resolve_sector_id(ef_sid, valid_ids, legacy_map)
        if is_legacy and resolved == canonical_id:
            _append_once(ef, "legacy_sector_id")
            continue

    return result


def get_output_spec(config: ProjectConfig) -> dict[str, Any]:
    """Return project output_spec.yaml as loaded by the project loader."""
    return config.raw.get("output_spec", {}) or {}


def get_output_schema() -> dict[str, Any]:
    """Return the canonical output.schema.yaml contract."""
    path = SCHEMAS_ROOT / "output.schema.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def list_output_types(config: ProjectConfig) -> list[str]:
    """List output types known to the canonical output contract."""
    schema = get_output_schema()
    output_types = schema.get("output_types", {}) or {}
    return sorted(output_types)


def get_output_contract(config: ProjectConfig, output_type: str) -> dict[str, Any]:
    """
    Return a single output contract.

    The canonical source is investment_system/research/schemas/output.schema.yaml.
    output_spec.yaml remains the project-local file/path/field definition source.
    """
    schema = get_output_schema()
    contract = (schema.get("output_types", {}) or {}).get(output_type)
    if not contract:
        raise KeyError(f"output_type '{output_type}' not found in output.schema.yaml")
    result = dict(contract)
    result["output_type"] = output_type
    result["schema_version"] = schema.get("schema_version", "")
    return result


def _table_file_by_name(config: ProjectConfig, file_name: str) -> Path:
    return config.total_tables_dir / file_name


def resolve_output_path(
    config: ProjectConfig,
    output_type: str,
    sector_id: str | None = None,
) -> str:
    """Resolve project-aware output path for a known output type."""
    if output_type == "sector_card":
        if not sector_id:
            raise ValueError("sector_id is required for sector_card output path")
        return str(resolve_sector_card_path(config, sector_id))
    if output_type == "company_table":
        return str(_table_file_by_name(config, "代表公司财务估值总表.csv"))
    if output_type == "sector_comparison_table":
        return str(_table_file_by_name(config, "科技细分方向横向比较表.csv"))
    if output_type == "source_index":
        return str(_table_file_by_name(config, "数据来源索引.csv"))
    if output_type == "missing_data_log":
        return str(config.logs_dir / "缺失数据清单.md")
    if output_type == "conflict_data_log":
        return str(config.logs_dir / "冲突数据清单.md")
    if output_type == "score_table":
        return str(_table_file_by_name(config, "科技细分方向横向比较表.csv"))
    raise KeyError(f"Unknown output_type '{output_type}'")


def validate_output_record_shape(
    config: ProjectConfig,
    output_type: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Validate a generated output record against the canonical output contract."""
    errors: list[str] = []
    warnings: list[str] = []
    contract = get_output_contract(config, output_type)
    required = list(contract.get("required_fields", []) or [])
    deprecated = set(contract.get("deprecated_fields", []) or [])
    legacy_display = set(contract.get("legacy_display_fields", []) or [])
    primary_keys = set(contract.get("primary_key", []) or [])
    optional = set(contract.get("optional_fields", []) or [])
    allowed_placeholders = set((get_output_schema().get("empty_value_policy", {}) or {}).get("allowed_placeholders", []) or [])

    missing_required = sorted(
        field for field in required
        if field not in record or record.get(field) is None or str(record.get(field)).strip() == ""
    )
    for field in missing_required:
        errors.append(f"{output_type} record missing required field '{field}'")

    deprecated_fields_present = sorted(deprecated.intersection(record))
    for field in deprecated_fields_present:
        warnings.append(f"{output_type} record contains deprecated field '{field}'")

    legacy_fields_present = sorted(legacy_display.intersection(record))
    forbidden = {"main_theme", "sub_theme", "legacy_theme_name"}
    for key in sorted(primary_keys.intersection(forbidden)):
        errors.append(f"{output_type} contract uses legacy field '{key}' as primary key")

    for key in sorted(forbidden.intersection(record)):
        if key in primary_keys:
            errors.append(f"{output_type} record uses legacy field '{key}' as primary key")
        elif key not in legacy_display:
            warnings.append(f"{output_type} record contains legacy field '{key}' outside legacy_display_fields")

    empty_required = [
        field for field in required
        if str(record.get(field, "")).strip() in allowed_placeholders and str(record.get(field, "")).strip() != ""
    ]
    for field in empty_required:
        warnings.append(f"{output_type} required field '{field}' uses placeholder value '{record.get(field)}'")

    source_status: dict[str, Any] = {"status": "not_required"}
    source_reqs = contract.get("source_evidence_requirements", {}) or {}
    if source_reqs.get("source_ids_required") and "source_ids" not in record:
        errors.append(f"{output_type} requires source_ids field")
        source_status["status"] = "missing_source_ids"
    elif source_reqs.get("source_ids_required"):
        source_status["status"] = "source_ids_present"

    if source_reqs.get("source_id_required") and "source_id" not in record:
        errors.append(f"{output_type} requires source_id field")
        source_status["status"] = "missing_source_id"
    elif source_reqs.get("source_id_required"):
        source_status["status"] = "source_id_present"

    if output_type == "source_index" and "source_id" not in record:
        errors.append("source_index record missing source_id")

    if output_type == "score_table":
        score_fields = [field for field in required if field.endswith("_score") and field != "total_score"]
        missing_reasons = [
            field.replace("_score", "_reason")
            for field in score_fields
            if field.replace("_score", "_reason") not in record or str(record.get(field.replace("_score", "_reason"), "")).strip() == ""
        ]
        if missing_reasons:
            errors.append(f"score_table missing score reason fields: {', '.join(missing_reasons)}")

    if output_type == "missing_data_log":
        for field in ["output_type", "sector_id", "missing_field", "severity", "reason"]:
            if field not in record or str(record.get(field, "")).strip() == "":
                errors.append(f"missing_data_log missing canonical field '{field}'")

    if output_type == "conflict_data_log":
        for field in ["output_type", "sector_id", "field", "conflicting_values", "source_ids"]:
            if field not in record or str(record.get(field, "")).strip() == "":
                errors.append(f"conflict_data_log missing canonical field '{field}'")

    contract_fields = set(required) | optional | legacy_display
    extra_fields = sorted(set(record) - contract_fields - deprecated)
    if extra_fields:
        warnings.append(f"{output_type} record has fields outside contract: {extra_fields}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "output_type": output_type,
        "missing_required_fields": missing_required,
        "deprecated_fields_present": deprecated_fields_present,
        "legacy_fields_present": legacy_fields_present,
        "source_evidence_status": source_status,
    }


# ── Validation Helpers ───────────────────────────────────────────────────────

def check_missing_files(project_dir: Path) -> list[ValidationWarning]:
    warnings = []
    for fname in REQUIRED_PROJECT_FILES:
        path = project_dir / fname
        if not path.exists():
            warnings.append(ValidationWarning(
                code="MISSING_REQUIRED_FILE",
                message=f"Required file not found: {fname}",
                severity="error",
            ))
    return warnings


def check_sector_id_uniqueness(sectors: list[dict]) -> list[ValidationWarning]:
    warnings = []
    seen: dict[str, str] = {}
    for s in sectors:
        sid = s.get("sector_id", "")
        if not sid:
            warnings.append(ValidationWarning(
                code="SECTOR_MISSING_ID",
                message=f"Sector missing sector_id (name={s.get('sector_name', '?')})",
                severity="error",
            ))
            continue
        if sid in seen:
            warnings.append(ValidationWarning(
                code="DUPLICATE_SECTOR_ID",
                message=f"Duplicate sector_id '{sid}' "
                        f"(first: '{seen[sid]}', second: '{s.get('sector_name', '?')}')",
                severity="error",
            ))
        else:
            seen[sid] = s.get("sector_name", "?")
    return warnings


def check_legacy_sector_map_uniqueness(
    sectors: list[dict],
) -> list[ValidationWarning]:
    """
    Ensure no legacy key (legacy_sector_ids / aliases / legacy_theme_names)
    maps to more than one canonical sector_id. Conflicts are errors.
    """
    warnings = []
    key_to_canonical: dict[str, list[str]] = {}
    for s in sectors:
        sid = s.get("sector_id", "")
        if not sid:
            continue
        for key in s.get("legacy_sector_ids", []):
            key_to_canonical.setdefault(str(key), []).append(sid)
        for key in s.get("aliases", []):
            key_to_canonical.setdefault(str(key), []).append(sid)
        for key in s.get("legacy_theme_names", []):
            key_to_canonical.setdefault(str(key), []).append(sid)

    for key, canonicals in key_to_canonical.items():
        unique = list(dict.fromkeys(canonicals))  # preserve order, remove dups
        if len(unique) > 1:
            warnings.append(ValidationWarning(
                code="LEGACY_MAP_AMBIGUOUS",
                message=f"Legacy key '{key}' maps to multiple canonical sector_ids: "
                        f"{unique}. Conflict must be resolved.",
                severity="error",
            ))
    return warnings


def check_group_id_uniqueness(groups: list[dict]) -> list[ValidationWarning]:
    warnings = []
    seen: dict[str, str] = {}
    for g in groups:
        gid = g.get("group_id", "")
        if not gid:
            warnings.append(ValidationWarning(
                code="GROUP_MISSING_ID",
                message=f"Research group missing group_id (name={g.get('group_name', '?')})",
                severity="error",
            ))
            continue
        if gid in seen:
            warnings.append(ValidationWarning(
                code="DUPLICATE_GROUP_ID",
                message=f"Duplicate group_id '{gid}' "
                        f"(first: '{seen[gid]}', second: '{g.get('group_name', '?')}')",
                severity="error",
            ))
        else:
            seen[gid] = g.get("group_name", "?")
    return warnings


def check_sector_group_membership(
    sectors: list[dict],
    groups: list[dict],
) -> list[ValidationWarning]:
    warnings = []
    valid_group_ids = {g.get("group_id") for g in groups if g.get("group_id")}
    valid_sector_ids = {s.get("sector_id") for s in sectors if s.get("sector_id")}
    for s in sectors:
        rg_id = s.get("research_group_id")
        sid = s.get("sector_id", "?")
        if rg_id and rg_id not in valid_group_ids:
            warnings.append(ValidationWarning(
                code="SECTOR_BAD_GROUP_REF",
                message=f"Sector '{sid}' has research_group_id='{rg_id}' "
                        f"but no matching group found",
                severity="error",
            ))
    for g in groups:
        for ref_sid in g.get("sector_ids", []):
            if ref_sid not in valid_sector_ids:
                warnings.append(ValidationWarning(
                    code="GROUP_REFS_MISSING_SECTOR",
                    message=f"Group '{g.get('group_id')}' references sector_id='{ref_sid}' "
                            f"which does not exist in sectors list",
                    severity="error",
                ))
    return warnings


def check_stock_sector_refs(
    stocks: list[dict],
    valid_sector_ids: set[str],
) -> list[ValidationWarning]:
    warnings = []
    for stk in stocks:
        for sid in stk.get("sectors", []):
            if sid not in valid_sector_ids:
                warnings.append(ValidationWarning(
                    code="STOCK_BAD_SECTOR_REF",
                    message=f"Stock '{stk.get('name', stk.get('code', '?'))}' "
                            f"references sector_id='{sid}' which does not exist",
                    severity="error",
                ))
    return warnings


def check_manifest_sector_refs(
    existing_outputs: list[dict],
    valid_sector_ids: set[str],
) -> list[ValidationWarning]:
    warnings = []
    for out in existing_outputs:
        sid = out.get("sector_id", "")
        if sid and sid not in valid_sector_ids:
            warnings.append(ValidationWarning(
                code="MANIFEST_BAD_SECTOR_REF",
                message=f"existing_outputs '{out.get('path', '?')}' "
                        f"has sector_id='{sid}' which does not exist",
                severity="warning",
            ))
        for s in out.get("sector_ids", []):
            if s not in valid_sector_ids:
                warnings.append(ValidationWarning(
                    code="MANIFEST_BAD_SECTOR_REF",
                    message=f"existing_outputs '{out.get('path', '?')}' "
                            f"has sector_ids[] containing '{s}' which does not exist",
                    severity="warning",
                ))
    return warnings


def check_manifest_planned_sector_refs(
    planned: list[dict],
    valid_sector_ids: set[str],
    legacy_map: dict[str, str],
) -> list[ValidationWarning]:
    """
    run_manifest.planned_sectors[].sector_id must resolve to a valid sector_id.
    Legacy IDs allowed with warning. Unresolvable = error.
    """
    warnings = []
    for p in planned:
        sid = p.get("sector_id", "")
        if not sid:
            continue
        if sid in valid_sector_ids:
            continue
        resolved, is_legacy = resolve_sector_id(sid, valid_sector_ids, legacy_map)
        if is_legacy:
            warnings.append(ValidationWarning(
                code="PLANNED_SECTOR_LEGACY_ID",
                message=f"planned_sectors references legacy sector_id='{sid}' "
                        f"(resolved to '{resolved}'). Update to canonical sector_id.",
                severity="warning",
            ))
        else:
            warnings.append(ValidationWarning(
                code="PLANNED_SECTOR_BAD_REF",
                message=f"planned_sectors references sector_id='{sid}' "
                        f"which does not exist in sector_universe.yaml",
                severity="error",
            ))
    return warnings


def check_evidence_file_sector_refs(
    evidence_files: list[dict],
    valid_sector_ids: set[str],
    legacy_map: dict[str, str],
) -> tuple[list[ValidationWarning], list[str]]:
    """
    Check run_manifest.evidence_files[].sector_id references.
    Returns (warnings, evidence_warnings).
    """
    warnings = []
    evidence_warnings = []
    for ef in evidence_files:
        sid = ef.get("sector_id", "")
        ef_id = ef.get("evidence_file_id", ef.get("path", "?"))
        if not sid:
            warnings.append(ValidationWarning(
                code="EVIDENCE_FILE_NO_SECTOR_ID",
                message=f"evidence_file '{ef_id}' has no sector_id",
                severity="error",
            ))
            continue
        if sid in valid_sector_ids:
            continue
        resolved, is_legacy = resolve_sector_id(sid, valid_sector_ids, legacy_map)
        if is_legacy:
            evidence_warnings.append(
                f"evidence_file '{ef_id}' uses legacy sector_id='{sid}' "
                f"(resolved to '{resolved}'). Update to canonical sector_id."
            )
        else:
            warnings.append(ValidationWarning(
                code="EVIDENCE_FILE_BAD_SECTOR_REF",
                message=f"evidence_file '{ef_id}' references sector_id='{sid}' "
                        f"which does not exist in sector_universe.yaml",
                severity="error",
            ))
    return warnings, evidence_warnings


def check_seed_document_action(
    seed_docs: list[dict],
) -> list[ValidationWarning]:
    """
    seed_documents[].action must be 'use_as_seed_only'.
    not_allowed_for must contain all mandatory items (evidence, score, rating, investment_conclusion).
    """
    warnings = []
    for doc in seed_docs:
        action = str(doc.get("action", "")).lower()
        path = doc.get("path", "?")
        not_allowed = doc.get("not_allowed_for", [])
        if action != "use_as_seed_only":
            warnings.append(ValidationWarning(
                code="SEED_WRONG_ACTION",
                message=f"Seed document '{path}' has action='{action}' "
                        f"but must be 'use_as_seed_only'",
                severity="warning",
            ))

        # Check mandatory not_allowed_for items
        missing = SEED_MANDATORY_NOT_ALLOWED - set(not_allowed)
        if missing and action == "use_as_seed_only":
            warnings.append(ValidationWarning(
                code="SEED_MISSING_NOT_ALLOWED",
                message=f"Seed document '{path}' missing required not_allowed_for items: "
                        f"{sorted(missing)}. Must include: {sorted(SEED_MANDATORY_NOT_ALLOWED)}",
                severity="warning",
            ))
    return warnings


def check_seed_document_paths(
    seed_docs: list[dict],
    project_dir: Path,
) -> list[ValidationWarning]:
    warnings = []
    for doc in seed_docs:
        p = doc.get("path", "")
        if p:
            abs_path = Path(p) if Path(p).is_absolute() else (project_dir / p)
            if not abs_path.exists() and not Path(p).exists():
                warnings.append(ValidationWarning(
                    code="SEED_DOC_NOT_FOUND",
                    message=f"seed_documents path does not exist: {p}",
                    severity="warning",
                ))
    return warnings


def check_seed_document_status(seed_docs: list[dict]) -> list[ValidationWarning]:
    warnings = []
    for doc in seed_docs:
        status = str(doc.get("status", "")).lower()
        dtype = str(doc.get("type", "")).lower()
        action = str(doc.get("action", "")).lower()
        path = doc.get("path", "?")

        if status in SEED_FORBIDDEN_STATUSES:
            warnings.append(ValidationWarning(
                code="SEED_WRONG_STATUS",
                message=f"Seed document '{path}' has forbidden status '{doc.get('status')}'. "
                        f"Must be 'seeded_unverified', not completed/research.",
                severity="error",
            ))
        if dtype in SEED_FORBIDDEN_TYPES:
            warnings.append(ValidationWarning(
                code="SEED_WRONG_TYPE",
                message=f"Seed document '{path}' has type '{doc.get('type')}' "
                        f"which is a completed-output type.",
                severity="error",
            ))
        if action in SEED_FORBIDDEN_ACTIONS:
            warnings.append(ValidationWarning(
                code="SEED_WRONG_ACTION",
                message=f"Seed document '{path}' has action '{doc.get('action')}' "
                        f"which is not 'use_as_seed_only'. "
                        f"Seed documents must use action='use_as_seed_only'.",
                severity="warning",
            ))
    return warnings


def check_peripheral_observation_scoring(sectors: list[dict]) -> list[ValidationWarning]:
    warnings = []
    for s in sectors:
        if s.get("research_group_id") == "peripheral_observation":
            if s.get("scoring_enabled", False):
                warnings.append(ValidationWarning(
                    code="OBSERVATION_SECTOR_SCORING_ENABLED",
                    message=f"Sector '{s.get('sector_id')}' is in peripheral_observation "
                            f"group but has scoring_enabled=true",
                    severity="error",
                ))
    return warnings


def check_ai_app_parent_chain(sectors: list[dict]) -> list[ValidationWarning]:
    warnings = []
    ai_app_ids = {"ai_application_data", "ai_terminal_consumer_electronics"}
    for s in sectors:
        if s.get("research_group_id") in ai_app_ids:
            pc = s.get("parent_chain", "")
            if pc in AI_APP_FORBIDDEN_PARENTCHAINS:
                warnings.append(ValidationWarning(
                    code="AI_APP_BAD_PARENT_CHAIN",
                    message=f"Sector '{s.get('sector_id')}' in '{s.get('research_group_id')}' "
                            f"has parent_chain='{pc}' which is forbidden for AI应用/数据要素",
                    severity="error",
                ))
    return warnings


def check_unlisted_in_stocks(stocks: list[dict]) -> list[ValidationWarning]:
    warnings = []
    for stk in stocks:
        code = stk.get("code", "")
        notes = stk.get("notes", "")
        name = stk.get("name", "?")
        if "未上市" in notes or "未上市，参考" in notes or "（未上市" in name:
            warnings.append(ValidationWarning(
                code="UNLISTED_IN_STOCKS",
                message=f"Stock '{name}' (code={code}) appears to be unlisted. "
                        f"Move to reference_companies.",
                severity="warning",
            ))
        if code and not STOCK_CODE_PATTERN.match(code):
            if code not in ("", "待查", "pending"):
                warnings.append(ValidationWarning(
                    code="MALFORMED_STOCK_CODE",
                    message=f"Stock '{name}' has code '{code}' which does not match "
                            f"^\\d{{6}}\\.(SH|SZ|BJ)$. Use full code.",
                    severity="error",
                ))
    return warnings


def check_stock_code_duplicates(stocks: list[dict]) -> list[ValidationWarning]:
    warnings = []
    seen: dict[str, str] = {}
    for stk in stocks:
        code = stk.get("code", "")
        if not code:
            continue
        name = stk.get("name", "?")
        if code in seen:
            warnings.append(ValidationWarning(
                code="DUPLICATE_STOCK_CODE",
                message=f"Stock code '{code}' appears twice: '{seen[code]}' and '{name}'",
                severity="error",
            ))
        else:
            seen[code] = name
    return warnings


def check_output_spec_directories(output_spec: dict[str, Any]) -> list[ValidationWarning]:
    warnings = []
    dirs = output_spec.get("directories", {})
    for d in ["total_tables", "logs"]:
        if d not in dirs:
            warnings.append(ValidationWarning(
                code="MISSING_OUTPUT_DIR",
                message=f"output_spec.directories missing required key '{d}'",
                severity="error",
            ))
        elif "path" not in dirs.get(d, {}) and "path_template" not in dirs.get(d, {}):
            warnings.append(ValidationWarning(
                code="OUTPUT_DIR_NO_PATH",
                message=f"output_spec.directories.{d} missing 'path' or 'path_template'",
                severity="error",
            ))
    return warnings


def check_scoring_weights(weights: dict[str, float]) -> list[ValidationWarning]:
    warnings = []
    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        warnings.append(ValidationWarning(
            code="WEIGHTS_NOT_SUM_TO_1",
            message=f"Scoring weights sum to {total:.4f}, expected 1.0 "
                    f"(off by {abs(total - 1.0):.4f})",
            severity="error",
        ))
    return warnings


def check_quality_settings(
    require_sources: bool,
    allow_placeholders: bool,
) -> list[ValidationWarning]:
    warnings = []
    if not require_sources:
        warnings.append(ValidationWarning(
            code="SOURCES_NOT_REQUIRED",
            message="quality.require_sources is False. Must be True for research-grade.",
            severity="error",
        ))
    if allow_placeholders:
        warnings.append(ValidationWarning(
            code="PLACEHOLDERS_ALLOWED",
            message="quality.allow_placeholders is True. Should be False.",
            severity="warning",
        ))
    return warnings


def check_excluded_scope_robots(
    sectors: list[dict],
    scope_exclude: list[str],
) -> list[ValidationWarning]:
    warnings = []
    excluded_terms = [e.lower() for e in scope_exclude]
    for s in sectors:
        sid = s.get("sector_id", "")
        sname = s.get("sector_name", "")
        if any(term in sid.lower() or term in sname.lower() for term in excluded_terms):
            warnings.append(ValidationWarning(
                code="EXCLUDED_SECTOR_FOUND",
                message=f"Sector '{sname}' (id={sid}) matches excluded scope term",
                severity="warning",
            ))
    return warnings


def check_pending_code_resolution_refs(
    pending: list[dict],
    valid_sector_ids: set[str],
) -> list[ValidationWarning]:
    """pending_code_resolution[].suggested_sectors must reference valid sector_ids."""
    warnings = []
    for item in pending:
        name = item.get("name", "?")
        for sid in item.get("suggested_sectors", []):
            if sid not in valid_sector_ids:
                warnings.append(ValidationWarning(
                    code="PENDING_BAD_SECTOR_REF",
                    message=f"pending_code_resolution '{name}' references sector_id='{sid}' "
                            f"which does not exist in sector_universe.yaml",
                    severity="error",
                ))
    return warnings


def check_stock_coverage_by_sector(
    sectors: list[dict],
    stocks: list[dict],
    valid_sector_ids: set[str],
) -> list[ValidationWarning]:
    """
    Warn if scoring-enabled sectors have too few stocks.
    P0/P1 < 5 companies = warning; P2 < 3 = warning.
    observation_only sectors are exempt.
    """
    warnings = []
    sector_stocks: dict[str, list[str]] = {sid: [] for sid in valid_sector_ids}
    for stk in stocks:
        for sid in stk.get("sectors", []):
            if sid in sector_stocks:
                sector_stocks[sid].append(stk.get("name", stk.get("code", "?")))

    for s in sectors:
        sid = s.get("sector_id", "")
        if s.get("research_group_id") == "peripheral_observation":
            continue  # exempt

        count = len(sector_stocks.get(sid, []))
        priority = s.get("priority", "P9")
        sname = s.get("sector_name", sid)

        if priority in ("P0", "P1"):
            if count < 5:
                warnings.append(ValidationWarning(
                    code="SECTOR_THIN_COVERAGE",
                    message=f"Sector '{sname}' (id={sid}, priority={priority}) "
                            f"has only {count} stock(s) (need >=5 for P0/P1). "
                            f"Coverage: {sector_stocks.get(sid, [])}",
                    severity="warning",
                ))
        else:  # P2, P3
            if count < 3:
                warnings.append(ValidationWarning(
                    code="SECTOR_THIN_COVERAGE",
                    message=f"Sector '{sname}' (id={sid}, priority={priority}) "
                            f"has only {count} stock(s) (need >=3 for P2/P3). "
                            f"Coverage: {sector_stocks.get(sid, [])}",
                    severity="warning",
                ))

    return warnings


def check_evidence_file_mapping_consistency(
    evidence_files: list[dict],
    sectors: list[dict],
    legacy_map: dict[str, str],
) -> list[ValidationWarning]:
    """
    Verify:
    1. evidence_files[].sector_id must be canonical.
    2. If evidence_file_id exists, it must appear in the matched sector's evidence_file_ids[].
    3. If legacy_sector_id exists, it must resolve to the same canonical sector_id.
    """
    warnings = []
    valid_ids = {s.get("sector_id") for s in sectors}
    ef_id_to_sector: dict[str, str] = {}
    for s in sectors:
        sid = s.get("sector_id", "")
        for ef_id in s.get("evidence_file_ids", []):
            ef_id_to_sector[ef_id] = sid

    for ef in evidence_files:
        ef_id = ef.get("evidence_file_id", "")
        sid = ef.get("sector_id", "")
        legacy_sid = ef.get("legacy_sector_id", "")

        # Check canonical
        if sid not in valid_ids:
            continue  # already covered by check_evidence_file_sector_refs

        # Check evidence_file_id mapping
        if ef_id and ef_id in ef_id_to_sector:
            expected = ef_id_to_sector[ef_id]
            if expected != sid:
                warnings.append(ValidationWarning(
                    code="EVIDENCE_FILE_ID_MISMATCH",
                    message=f"evidence_file '{ef_id}' is registered in sector "
                            f"'{expected}' but evidence_file.sector_id='{sid}'. "
                            f"Align sector_id with evidence_file_ids[] in sector_universe.yaml.",
                    severity="warning",
                ))
        elif ef_id:
            warnings.append(ValidationWarning(
                code="EVIDENCE_FILE_ID_NOT_IN_SECTOR",
                message=f"evidence_file_id '{ef_id}' is not in any sector's "
                        f"evidence_file_ids[] list. Either add it or check the ID.",
                severity="warning",
            ))

        # Check legacy_sector_id consistency
        if legacy_sid:
            resolved, is_legacy = resolve_sector_id(legacy_sid, valid_ids, legacy_map)
            if is_legacy and resolved != sid:
                warnings.append(ValidationWarning(
                    code="LEGACY_SECTOR_ID_MISMATCH",
                    message=f"evidence_file has legacy_sector_id='{legacy_sid}' "
                            f"(→ canonical '{resolved}') but sector_id='{sid}'. "
                            f"These must be consistent.",
                    severity="warning",
                ))

    return warnings


def check_unregistered_md_seed_documents(
    project_dir: Path,
    seed_docs: list[dict],
    existing_outputs: list[dict],
    retired_legacy_outputs: list[dict] | None = None,
) -> list[ValidationWarning]:
    """
    Scan workspace for MD files that look like sector seeds but are not
    registered in run_manifest.seed_documents or existing_outputs.
    Returns warnings; does NOT auto-register.
    """
    warnings = []
    scan_roots = [
        project_dir,
        WORKSPACE_ROOT / "科技主线调研输出",
        WORKSPACE_ROOT,
    ]

    registered_paths: set[str] = set()
    for doc in seed_docs:
        p = doc.get("path", "")
        if p:
            registered_paths.add(str(Path(p).resolve()))
            registered_paths.add(str(Path(p).absolute()))
            registered_paths.add(p)
    for out in existing_outputs:
        p = out.get("path", "")
        if p:
            abs_p = WORKSPACE_ROOT / p
            registered_paths.add(str(abs_p.resolve()))
            registered_paths.add(str(abs_p))
            registered_paths.add(p)
    # Also exclude retired legacy output paths from the unregistered-MD scan
    if retired_legacy_outputs:
        for out in retired_legacy_outputs:
            p = out.get("path", "")
            if p:
                abs_p = WORKSPACE_ROOT / p
                registered_paths.add(str(abs_p.resolve()))
                registered_paths.add(str(abs_p))
                registered_paths.add(p)

    found_unregistered: list[tuple[str, str]] = []

    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for root, dirs, files in os.walk(scan_root):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if d not in MD_SCAN_EXCLUDE_DIRS]

            for fname in files:
                if not fname.endswith(".md"):
                    continue
                if fname in MD_SCAN_EXCLUDE_FILES:
                    continue
                full_path = root_path / fname
                if str(full_path.resolve()) in registered_paths:
                    continue
                if str(full_path.absolute()) in registered_paths:
                    continue
                if _looks_like_sector_seed(full_path):
                    rel = str(full_path.relative_to(WORKSPACE_ROOT))
                    found_unregistered.append((rel, full_path.name))

    for rel_path, fname in found_unregistered:
        warnings.append(ValidationWarning(
            code="UNREGISTERED_MD_SEED",
            message=f"Unregistered MD file found: {rel_path} "
                    f"(looks like sector seed but not in seed_documents or existing_outputs). "
                    f"Add it to run_manifest.seed_documents or existing_outputs.",
            severity="warning",
        ))

    return warnings


def _looks_like_sector_seed(path: Path) -> bool:
    """Conservative heuristic: requires strong sector-specific signals."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        text_lower = text.lower()
        snippet = text[:1024]
        has_cjk = any("\u4e00" <= c <= "\u9fff" for c in snippet)
        if not has_cjk:
            return False

        negative_patterns = [
            "工作流", "重构", "计划", "迁移", "调研日志",
            "缺失数据", "冲突数据", "系统设计", "架构",
            "pipeline", "技术方案", "实施计划", "项目重构",
            "工作流构建", "阶段", "下一步", "TODO",
        ]
        neg_count = sum(1 for p in negative_patterns if p in text_lower)
        if neg_count >= 2:
            return False

        positive_patterns = [
            "## ", "### ",
            "景气度", "产业逻辑",
            "光模块", "半导体", "AI芯片", "液冷", "CPO",
            "估值", "催化剂", "风险",
            "公司", "细分方向", "股票池",
        ]
        pos_count = sum(1 for p in positive_patterns if p in text_lower)
        if pos_count < 3:
            return False

        return True
    except Exception:
        return False


# ── Core Loader ─────────────────────────────────────────────────────────────

def load_project(
    project_id: str,
    *,
    silent: bool = False,
    strict: bool = True,
    create_dirs: bool = False,
) -> ProjectConfig:
    """
    Load and validate a project configuration.

    By default this function is read-only: it will NOT create output directories.
    Pass create_dirs=True (or use --create-output-dirs CLI flag) to create them.
    """
    project_dir = PROJECTS_ROOT / project_id

    if not project_dir.exists():
        raise FileNotFoundError(
            f"Project directory not found: {project_dir}\n"
            f"Available: {sorted(p.name for p in PROJECTS_ROOT.iterdir() if p.is_dir())}"
        )

    # ── 0. Required files ───────────────────────────────────────────────
    missing_file_warnings = check_missing_files(project_dir)
    errors_from_missing = [w for w in missing_file_warnings if w.severity == "error"]
    if errors_from_missing and strict:
        raise ValueError(
            f"Missing required files in '{project_id}':\n" +
            "\n".join(f"  [{w.code}] {w.message}" for w in errors_from_missing)
        )
    all_warnings: list[ValidationWarning] = list(missing_file_warnings)

    # ── Load YAML files ────────────────────────────────────────────────
    project_yaml = load_yaml(project_dir / "project.yaml")
    sector_yaml = load_yaml(project_dir / "sector_universe.yaml")
    stock_yaml = load_yaml(project_dir / "stock_universe.yaml")
    scoring_yaml = load_yaml(project_dir / "scoring_rules.yaml")
    output_spec_yaml = load_yaml(project_dir / "output_spec.yaml")
    manifest_yaml = load_yaml(project_dir / "run_manifest.yaml")

    # ── 1. Basic project info ───────────────────────────────────────
    actual_project_id = project_yaml.get("project_id", project_id)
    if actual_project_id != project_id:
        all_warnings.append(ValidationWarning(
            code="PROJECT_ID_MISMATCH",
            message=f"project.yaml has project_id='{actual_project_id}' but "
                    f"directory is '{project_id}'",
            severity="error",
        ))

    # ── 2. Output directory ───────────────────────────────────────
    output_root_str = get_nested(project_yaml, "output", "root", default="")
    if not output_root_str:
        all_warnings.append(ValidationWarning(
            code="MISSING_OUTPUT_ROOT",
            message="project.yaml missing 'output.root'",
            severity="error",
        ))
        output_root = project_dir / "output"
    else:
        output_root = Path(output_root_str)

    if not output_root.exists():
        if create_dirs:
            try:
                output_root.mkdir(parents=True, exist_ok=True)
                if not silent:
                    print(f"[NOTE] Created output directory: {output_root}", file=sys.stderr)
            except OSError as exc:
                all_warnings.append(ValidationWarning(
                    code="OUTPUT_DIR_UNWRITABLE",
                    message=f"Cannot create output directory: {output_root}: {exc}",
                    severity="warning",
                ))
        else:
            all_warnings.append(ValidationWarning(
                code="OUTPUT_DIR_NOT_FOUND",
                message=f"Output root does not exist: {output_root} "
                        f"(use --create-output-dirs to create it)",
                severity="warning",
            ))

    # ── 3-5. Universe loading ───────────────────────────────────────
    research_groups = get_nested(sector_yaml, "research_groups", default=[])
    sectors = get_nested(sector_yaml, "sectors", default=[])
    stocks = get_nested(stock_yaml, "stocks", default=[])
    reference_companies = get_nested(stock_yaml, "reference_companies", default=[])
    pending_code = get_nested(stock_yaml, "pending_code_resolution", default=[])
    evidence_files = get_nested(manifest_yaml, "evidence_files", default=[])
    existing_outputs = get_nested(manifest_yaml, "existing_outputs", default=[])
    retired_legacy_outputs = get_nested(manifest_yaml, "retired_legacy_outputs", default=[])
    seed_docs = get_nested(manifest_yaml, "seed_documents", default=[])
    planned = get_nested(manifest_yaml, "planned_sectors", default=[])

    if not sectors:
        all_warnings.append(ValidationWarning(
            code="NO_SECTORS_DEFINED",
            message="sector_universe.yaml has no 'sectors' entries",
            severity="error",
        ))
    if not stocks:
        all_warnings.append(ValidationWarning(
            code="NO_STOCKS_DEFINED",
            message="stock_universe.yaml has no 'stocks' entries",
            severity="warning",
        ))

    valid_sector_ids = {s.get("sector_id") for s in sectors if s.get("sector_id")}
    legacy_sector_map = build_legacy_sector_map(sectors)

    # ── 6. Run all cross-validators ──────────────────────────────────
    all_warnings.extend(check_sector_id_uniqueness(sectors))
    all_warnings.extend(check_legacy_sector_map_uniqueness(sectors))
    all_warnings.extend(check_group_id_uniqueness(research_groups))
    all_warnings.extend(check_sector_group_membership(sectors, research_groups))
    all_warnings.extend(check_stock_sector_refs(stocks, valid_sector_ids))
    all_warnings.extend(check_manifest_sector_refs(existing_outputs, valid_sector_ids))
    all_warnings.extend(check_manifest_planned_sector_refs(planned, valid_sector_ids, legacy_sector_map))

    ev_warns, ev_file_warns = check_evidence_file_sector_refs(
        evidence_files, valid_sector_ids, legacy_sector_map
    )
    all_warnings.extend(ev_warns)
    all_warnings.extend(check_seed_document_action(seed_docs))
    all_warnings.extend(check_seed_document_paths(seed_docs, project_dir))
    all_warnings.extend(check_seed_document_status(seed_docs))
    all_warnings.extend(check_peripheral_observation_scoring(sectors))
    all_warnings.extend(check_ai_app_parent_chain(sectors))
    all_warnings.extend(check_unlisted_in_stocks(stocks))
    all_warnings.extend(check_stock_code_duplicates(stocks))
    all_warnings.extend(check_output_spec_directories(output_spec_yaml))
    all_warnings.extend(check_pending_code_resolution_refs(pending_code, valid_sector_ids))
    all_warnings.extend(check_stock_coverage_by_sector(sectors, stocks, valid_sector_ids))
    all_warnings.extend(check_evidence_file_mapping_consistency(evidence_files, sectors, legacy_sector_map))

    unregistered_warns = check_unregistered_md_seed_documents(
        project_dir, seed_docs, existing_outputs, retired_legacy_outputs
    )
    all_warnings.extend(unregistered_warns)

    # ── 7. Scoring rules ────────────────────────────────────────────
    scoring_model = get_nested(scoring_yaml, "score_model", default="unknown")
    dimensions = get_nested(scoring_yaml, "dimensions", default={})
    weights: dict[str, float] = {}
    for dim_name, dim_data in dimensions.items():
        if isinstance(dim_data, dict):
            weights[dim_name] = float(dim_data.get("weight", 0))
    all_warnings.extend(check_scoring_weights(weights))

    # ── 8. Excluded scope ──────────────────────────────────────────
    scope_exclude = get_nested(project_yaml, "scope", "exclude", default=[])
    all_warnings.extend(check_excluded_scope_robots(sectors, scope_exclude))

    # ── 9. Quality settings ───────────────────────────────────────
    quality = get_nested(project_yaml, "quality", default={})
    grade_target = quality.get("grade_target", "research-grade")
    require_sources = quality.get("require_sources", True)
    allow_placeholders = quality.get("allow_placeholders", False)
    all_warnings.extend(check_quality_settings(require_sources, allow_placeholders))

    # ── 10. Output spec required fields ──────────────────────────
    for field_name in REQUIRED_OUTPUT_SPEC_FIELDS:
        if field_name not in output_spec_yaml:
            all_warnings.append(ValidationWarning(
                code="MISSING_OUTPUT_SPEC_FIELD",
                message=f"output_spec.yaml missing required field '{field_name}'",
                severity="warning",
            ))

    # ── 11. Build sub-dirs ───────────────────────────────────────
    dirs = get_nested(output_spec_yaml, "directories", default={})

    # sector_cards_root: parent dir containing group sub-dirs
    sc_cfg = dirs.get("sector_cards", {})
    sc_path_template = sc_cfg.get("path_template", "{group_order}_{group_name}") \
        if isinstance(sc_cfg, dict) else str(sc_cfg)
    sc_filename_pattern = sc_cfg.get(
        "filename_pattern", "{priority}_{sector_name_safe}.md"
    ) if isinstance(sc_cfg, dict) else "{priority}_{sector_name_safe}.md"
    # sector_cards_root is the output_root (the parent; group dirs are under it)
    sector_cards_root = output_root

    tt_cfg = dirs.get("total_tables", {})
    tt_path = (tt_cfg.get("path", "00_总表")
               if isinstance(tt_cfg, dict) else str(tt_cfg))
    total_tables_dir = output_root / tt_path

    lg_cfg = dirs.get("logs", {})
    lg_path = (lg_cfg.get("path", "99_日志")
               if isinstance(lg_cfg, dict) else str(lg_cfg))
    logs_dir = output_root / lg_path

    rd_cfg = dirs.get("raw_data", {})
    rd_path = (rd_cfg.get("path", "00_原始数据")
               if isinstance(rd_cfg, dict) else "00_原始数据")
    raw_data_root = output_root / rd_path

    # Create sub-dirs only if create_dirs=True
    dirs_to_create = []
    if create_dirs:
        for d in [total_tables_dir, logs_dir, raw_data_root]:
            if not d.exists():
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    if not silent:
                        print(f"[NOTE] Created: {d}", file=sys.stderr)
                except OSError as exc:
                    all_warnings.append(ValidationWarning(
                        code="DIR_CREATE_FAILED",
                        message=f"Cannot create directory {d}: {exc}",
                        severity="warning",
                    ))

    # ── 12. Runtime ───────────────────────────────────────────────
    runtime = get_nested(project_yaml, "runtime", default={})
    python_exe = runtime.get("python", "")

    # ── 13. Compute extended counts ───────────────────────────────
    scoring_enabled = [s for s in sectors if s.get("scoring_enabled", False)]
    observation_only = [s for s in sectors
                        if s.get("research_group_id") == "peripheral_observation"]

    # ── 14. Build sector coverage summary ───────────────────────
    # Correct thresholds: P0/P1 >= 5, P2 >= 3, observation_only = exempt
    sector_stocks_map: dict[str, list[str]] = {
        s.get("sector_id"): [] for s in sectors
    }
    for stk in stocks:
        for sid in stk.get("sectors", []):
            if sid in sector_stocks_map:
                sector_stocks_map[sid].append(stk.get("name", stk.get("code", "?")))

    sector_coverage = []
    for s in sectors:
        sid = s.get("sector_id", "")
        count = len(sector_stocks_map.get(sid, []))
        is_obs = s.get("research_group_id") == "peripheral_observation"
        priority = s.get("priority", "P9")

        if is_obs:
            status = "exempt"
        elif count == 0:
            status = "missing"
        elif priority in ("P0", "P1"):
            status = "ok" if count >= 5 else "thin"
        else:  # P2, P3
            status = "ok" if count >= 3 else "thin"

        sector_coverage.append({
            "sector_id": sid,
            "sector_name": s.get("sector_name", ""),
            "priority": priority,
            "scoring_enabled": s.get("scoring_enabled", False),
            "stock_count": count,
            "coverage_status": status,
        })

    # ── 15. Sample sector card paths ─────────────────────────────
    sample_paths = []
    for s in sectors[:5]:
        try:
            path = resolve_sector_card_path(
                ProjectConfig(
                    project_id=project_id, project_name="", research_type="",
                    market="", version="", output_root=output_root,
                    sector_cards_root=sector_cards_root,
                    sector_card_path_template=sc_path_template,
                    sector_card_filename_pattern=sc_filename_pattern,
                    total_tables_dir=total_tables_dir, logs_dir=logs_dir,
                    raw_data_root=raw_data_root,
                    sectors_dir=sector_cards_root,
                    sector_count=0, stock_count=0,
                    scoring_model="", weights={}, quality_grade_target="",
                    require_sources=False, allow_placeholders=False,
                    existing_output_count=0, seed_document_count=0,
                    planned_sector_count=0,
                    raw={"research_groups": research_groups, "output_spec": output_spec_yaml},
                ),
                s,
                output_spec_yaml,
            )
            sample_paths.append({
                "sector_id": s.get("sector_id", ""),
                "sector_name": s.get("sector_name", ""),
                "resolved_path": str(path),
            })
        except Exception:
            pass

    # ── 16. Error-severity gate ──────────────────────────────────
    current_errors = [w for w in all_warnings if w.severity == "error"]
    if current_errors and strict:
        raise ValueError(
            f"Validation errors in '{project_id}':\n" +
            "\n".join(f"  [{w.code}] {w.message}" for w in current_errors)
        )

    # ── Build ProjectConfig ───────────────────────────────────────
    config = ProjectConfig(
        project_id=project_id,
        project_name=project_yaml.get("project_name", ""),
        research_type=project_yaml.get("research_type", "sector_research"),
        market=project_yaml.get("market", "A股"),
        version=project_yaml.get("version", "1"),
        created_date=project_yaml.get("created_date", ""),
        output_root=output_root,
        sector_cards_root=sector_cards_root,
        sector_card_path_template=sc_path_template,
        sector_card_filename_pattern=sc_filename_pattern,
        total_tables_dir=total_tables_dir,
        logs_dir=logs_dir,
        raw_data_root=raw_data_root,
        sectors_dir=sector_cards_root,  # legacy alias
        sector_count=len(sectors),
        stock_count=len(stocks),
        planned_sector_count=len(planned),
        scoring_model=scoring_model,
        weights=weights,
        quality_grade_target=grade_target,
        require_sources=require_sources,
        allow_placeholders=allow_placeholders,
        existing_output_count=len(existing_outputs),
        seed_document_count=len(seed_docs),
        warnings=all_warnings,
        python_exe=python_exe,
        scope_include=get_nested(project_yaml, "scope", "include", default=[]),
        scope_exclude=scope_exclude,
        raw={
            "research_group_count": len(research_groups),
            "scoring_enabled_sector_count": len(scoring_enabled),
            "observation_only_sector_count": len(observation_only),
            "listed_stock_count": len([s for s in stocks if s.get("code")]),
            "reference_company_count": len(reference_companies),
            "pending_code_resolution_count": len(pending_code),
            "legacy_sector_map": legacy_sector_map,
            "sector_coverage": sector_coverage,
            "evidence_file_count": len(evidence_files),
            "evidence_file_warnings": ev_file_warns,
            "unregistered_md_warnings": [w.message for w in unregistered_warns],
            "sample_sector_card_paths": sample_paths,
            "retired_legacy_output_count": len(retired_legacy_outputs),
            # Full raw config for downstream pipelines
            "project_yaml": project_yaml,
            "sector_universe": sector_yaml,
            "stock_universe": stock_yaml,
            "scoring_rules": scoring_yaml,
            "output_spec": output_spec_yaml,
            "run_manifest": manifest_yaml,
            "sectors": sectors,
            "stocks": stocks,
            "research_groups": research_groups,
            "evidence_files": evidence_files,
            "existing_outputs": existing_outputs,
            "retired_legacy_outputs": retired_legacy_outputs,
        },
    )
    return config


# ── CLI Entry Point ────────────────────────────────────────────────────────

def _print_dry_run_paths(config: ProjectConfig) -> None:
    """Print dry-run path resolution for all sectors. NEVER creates files."""
    output_spec = config.raw.get("output_spec", {})
    sectors = config.raw.get("sectors", [])
    research_groups = config.raw.get("research_groups", [])
    dirs = output_spec.get("directories", {})

    print(f"Dry-run path resolution for project: {config.project_id} ({config.project_name})")
    print(f"Output root: {config.output_root}")
    print(f"sector_cards_root: {config.sector_cards_root}")
    print(f"sector_card_path_template: {config.sector_card_path_template}")
    print(f"sector_card_filename_pattern: {config.sector_card_filename_pattern}")
    print()

    print("Global directories:")
    for key in ["total_tables", "logs", "raw_data", "seed_documents"]:
        d = dirs.get(key, {})
        if isinstance(d, dict):
            p = d.get("path", d.get("path_template", "?"))
        else:
            p = str(d)
        full = config.output_root / p
        print(f"  {key}: {full}")
    print()

    # Shared paths via resolve_output_paths
    paths = resolve_output_paths(config)
    print("Shared output files:")
    for key in ["company_table_path", "comparison_table_path", "source_index_path",
                 "missing_data_log_path", "conflict_data_log_path", "research_log_path"]:
        if key in paths:
            print(f"  {key}: {paths[key]}")
    print()

    ev_files = config.raw.get("evidence_files", [])
    print(f"Evidence files ({len(ev_files)}):")
    for ef in ev_files:
        print(f"  {ef.get('path', '?')}  "
              f"[sector_id={ef.get('sector_id', '?')}, "
              f"ef_id={ef.get('evidence_file_id', '?')}]")
    print()

    manifest = config.raw.get("run_manifest", {})
    seed_docs = manifest.get("seed_documents", [])
    print(f"Seed documents ({len(seed_docs)}):")
    for sd in seed_docs:
        print(f"  {sd.get('path', '?')}  "
              f"[type={sd.get('type', '?')}, "
              f"action={sd.get('action', '?')}]")
    print()

    print(f"Sector cards ({len(sectors)} total):")
    grouped: dict[str, list[dict]] = {}
    for s in sectors:
        rg_id = s.get("research_group_id", "unknown")
        grouped.setdefault(rg_id, []).append(s)

    for g in research_groups:
        rg_id = g.get("group_id", "unknown")
        rg_name = g.get("group_name", rg_id)
        s_list = grouped.get(rg_id, [])
        print(f"  Group {rg_id} ({rg_name}): {len(s_list)} sectors")
        for s in s_list:
            path = resolve_sector_card_path(config, s, output_spec)
            sid = s.get("sector_id", "")
            status = s.get("status", "?")
            print(f"    [{s.get('priority','?')}] {sid} -> {path}")
            print(f"      status={status}, scoring={s.get('scoring_enabled', False)}")
    print()

    total_tables_cfg = dirs.get("total_tables", {})
    tt_path = (total_tables_cfg.get("path", "00_总表")
               if isinstance(total_tables_cfg, dict) else str(total_tables_cfg))
    print("Total table files:")
    for f in (total_tables_cfg.get("files", []) if isinstance(total_tables_cfg, dict) else []):
        full = config.total_tables_dir / f.get("name", "?")
        print(f"  {f.get('name','?')} -> {full}")
    print()

    logs_path = dirs.get("logs", {}).get("path", "99_日志") \
        if isinstance(dirs.get("logs", {}), dict) else str(dirs.get("logs", "99_日志"))
    print("Log files:")
    for f in dirs.get("logs", {}).get("files", []) if isinstance(dirs.get("logs", {}), dict) else []:
        full = config.logs_dir / f.get("name", "?")
        print(f"  {f.get('name','?')} -> {full}")


def _print_dry_run_output_contract(config: ProjectConfig) -> None:
    """Print output contract summary without creating files."""
    print(f"Output contract dry-run for project: {config.project_id} ({config.project_name})")
    print("Contract source: investment_system/research/schemas/output.schema.yaml")
    print("Project output spec: output_spec.yaml")
    print()
    output_types = list_output_types(config)
    print(f"Output types ({len(output_types)}):")
    for output_type in output_types:
        contract = get_output_contract(config, output_type)
        required = contract.get("required_fields", []) or []
        deprecated = contract.get("deprecated_fields", []) or []
        legacy_display = contract.get("legacy_display_fields", []) or []
        try:
            sample_sector = config.raw.get("sectors", [{}])[0].get("sector_id", "")
            path = resolve_output_path(config, output_type, sample_sector if output_type == "sector_card" else None)
        except Exception as exc:
            path = f"(unresolved: {exc})"
        print(f"  - {output_type}")
        print(f"      primary_key: {contract.get('primary_key', [])}")
        print(f"      required_fields({len(required)}): {required}")
        print(f"      deprecated_fields({len(deprecated)}): {deprecated}")
        print(f"      legacy_display_fields({len(legacy_display)}): {legacy_display}")
        print(f"      path: {path}")
    print()
    print("No files created. No data collected.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load and validate a sector research project configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m investment_system.pipelines.sector_research.load_project "
            "--project tech_ai_semiconductor\n"
            "  python -m investment_system.pipelines.sector_research.load_project "
            "--project tech_ai_semiconductor --dry-run-paths\n"
            "  python -m investment_system.pipelines.sector_research.load_project "
            "--project tech_ai_semiconductor --json\n"
            "  python -m investment_system.pipelines.sector_research.load_project "
            "--project tech_ai_semiconductor --create-output-dirs\n"
        ),
    )
    parser.add_argument("--project", type=str, required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--no-strict", action="store_true")
    parser.add_argument(
        "--dry-run-paths",
        action="store_true",
        help="Print resolved output paths for all sectors WITHOUT creating files",
    )
    parser.add_argument(
        "--dry-run-output-contract",
        action="store_true",
        help="Print output contract and resolved paths WITHOUT creating files",
    )
    parser.add_argument(
        "--create-output-dirs",
        action="store_true",
        help="Create output directories if they do not exist (default: read-only)",
    )
    args = parser.parse_args()

    try:
        config = load_project(
            args.project,
            silent=args.quiet,
            strict=not args.no_strict,
            create_dirs=args.create_output_dirs,
        )
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[ERROR] Validation failed: {exc}", file=sys.stderr)
        return 2

    errors = [w for w in config.warnings if w.severity == "error"]
    warns = [w for w in config.warnings if w.severity == "warning"]
    raw = config.raw

    if args.dry_run_paths:
        _print_dry_run_paths(config)
        if errors:
            return 2
        return 0

    if args.dry_run_output_contract:
        _print_dry_run_output_contract(config)
        if errors:
            return 2
        return 0

    if args.json:
        result = config.to_dict()
        result["_load_status"] = "error" if errors else ("warning" if warns else "ok")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.validate_only:
        if errors:
            for w in errors:
                print(f"[ERROR] {w.code}: {w.message}", file=sys.stderr)
            return 1
        return 0
    else:
        print(f"Project: {config.project_name} ({config.project_id})")
        print(f"Research type: {config.research_type}")
        print(f"Market: {config.market}")
        print(f"Version: {config.version}")
        print(f"Created: {config.created_date or '(not set)'}")
        print()
        print(f"Research groups: {raw.get('research_group_count', 0)}")
        print(f"Sectors: {config.sector_count} total, "
              f"{raw.get('scoring_enabled_sector_count', 0)} scoring-enabled, "
              f"{raw.get('observation_only_sector_count', 0)} observation-only")
        print(f"Stocks: {raw.get('listed_stock_count', 0)} listed, "
              f"{raw.get('pending_code_resolution_count', 0)} pending code")
        print(f"Reference companies: {raw.get('reference_company_count', 0)}")
        print()
        print(f"Evidence files: {raw.get('evidence_file_count', 0)}")
        print(f"Seed documents: {config.seed_document_count}")
        print()
        print(f"Output root: {config.output_root}")
        print(f"sector_cards_root: {config.sector_cards_root}")
        print(f"sector_card_path_template: {config.sector_card_path_template}")
        print(f"sector_card_filename_pattern: {config.sector_card_filename_pattern}")
        print(f"total_tables_dir: {config.total_tables_dir}")
        print(f"logs_dir: {config.logs_dir}")
        print(f"raw_data_root: {config.raw_data_root}")
        print()
        print(f"Scoring model: {config.scoring_model}")
        print(f"  Weights: " + ", ".join(f"{k}={v:.0%}" for k, v in config.weights.items()))
        print()
        print(f"Quality target: {config.quality_grade_target}")
        print(f"  require_sources: {config.require_sources}")
        print(f"  allow_placeholders: {config.allow_placeholders}")
        print()
        print(f"Existing outputs indexed: {config.existing_output_count}")
        print()

        if warns:
            print(f"Warnings ({len(warns)}):")
            for w in warns:
                print(f"  [{w.code}] {w.message}")
            print()

        if errors:
            print(f"ERRORS ({len(errors)}):")
            for w in errors:
                print(f"  [{w.code}] {w.message}")
            print()

        if not errors and not warns:
            print("Validation: PASSED — no warnings or errors.")

    if errors:
        return 2
    if warns:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
