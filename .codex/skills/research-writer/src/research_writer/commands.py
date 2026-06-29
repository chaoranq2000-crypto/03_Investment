"""CLI command map for the research-writer skill."""

from __future__ import annotations

from investment_system.core.command_dispatch import SkillCommand, dispatch_skill_commands

COMMANDS = {
    "generate-candidate": SkillCommand(
        "research_writer.candidate_outputs",
        "Build isolated sector candidate outputs under the project audit directory.",
        ("--candidate-only",),
        requires_flag="--write-candidate",
    ),
    "build-dry-run": SkillCommand(
        "research_writer.dry_run_outputs",
        "Build project-aware dry-run output records.",
        requires_flag="--write-dry-run",
    ),
    "build-mock": SkillCommand(
        "research_writer.mock_outputs",
        "Build project-aware mock output records.",
        requires_flag="--write-mock",
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_skill_commands("research-writer", COMMANDS, argv)
