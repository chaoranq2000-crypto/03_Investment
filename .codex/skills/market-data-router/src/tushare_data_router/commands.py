"""Shared Tushare-first fetch command for data skills."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from typing import Any

from investment_system.core.data_sources.tushare_client import get_tushare_pro
from investment_system.core.project_loader import get_stocks_for_sector, load_project

from .datasets import DatasetSpec, get_dataset, list_group_datasets, list_groups
from .rate_limit import RateLimitPolicy
from .raw_cache import (
    build_envelope,
    build_manifest_record,
    cache_path,
    manifest_path,
    write_json,
    write_manifest,
)


def _today_compact() -> str:
    return date.today().strftime("%Y%m%d")


def _previous_date_compact() -> str:
    day = date.today() - timedelta(days=1)
    return day.strftime("%Y%m%d")


def _run_date() -> str:
    return date.today().isoformat()


def _split_code_market(code: str, fallback_market: str = "SZ") -> tuple[str, str, str]:
    value = code.strip().upper()
    if "." in value:
        raw_code, raw_market = value.split(".", 1)
        return raw_code, raw_market, f"{raw_code}.{raw_market}"
    return value, fallback_market.upper(), f"{value}.{fallback_market.upper()}"


def _stock_target(code: str, market: str, name: str = "") -> dict[str, str]:
    raw_code, raw_market, full_code = _split_code_market(code, market)
    return {
        "stock_code": raw_code,
        "market": raw_market,
        "ts_code": full_code,
        "stock_name": name,
    }


def _resolve_targets(args: argparse.Namespace, spec: DatasetSpec) -> list[dict[str, str]]:
    if spec.target_mode == "all":
        return [{"target_key": "all"}]
    if spec.target_mode == "single":
        code = args.code or dict(spec.default_params).get("ts_code", "") or "all"
        if code and code != "all" and any(code.endswith(suffix) for suffix in (".SZ", ".SH", ".BJ")):
            target = _stock_target(code, args.market)
            target["target_key"] = target["ts_code"]
            return [target]
        return [{"target_key": str(code or spec.dataset)}]

    if args.code:
        target = _stock_target(args.code, args.market)
        target["target_key"] = target["ts_code"]
        return [target]

    if not args.project or not args.sector_id:
        raise SystemExit("--code/--market or --project/--sector-id is required for stock-scoped datasets")
    config = load_project(args.project, create_dirs=False, strict=False, silent=True)
    stocks = get_stocks_for_sector(config, args.sector_id)
    targets: list[dict[str, str]] = []
    for stock in stocks[: max(1, args.limit)]:
        code = str(stock.get("code") or stock.get("stock_code") or "")
        if not code:
            continue
        name = str(stock.get("name") or stock.get("stock_name") or "")
        target = _stock_target(code, args.market, name)
        target["target_key"] = target["ts_code"]
        targets.append(target)
    return targets


def _date_params(args: argparse.Namespace, spec: DatasetSpec) -> dict[str, str]:
    params: dict[str, str] = {}
    if args.period:
        params["period"] = args.period
    if args.start_date:
        params["start_date"] = args.start_date
    if args.end_date:
        params["end_date"] = args.end_date
    if (
        not args.period
        and not args.start_date
        and not args.end_date
        and spec.target_mode != "all"
        and not spec.date_param
    ):
        params.setdefault("start_date", args.default_start_date)
        params.setdefault("end_date", args.default_end_date)
    if spec.date_param:
        value = args.trade_date or args.ann_date or args.default_end_date
        params[spec.date_param] = value
    if args.trade_date and not spec.date_param:
        params["trade_date"] = args.trade_date
    if args.ann_date and not spec.date_param:
        params["ann_date"] = args.ann_date
    return params


def _request_for(args: argparse.Namespace, spec: DatasetSpec, target: dict[str, str]) -> dict[str, Any]:
    params = spec.params()
    params.update(_date_params(args, spec))
    if spec.target_mode == "stock":
        params["ts_code"] = target["ts_code"]
    elif spec.target_mode == "single":
        if "ts_code" not in params and target.get("ts_code"):
            params["ts_code"] = target["ts_code"]
    if args.params_json:
        extra = json.loads(args.params_json)
        if not isinstance(extra, dict):
            raise SystemExit("--params-json must decode to a JSON object")
        params.update(extra)
    return {
        "group": spec.group,
        "dataset": spec.dataset,
        "api_name": spec.api_name,
        "target": target,
        "params": params,
        "fields": args.fields or spec.fields,
    }


def _df_to_rows(dataframe: Any, max_rows: int) -> list[dict[str, Any]]:
    if dataframe is None:
        return []
    if hasattr(dataframe, "head") and hasattr(dataframe, "to_dict"):
        limited = dataframe.head(max_rows) if max_rows > 0 else dataframe
        return list(limited.to_dict(orient="records"))
    if isinstance(dataframe, list):
        return [row for row in dataframe[:max_rows] if isinstance(row, dict)]
    return []


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    for key, value in payload.items():
        if key == "requests" and isinstance(value, list):
            print("requests:")
            for item in value:
                print(f"- {item.get('dataset')} {item.get('target', {}).get('target_key', '')} params={item.get('params')}")
        elif key == "results" and isinstance(value, list):
            print("results:")
            for item in value:
                print(
                    f"- {item.get('dataset')} {item.get('target_key')} status={item.get('status')} "
                    f"rows={item.get('row_count')} cache={item.get('cache_path', '')}"
                )
        else:
            print(f"{key}: {value}")


def _list_payload(group: str) -> dict[str, Any]:
    datasets = [
        {
            "dataset": spec.dataset,
            "api_name": spec.api_name,
            "target_mode": spec.target_mode,
            "source_type": spec.source_type,
            "description": spec.description,
        }
        for spec in list_group_datasets(group)
    ]
    return {"command": "tushare-fetch", "dry_run": True, "group": group, "datasets": datasets}


def run_tushare_fetch(args: argparse.Namespace) -> int:
    if args.group not in list_groups():
        raise SystemExit(f"Unsupported group: {args.group}. Available: {', '.join(list_groups())}")
    if not args.dataset:
        _emit(_list_payload(args.group), args.format)
        return 0

    spec = get_dataset(args.group, args.dataset)
    targets = _resolve_targets(args, spec)
    requests = [_request_for(args, spec, target) for target in targets]
    rate_limit = RateLimitPolicy.from_env(args.interval, args.jitter)
    project_id = args.project or ""
    sector_id = args.sector_id or ""
    run_date = args.run_date or _run_date()
    payload: dict[str, Any] = {
        "command": "tushare-fetch",
        "dry_run": not args.fetch,
        "group": args.group,
        "dataset": spec.dataset,
        "api_name": spec.api_name,
        "project_id": project_id,
        "sector_id": sector_id,
        "rate_limit": {
            "interval_seconds": rate_limit.interval_seconds,
            "jitter_seconds": rate_limit.jitter_seconds,
        },
        "requests": requests,
    }
    if not args.fetch:
        payload["note"] = "Pass --fetch for live Tushare calls; pass --write-cache to persist raw envelopes."
        _emit(payload, args.format)
        return 0
    if args.write_cache is False and args.write_manifest:
        raise SystemExit("--write-manifest requires --write-cache")

    pro = get_tushare_pro()
    limiter = rate_limit
    results: list[dict[str, Any]] = []
    manifest_records: list[dict[str, Any]] = []
    for index, request in enumerate(requests):
        target = request["target"]
        target_key = str(target.get("target_key") or target.get("ts_code") or "all")
        status = "ok"
        error = ""
        rows: list[dict[str, Any]] = []
        try:
            df = pro.query(spec.api_name, **request["params"], fields=request["fields"])
            rows = _df_to_rows(df, args.rows)
        except Exception as exc:
            status = "error"
            error = f"{type(exc).__name__}: {exc}"

        result: dict[str, Any] = {
            "dataset": spec.dataset,
            "target_key": target_key,
            "status": status,
            "row_count": len(rows),
            "error": error,
            "sample": rows[: args.sample_rows],
        }
        if args.write_cache:
            envelope = build_envelope(
                dataset=spec.dataset,
                api_name=spec.api_name,
                group=spec.group,
                project_id=project_id,
                sector_id=sector_id,
                stock=target,
                params=request["params"],
                fields=request["fields"],
                rows=rows,
                row_limit=args.rows,
                fetch_status=status,
                error=error,
            )
            out_path = cache_path(spec.dataset, run_date, target_key)
            write_json(out_path, envelope)
            result["cache_path"] = str(out_path)
            manifest_records.append(
                build_manifest_record(
                    project_id=project_id,
                    sector_id=sector_id,
                    dataset=spec.dataset,
                    source_type=spec.source_type,
                    target_key=target_key,
                    cache_file=out_path,
                    envelope=envelope,
                )
            )
        results.append(result)
        if index + 1 < len(requests):
            limiter.sleep()

    if args.write_manifest and manifest_records:
        out_manifest = manifest_path(project_id or "no_project", sector_id, run_date)
        write_manifest(out_manifest, manifest_records, project_id, sector_id, run_date)
        payload["manifest_path"] = str(out_manifest)

    payload["results"] = results
    _emit(payload, args.format)
    return 0 if all(item["status"] == "ok" for item in results) else 1


def add_tushare_fetch_parser(subparsers: argparse._SubParsersAction[Any]) -> None:
    parser = subparsers.add_parser("tushare-fetch", help="Preview or fetch Tushare datasets through the shared router.")
    parser.add_argument("--group", choices=list_groups(), required=True)
    parser.add_argument("--dataset", default="", help="Dataset name within the group. Omit to list supported datasets.")
    parser.add_argument("--project", default="")
    parser.add_argument("--sector-id", default="")
    parser.add_argument("--code", default="", help="Tushare-style code such as 000001.SZ, or 6-digit code with --market.")
    parser.add_argument("--market", choices=["SH", "SZ", "BJ"], default="SZ")
    parser.add_argument("--limit", type=int, default=1, help="Max project-sector stocks for stock-scoped datasets.")
    parser.add_argument("--rows", type=int, default=2000, help="Max rows retained per request in stdout/cache.")
    parser.add_argument("--sample-rows", type=int, default=3)
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--period", default="")
    parser.add_argument("--trade-date", default="")
    parser.add_argument("--ann-date", default="")
    parser.add_argument("--default-start-date", default=(_previous_date_compact()))
    parser.add_argument("--default-end-date", default=(_today_compact()))
    parser.add_argument("--params-json", default="", help="Extra Tushare params as a JSON object.")
    parser.add_argument("--fields", default="", help="Override default field list.")
    parser.add_argument("--run-date", default="")
    parser.add_argument("--interval", type=float, default=None)
    parser.add_argument("--jitter", type=float, default=None)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--write-cache", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.set_defaults(func=run_tushare_fetch)


def build_parser(default_group: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    add_tushare_fetch_parser(sub)
    if default_group:
        parser.set_defaults(default_group=default_group)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
