"""CLI command map for the financial-data-router skill."""

from __future__ import annotations

from investment_system.core.legacy_cli import LegacyCommand, dispatch_legacy_commands

COMMANDS = {
    "financial-indicator": LegacyCommand(
        "financial_data_router.research_client_commands",
        "Preview or fetch AKShare financial indicators through ResearchClient.",
        ("financial-indicator",),
    ),
    "normalize-financials": LegacyCommand(
        "financial_data_router.research_client_commands",
        "Preview normalized financial output fields and source-period requirements.",
        ("normalize-financials",),
    ),
    "profit": LegacyCommand(
        "financial_data_router.research_client_commands",
        "Preview or fetch BaoStock profit rows through ResearchClient.",
        ("profit",),
    ),
    "tushare-ping": LegacyCommand(
        "investment_system.core.data_sources.tushare_client",
        "Run the configured Tushare ping diagnostic before financial pulls.",
        ("--ping",),
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_legacy_commands("financial-data-router", COMMANDS, argv)
