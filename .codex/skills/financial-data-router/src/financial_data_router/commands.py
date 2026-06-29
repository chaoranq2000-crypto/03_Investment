"""CLI command map for the financial-data-router skill."""

from __future__ import annotations

from investment_system.core.command_dispatch import SkillCommand, dispatch_skill_commands

COMMANDS = {
    "financial-indicator": SkillCommand(
        "financial_data_router.research_client_commands",
        "Preview or fetch AKShare financial indicators through ResearchClient.",
        ("financial-indicator",),
    ),
    "normalize-financials": SkillCommand(
        "financial_data_router.research_client_commands",
        "Preview normalized financial output fields and source-period requirements.",
        ("normalize-financials",),
    ),
    "profit": SkillCommand(
        "financial_data_router.research_client_commands",
        "Preview or fetch BaoStock profit rows through ResearchClient.",
        ("profit",),
    ),
    "income": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare income statement rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "income"),
    ),
    "balancesheet": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare balance-sheet rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "balancesheet"),
    ),
    "cashflow": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare cash-flow rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "cashflow"),
    ),
    "fina-indicator": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare financial-indicator rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "fina_indicator"),
    ),
    "main-business": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare main-business composition rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "fina_mainbz"),
    ),
    "holders": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare holder rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "top10_holders"),
    ),
    "share-float": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare restricted-share unlock rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "share_float"),
    ),
    "dividend": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare dividend rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "dividend"),
    ),
    "repurchase": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare repurchase rows.",
        ("tushare-fetch", "--group", "financial", "--dataset", "repurchase"),
    ),
    "valuation-snapshot": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare daily_basic valuation rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "daily_basic"),
    ),
    "tushare-ping": SkillCommand(
        "investment_system.core.data_sources.tushare_client",
        "Run the configured Tushare ping diagnostic before financial pulls.",
        ("--ping",),
    ),
    "tushare-fetch": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare financial datasets; dry-run by default.",
        ("tushare-fetch", "--group", "financial"),
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_skill_commands("financial-data-router", COMMANDS, argv)
