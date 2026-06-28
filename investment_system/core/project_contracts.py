"""Static project contract constants for sector-research project loading."""

from __future__ import annotations

import re

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

MD_SCAN_EXCLUDE_DIRS = frozenset({
    "docs", "templates", "schemas", ".git", ".conda",
    "node_modules", "__pycache__", ".codex",
    "projects",
    "pipelines", "scripts", "tools", "research",
    "decisions", "risk", "portfolio", "data",
})

MD_SCAN_EXCLUDE_FILES = frozenset({
    "AGENTS.md", "README.md", "README_CN.md",
    "调研日志.md", "缺失数据清单.md", "冲突数据清单.md",
    "run_manifest.yaml", "project.yaml", "sector_universe.yaml",
    "stock_universe.yaml", "scoring_rules.yaml", "output_spec.yaml",
})

SEED_MANDATORY_NOT_ALLOWED = frozenset({
    "evidence", "score", "rating", "investment_conclusion",
})

__all__ = [
    "AI_APP_FORBIDDEN_PARENTCHAINS",
    "MD_SCAN_EXCLUDE_DIRS",
    "MD_SCAN_EXCLUDE_FILES",
    "REQUIRED_OUTPUT_SPEC_FIELDS",
    "REQUIRED_PROJECT_FILES",
    "SEED_FORBIDDEN_ACTIONS",
    "SEED_FORBIDDEN_STATUSES",
    "SEED_FORBIDDEN_TYPES",
    "SEED_MANDATORY_NOT_ALLOWED",
    "STOCK_CODE_PATTERN",
]
