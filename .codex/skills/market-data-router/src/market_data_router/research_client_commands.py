"""Market-data CLI commands backed by the shared ResearchClient."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from investment_system.core.project_loader import get_stocks_for_sector, load_project
from investment_system.core.data_sources.research_client import ResearchClient, tencent_code


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


def _run_daily_kline(args: argparse.Namespace) -> int:
    targets = _resolve_targets(args)
    payload: dict[str, Any] = {
        "command": "daily-kline",
        "dry_run": not args.fetch,
        "route": "BaoStock -> Tencent direct fallback",
        "targets": targets,
    }
    if args.fetch:
        rows_by_code: dict[str, Any] = {}
        with ResearchClient() as client:
            for target in targets:
                code = target["stock_code"]
                market = target["market"]
                rows = client.get_daily_kline(code, market)
                rows_by_code[code] = rows[-args.rows :]
        payload["rows"] = rows_by_code
    _emit(payload, args.format)
    return 0


def _run_tencent_daily(args: argparse.Namespace) -> int:
    if args.symbol:
        symbol = args.symbol
    else:
        code, market, _full_code = _split_code_market(args.code, args.market)
        symbol = tencent_code(code, market)
    payload: dict[str, Any] = {
        "command": "tencent-daily",
        "dry_run": not args.fetch,
        "route": "Tencent direct HTTP",
        "symbol": symbol,
    }
    if args.fetch:
        with ResearchClient() as client:
            payload["rows"] = client.get_tencent_direct(symbol)[-args.rows :]
    _emit(payload, args.format)
    return 0


def _run_fund_flow(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "command": "fund-flow",
        "dry_run": not args.fetch,
        "route": "AKShare individual fund flow",
        "stock": args.stock,
    }
    if args.fetch:
        with ResearchClient() as client:
            payload["rows"] = client.get_akshare_individual_fund_flow(args.stock)[-args.rows :]
    _emit(payload, args.format)
    return 0


def _run_index_daily(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "command": "index-daily",
        "dry_run": not args.fetch,
        "route": "AKShare Sina index daily",
        "symbol": args.symbol,
    }
    if args.fetch:
        with ResearchClient() as client:
            payload["rows"] = client.get_akshare_index_daily(args.symbol)[-args.rows :]
    _emit(payload, args.format)
    return 0


def _run_stock_info(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "command": "stock-info",
        "dry_run": not args.fetch,
        "route": "AKShare A-share code/name list",
    }
    if args.fetch:
        with ResearchClient() as client:
            payload["rows"] = client.get_stock_info()[: args.rows]
    _emit(payload, args.format)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    daily = sub.add_parser("daily-kline", help="Route daily K-line requests.")
    _add_common(daily)
    daily.add_argument("--project")
    daily.add_argument("--sector-id")
    daily.add_argument("--code")
    daily.add_argument("--market", choices=["SH", "SZ"], default="SZ")
    daily.add_argument("--limit", type=int, default=1)
    daily.add_argument("--rows", type=int, default=5)
    daily.set_defaults(func=_run_daily_kline)

    tencent = sub.add_parser("tencent-daily", help="Route Tencent direct daily K-line requests.")
    _add_common(tencent)
    tencent.add_argument("--symbol")
    tencent.add_argument("--code")
    tencent.add_argument("--market", choices=["SH", "SZ"], default="SZ")
    tencent.add_argument("--rows", type=int, default=5)
    tencent.set_defaults(func=_run_tencent_daily)

    fund = sub.add_parser("fund-flow", help="Route individual fund-flow requests.")
    _add_common(fund)
    fund.add_argument("--stock", required=True)
    fund.add_argument("--rows", type=int, default=5)
    fund.set_defaults(func=_run_fund_flow)

    index = sub.add_parser("index-daily", help="Route index daily K-line requests.")
    _add_common(index)
    index.add_argument("--symbol", default="sh000001")
    index.add_argument("--rows", type=int, default=5)
    index.set_defaults(func=_run_index_daily)

    stock_info = sub.add_parser("stock-info", help="Route A-share code/name list requests.")
    _add_common(stock_info)
    stock_info.add_argument("--rows", type=int, default=20)
    stock_info.set_defaults(func=_run_stock_info)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
