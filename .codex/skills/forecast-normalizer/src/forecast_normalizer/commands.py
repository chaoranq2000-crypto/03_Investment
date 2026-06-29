"""CLI command map for the forecast-normalizer skill."""

from __future__ import annotations

import sys

from investment_system.core.command_dispatch import SkillCommand, dispatch_skill_commands


COMMANDS = {
    "status": SkillCommand(
        "forecast_normalizer.commands",
        "Show migration status for forecast commands.",
        ("_status",),
    ),
    "tushare-fetch": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare forecast datasets; dry-run by default.",
        ("tushare-fetch", "--group", "forecast"),
    ),
    "report-rc": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare broker forecast report_rc rows.",
        ("tushare-fetch", "--group", "forecast", "--dataset", "report_rc"),
    ),
    "research-report-index": SkillCommand(
        "tushare_data_router.commands",
        "Preview or fetch Tushare research-report metadata rows for forecast sourcing.",
        ("tushare-fetch", "--group", "forecast", "--dataset", "research_report"),
    ),
    "normalize-forecast-fields": SkillCommand(
        "forecast_normalizer.forecast_tools",
        "Preview forecast field normalization and source-label rules.",
        ("normalize-forecast-fields",),
    ),
    "audit-forecast-source-count": SkillCommand(
        "forecast_normalizer.forecast_tools",
        "Audit forecast source count from a Tushare cache or manifest JSON.",
        ("audit-forecast-source-count",),
    ),
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "_status":
        print("forecast-normalizer CLI exists; Tushare report_rc/research_report previews are now routed through tushare-fetch.")
        print("Do not assume Wind or iFind access; use curated/user-provided forecasts for formal outputs.")
        return 0
    if not args or args[0] in {"-h", "--help"}:
        return dispatch_skill_commands("forecast-normalizer", COMMANDS, args)
    return dispatch_skill_commands("forecast-normalizer", COMMANDS, args)
