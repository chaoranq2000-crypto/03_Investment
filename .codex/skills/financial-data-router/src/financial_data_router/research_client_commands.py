"""Financial-data CLI commands backed by the shared ResearchClient."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from investment_system.core.project_loader import get_stocks_for_sector, load_project
from investment_system.scripts.research_client import ResearchClient


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _print_text(payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        print(f"{key}: {value}")


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        _print_json(payload)
    else:
        _print_text(payload)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--fetch", action="store_true", help="Actually call external data sources.")


def _split_code_market(code: str, fallback_market: str = "SZ") -> tuple[str, str, str]:
    full_code = code.strip()
    if "." in full_code:
        raw_code, raw_market = full_code.split(".", 1)
        return raw_code, raw_market.upper(), full_code
    return full_code, fallback_market, f"{full_code}.{fallback_market}"


def _resolve_targets(args: argparse.Namespace) -> list[dict[str, str]]:
    if args.code:
        code, market, full_code = _split_code_market(args.code, args.market)
        return [{"stock_code": code, "market": market, "full_code": full_code}]
    if not args.project or not args.sector_id:
        raise SystemExit("--code/--market or --project/--sector-id is required")
    config = load_project(args.project)
    stocks = get_stocks_for_sector(config, args.sector_id)
    limit = max(1, args.limit)
    targets = []
    for stock in stocks[:limit]:
        code, market, full_code = _split_code_market(str(stock.get("code", "")))
        targets.append(
            {
                "stock_code": code,
                "market": market,
                "full_code": full_code,
                "stock_name": str(stock.get("name", "")),
            }
        )
    return targets


def _parse_years(value: str) -> list[int]:
    years: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if part:
            years.append(int(part))
    return years


def _run_profit(args: argparse.Namespace) -> int:
    targets = _resolve_targets(args)
    years = _parse_years(args.years)
    payload: dict[str, Any] = {
        "command": "profit",
        "dry_run": not args.fetch,
        "route": "BaoStock query_profit_data",
        "years": years,
        "targets": targets,
    }
    if args.fetch:
        rows_by_code: dict[str, Any] = {}
        with ResearchClient() as client:
            for target in targets:
                code = target["stock_code"]
                market = target["market"]
                rows_by_code[code] = client.get_profit(code, market, years)[-args.rows :]
        payload["rows"] = rows_by_code
    _emit(payload, args.format)
    return 0


def _run_financial_indicator(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "command": "financial-indicator",
        "dry_run": not args.fetch,
        "route": "AKShare financial analysis indicator",
        "code": args.code,
        "start_year": args.start_year,
    }
    if args.fetch:
        with ResearchClient() as client:
            payload["rows"] = client.get_akshare_financial_indicator(args.code)[-args.rows :]
    _emit(payload, args.format)
    return 0


def _run_normalize_financials(args: argparse.Namespace) -> int:
    config = load_project(args.project)
    stocks = get_stocks_for_sector(config, args.sector_id)
    payload: dict[str, Any] = {
        "command": "normalize-financials",
        "dry_run": True,
        "status": "preview_only",
        "project": args.project,
        "sector_id": args.sector_id,
        "target_stock_count": len(stocks),
        "fields": [
            "revenue",
            "net_profit",
            "gross_margin",
            "net_margin",
            "eps_ttm",
            "total_share",
            "pe_ttm",
            "ps_ttm",
        ],
        "note": "Normalization writes remain deferred; generated outputs must record source period and missing fields.",
    }
    _emit(payload, args.format)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    profit = sub.add_parser("profit", help="Route profit/financial rows through BaoStock.")
    _add_common(profit)
    profit.add_argument("--project")
    profit.add_argument("--sector-id")
    profit.add_argument("--code")
    profit.add_argument("--market", choices=["SH", "SZ"], default="SZ")
    profit.add_argument("--years", default="2024,2025")
    profit.add_argument("--limit", type=int, default=1)
    profit.add_argument("--rows", type=int, default=8)
    profit.set_defaults(func=_run_profit)

    indicator = sub.add_parser("financial-indicator", help="Route AKShare financial indicator requests.")
    _add_common(indicator)
    indicator.add_argument("--code", required=True)
    indicator.add_argument("--start-year", default="2024")
    indicator.add_argument("--rows", type=int, default=8)
    indicator.set_defaults(func=_run_financial_indicator)

    normalize = sub.add_parser("normalize-financials", help="Preview normalized financial output fields.")
    normalize.add_argument("--project", required=True)
    normalize.add_argument("--sector-id", required=True)
    normalize.add_argument("--format", choices=["text", "json"], default="text")
    normalize.set_defaults(func=_run_normalize_financials)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
