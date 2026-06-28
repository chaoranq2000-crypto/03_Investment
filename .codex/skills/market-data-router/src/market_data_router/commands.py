"""CLI command map for the market-data-router skill."""

from __future__ import annotations

from investment_system.core.legacy_cli import LegacyCommand, dispatch_legacy_commands

COMMANDS = {
    "daily-kline": LegacyCommand(
        "market_data_router.research_client_commands",
        "Preview or fetch daily K-line data through ResearchClient.",
        ("daily-kline",),
    ),
    "fund-flow": LegacyCommand(
        "market_data_router.research_client_commands",
        "Preview or fetch individual fund-flow data through ResearchClient.",
        ("fund-flow",),
    ),
    "index-daily": LegacyCommand(
        "market_data_router.research_client_commands",
        "Preview or fetch index daily K-line data through ResearchClient.",
        ("index-daily",),
    ),
    "stock-info": LegacyCommand(
        "market_data_router.research_client_commands",
        "Preview or fetch the A-share code/name list through ResearchClient.",
        ("stock-info",),
    ),
    "tencent-daily": LegacyCommand(
        "market_data_router.research_client_commands",
        "Preview or fetch Tencent direct daily K-line data.",
        ("tencent-daily",),
    ),
    "tushare-ping": LegacyCommand(
        "investment_system.core.data_sources.tushare_client",
        "Run the configured Tushare ping diagnostic.",
        ("--ping",),
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_legacy_commands("market-data-router", COMMANDS, argv)
