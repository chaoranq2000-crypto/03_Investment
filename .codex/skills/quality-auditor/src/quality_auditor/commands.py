"""CLI command map for the quality-auditor skill."""

from __future__ import annotations

from investment_system.core.legacy_cli import LegacyCommand, dispatch_legacy_commands

COMMANDS = {
    "pipeline-readiness": LegacyCommand(
        "quality_auditor.pipeline_readiness",
        "Audit project-aware pipeline readiness.",
    ),
    "stock-universe": LegacyCommand(
        "quality_auditor.stock_universe",
        "Audit stock universe coverage and canonical sector references.",
    ),
    "evidence-bindings": LegacyCommand(
        "quality_auditor.evidence_bindings",
        "Audit run-manifest evidence bindings.",
    ),
    "evidence-schema": LegacyCommand(
        "quality_auditor.evidence_schema",
        "Audit canonical evidence YAML schema/source-id readiness.",
    ),
    "evidence-coverage": LegacyCommand(
        "quality_auditor.evidence_coverage",
        "Audit source/evidence coverage.",
    ),
    "evidence-gate": LegacyCommand(
        "sector_research_orchestrator.stage_runner",
        "Run the standardized evidence gate for one sector.",
        ("--stage", "evidence_gate"),
    ),
    "candidate-gate": LegacyCommand(
        "sector_research_orchestrator.stage_runner",
        "Run the standardized candidate gate for one sector.",
        ("--stage", "candidate_gate"),
    ),
    "publish-gate": LegacyCommand(
        "sector_research_orchestrator.stage_runner",
        "Run publish dry-run checks for one sector.",
        ("--stage", "publish_gate"),
    ),
    "post-publish-check": LegacyCommand(
        "sector_research_orchestrator.stage_runner",
        "Run post-publish checks for an already published sector card.",
        ("--stage", "post_publish_check"),
    ),
    "gated-outputs": LegacyCommand(
        "quality_auditor.gated_outputs",
        "Audit gated formal staging outputs.",
    ),
    "output-schema": LegacyCommand(
        "quality_auditor.output_schema",
        "Audit output schema readiness.",
    ),
    "mock-outputs": LegacyCommand(
        "quality_auditor.mock_outputs",
        "Audit mock output fixtures.",
    ),
    "dry-run-outputs": LegacyCommand(
        "quality_auditor.dry_run_outputs",
        "Audit dry-run output artifacts.",
    ),
    "generator-previews": LegacyCommand(
        "quality_auditor.generator_previews",
        "Audit generator preview artifacts.",
    ),
    "validate-outputs": LegacyCommand(
        "quality_auditor.validate_outputs",
        "Validate project-aware generated outputs.",
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_legacy_commands("quality-auditor", COMMANDS, argv)
