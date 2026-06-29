"""CLI command map for the market-data-router skill."""

from __future__ import annotations

from investment_system.core.command_dispatch import SkillCommand, dispatch_skill_commands

COMMANDS = {
    "daily-kline": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare daily K-line data; dry-run by default.",
        ("tushare-fetch", "--group", "market", "--dataset", "daily"),
    ),
    "daily-basic": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare daily_basic valuation/turnover rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "daily_basic"),
    ),
    "moneyflow": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare individual-stock moneyflow rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "moneyflow"),
    ),
    "dragon-tiger": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare dragon-tiger list rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "top_list"),
    ),
    "margin": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare margin-detail rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "margin_detail"),
    ),
    "limit-list": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare limit-up/limit-down list rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "limit_list_d"),
    ),
    "sector-theme": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare theme/heat rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "ths_hot"),
    ),
    "fund-flow": SkillCommand(
        "market_data_router.research_client_commands",
        "Preview or fetch individual fund-flow data through ResearchClient.",
        ("fund-flow",),
    ),
    "index-daily": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare index daily rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "index_daily"),
    ),
    "stock-info": SkillCommand(
        "market_data_router.research_client_commands",
        "Preview or fetch the A-share code/name list through ResearchClient.",
        ("stock-info",),
    ),
    "tencent-daily": SkillCommand(
        "market_data_router.research_client_commands",
        "Preview or fetch Tencent direct daily K-line data.",
        ("tencent-daily",),
    ),
    "tushare-ping": SkillCommand(
        "investment_system.core.data_sources.tushare_client",
        "Run the configured Tushare ping diagnostic.",
        ("--ping",),
    ),
    "tushare-fetch": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare market datasets; dry-run by default.",
        ("tushare-fetch", "--group", "market"),
    ),
    "fund-etf-daily": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare fund/ETF daily rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "fund_daily"),
    ),
    "convertible-bond-daily": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare convertible-bond daily rows.",
        ("tushare-fetch", "--group", "market", "--dataset", "cb_daily"),
    ),
}


def main(argv: list[str] | None = None) -> int:
    return dispatch_skill_commands("market-data-router", COMMANDS, argv)
