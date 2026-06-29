"""CLI command map for the sector-research-orchestrator skill."""

from __future__ import annotations

from investment_system.core.command_dispatch import SkillCommand, dispatch_skill_commands

COMMANDS = {
    "run-stage": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Run one standardized project-aware workflow stage.",
    ),
    "scope-check": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Run the standardized scope check for one sector.",
        ("--stage", "scope_check"),
    ),
    "publish-gate": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Run publish dry-run checks; does not write formal outputs.",
        ("--stage", "publish_gate"),
    ),
    "publish-sector-card-only": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Publish one sector card only; requires --confirm-publish.",
        ("--stage", "publish_sector_card_only", "--publish-scope", "sector_card_only"),
    ),
    "prepare-publish": SkillCommand(
        "sector_research_orchestrator.publish",
        "Prepare or execute the tightly scoped formal publish flow.",
        ("--dry-run", "--no-overwrite", "--publish-scope", "sector_card_only"),
    ),
    "promote-candidate": SkillCommand(
        "sector_research_orchestrator.promote",
        "Promote candidate outputs into gated formal staging.",
        ("--require-audit-pass",),
        requires_flag="--apply-promotion",
    ),
    "post-publish-check": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Run post-publish checks for an already published sector card.",
        ("--stage", "post_publish_check"),
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_skill_commands("sector-research-orchestrator", COMMANDS, argv)
