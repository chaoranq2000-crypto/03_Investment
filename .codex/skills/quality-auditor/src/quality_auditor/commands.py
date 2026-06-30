"""CLI command map for the quality-auditor skill."""

from __future__ import annotations

from investment_system.core.command_dispatch import SkillCommand, dispatch_skill_commands

COMMANDS = {
    "runtime-contract-check": SkillCommand(
        "quality_auditor.runtime_contract_check",
        "Check active project runtime contracts for scope checks.",
    ),
    "stock-universe": SkillCommand(
        "quality_auditor.stock_universe",
        "Audit stock universe coverage and canonical sector references.",
    ),
    "evidence-bindings": SkillCommand(
        "quality_auditor.evidence_bindings",
        "Audit run-manifest evidence bindings.",
    ),
    "evidence-schema": SkillCommand(
        "quality_auditor.evidence_schema",
        "Audit canonical evidence YAML schema/source-id readiness.",
    ),
    "evidence-coverage": SkillCommand(
        "quality_auditor.evidence_coverage",
        "Audit source/evidence coverage.",
    ),
    "evidence-gate": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Run the standardized evidence gate for one sector.",
        ("--stage", "evidence_gate"),
    ),
    "candidate-gate": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Run the standardized candidate gate for one sector.",
        ("--stage", "candidate_gate"),
    ),
    "publish-gate": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Run publish dry-run checks for one sector.",
        ("--stage", "publish_gate"),
    ),
    "post-publish-check": SkillCommand(
        "sector_research_orchestrator.stage_runner",
        "Run post-publish checks for an already published sector card.",
        ("--stage", "post_publish_check"),
    ),
    "gated-outputs": SkillCommand(
        "quality_auditor.gated_outputs",
        "Audit gated formal staging outputs.",
    ),
    "output-schema": SkillCommand(
        "quality_auditor.output_schema",
        "Audit output schema readiness.",
    ),
    "mock-outputs": SkillCommand(
        "quality_auditor.mock_outputs",
        "Audit mock output fixtures.",
    ),
    "dry-run-outputs": SkillCommand(
        "quality_auditor.dry_run_outputs",
        "Audit dry-run output artifacts.",
    ),
    "generator-previews": SkillCommand(
        "quality_auditor.generator_previews",
        "Audit generator preview artifacts.",
    ),
    "validate-outputs": SkillCommand(
        "quality_auditor.validate_outputs",
        "Validate project-aware generated outputs.",
    ),
    "tushare-raw-cache": SkillCommand(
        "quality_auditor.tushare_raw_cache",
        "Audit skill-owned Tushare raw-cache envelopes for schema and token leakage.",
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_skill_commands("quality-auditor", COMMANDS, argv)
