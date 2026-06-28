"""CLI command map for the evidence-miner skill."""

from __future__ import annotations

from investment_system.core.legacy_cli import LegacyCommand, dispatch_legacy_commands

COMMANDS = {
    "collect": LegacyCommand(
        "evidence_miner.source_manifest",
        "Build a source manifest from cached official files; preview by default.",
    ),
    "draft": LegacyCommand(
        "evidence_miner.draft_skeleton",
        "Build a draft evidence YAML skeleton under project audits.",
    ),
    "validate-curated": LegacyCommand(
        "evidence_miner.curation_validator",
        "Validate curated evidence YAML before registration.",
    ),
    "register": LegacyCommand(
        "evidence_miner.register",
        "Preview registration for one evidence YAML file.",
        ("--dry-run",),
    ),
    "register-apply": LegacyCommand(
        "evidence_miner.register",
        "Apply registration for one evidence YAML file; writes run_manifest/sector binding.",
    ),
    "split-tushare-cache": LegacyCommand(
        "evidence_miner.tushare_cache_split",
        "Split bundled Tushare cache records into source-level artifacts.",
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_legacy_commands("evidence-miner", COMMANDS, argv)
