"""CLI command map for the evidence-miner skill."""

from __future__ import annotations

from investment_system.core.command_dispatch import SkillCommand, dispatch_skill_commands

COMMANDS = {
    "collect": SkillCommand(
        "evidence_miner.source_manifest",
        "Build a source manifest from cached official files; preview by default.",
    ),
    "draft": SkillCommand(
        "evidence_miner.draft_skeleton",
        "Build a draft evidence YAML skeleton under project audits.",
    ),
    "validate-curated": SkillCommand(
        "evidence_miner.curation_validator",
        "Validate curated evidence YAML before registration.",
    ),
    "register": SkillCommand(
        "evidence_miner.register",
        "Preview registration for one evidence YAML file.",
        ("--dry-run",),
    ),
    "register-apply": SkillCommand(
        "evidence_miner.register",
        "Apply registration for one evidence YAML file; writes run_manifest/sector binding.",
    ),
    "split-tushare-cache": SkillCommand(
        "evidence_miner.tushare_cache_split",
        "Split bundled Tushare cache records into source-level artifacts.",
    ),
    "tushare-source-manifest": SkillCommand(
        "evidence_miner.tushare_cache_split",
        "Build a source manifest from a Tushare cache file or raw-cache envelope.",
    ),
    "tushare-fetch": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare evidence-index datasets; dry-run by default.",
        ("tushare-fetch", "--group", "evidence"),
    ),
    "announcements-index": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare announcement index rows.",
        ("tushare-fetch", "--group", "evidence", "--dataset", "anns_d"),
    ),
    "research-report-index": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare research-report metadata rows.",
        ("tushare-fetch", "--group", "evidence", "--dataset", "research_report"),
    ),
    "survey-index": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare institutional-survey rows.",
        ("tushare-fetch", "--group", "evidence", "--dataset", "stk_surv"),
    ),
    "irm-qa-index": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare interactive-Q&A rows.",
        ("tushare-fetch", "--group", "evidence", "--dataset", "irm_qa_sz"),
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_skill_commands("evidence-miner", COMMANDS, argv)
