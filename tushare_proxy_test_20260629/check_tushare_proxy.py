from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests


CONFIG_LOCAL = Path(__file__).resolve().with_name("config.local.json")


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def ymd(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")


def previous_weekday() -> str:
    day = datetime.now() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.strftime("%Y%m%d")


def call_api(
    session: requests.Session,
    base_url: str,
    token: str,
    api_name: str,
    params: dict[str, Any],
    fields: str,
    timeout: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    payload = {
        "api_name": api_name,
        "token": token,
        "params": params,
        "fields": fields,
    }
    try:
        resp = session.post(base_url, json=payload, timeout=timeout)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        text = resp.text
        result: dict[str, Any] = {
            "api_name": api_name,
            "http_status": resp.status_code,
            "elapsed_ms": elapsed_ms,
        }
        try:
            data = resp.json()
        except Exception:
            result.update(
                {
                    "status": "ERROR",
                    "error": f"non-json response: {text[:200]}",
                }
            )
            return result

        result["code"] = data.get("code")
        result["msg"] = data.get("msg")
        if resp.status_code != 200 or data.get("code") != 0:
            result["status"] = "ERROR"
            return result

        data_block = data.get("data") or {}
        columns = data_block.get("fields") or []
        items = data_block.get("items") or []
        result.update(
            {
                "status": "OK" if items else "EMPTY",
                "row_count": len(items),
                "fields": columns,
                "sample": [dict(zip(columns, row)) for row in items[:3]],
            }
        )
        return result
    except Exception as exc:
        return {
            "api_name": api_name,
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }


def sdk_smoke(base_url: str, token: str, timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import tushare as ts

        pro = ts.pro_api(token)
        pro._DataApi__http_url = base_url.rstrip("/")
        df = pro.query(
            "daily",
            ts_code="000001.SZ",
            start_date=ymd(14),
            end_date=ymd(1),
            fields="ts_code,trade_date,open,close,vol",
        )
        return {
            "api_name": "sdk_daily",
            "status": "OK" if not df.empty else "EMPTY",
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "row_count": int(len(df)),
            "fields": list(df.columns),
            "sample": df.head(3).to_dict(orient="records"),
            "tushare_version": getattr(ts, "__version__", ""),
        }
    except Exception as exc:
        return {
            "api_name": "sdk_daily",
            "status": "ERROR",
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        }


def write_summary(results: list[dict[str, Any]], out_path: Path, base_url: str, token_len: int) -> None:
    ok = sum(1 for item in results if item.get("status") == "OK")
    empty = sum(1 for item in results if item.get("status") == "EMPTY")
    error = sum(1 for item in results if item.get("status") == "ERROR")
    lines = [
        "# Tushare Proxy Smoke Test",
        "",
        f"- run_time: {datetime.now().isoformat(timespec='seconds')}",
        f"- base_url: {base_url}",
        f"- token_length: {token_len}",
        f"- ok: {ok}",
        f"- empty: {empty}",
        f"- error: {error}",
        "",
        "| api | status | rows | code | message/error | elapsed_ms |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for item in results:
        message = item.get("error") or item.get("msg") or ""
        message = str(message).replace("|", "/").replace("\n", " ")[:160]
        lines.append(
            "| {api} | {status} | {rows} | {code} | {message} | {elapsed} |".format(
                api=item.get("api_name", ""),
                status=item.get("status", ""),
                rows=item.get("row_count", ""),
                code=item.get("code", ""),
                message=message,
                elapsed=item.get("elapsed_ms", ""),
            )
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="")
    parser.add_argument("--config", default=str(CONFIG_LOCAL))
    parser.add_argument("--pause", type=float, default=0.7)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--skip-sdk", action="store_true")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    token = os.environ.get("TUSHARE_TEST_TOKEN") or config.get("token")
    base_url = (
        args.base_url
        or os.environ.get("TUSHARE_TEST_HTTP_URL")
        or config.get("base_url")
        or "https://fast.xiaodefa.cn"
    ).rstrip("/")
    if not token:
        raise SystemExit("Missing token. Set TUSHARE_TEST_TOKEN or create config.local.json.")

    session = requests.Session()
    session.trust_env = False
    session.headers.update(
        {
            "Accept-Encoding": config.get("accept_encoding", "gzip"),
            "User-Agent": config.get("user_agent", "tushare-proxy-smoke-test/1.0"),
        }
    )

    start_date = ymd(14)
    end_date = ymd(1)
    minute_date = previous_weekday()
    tests = [
        {
            "api_name": "stock_basic",
            "params": {"exchange": "", "list_status": "L"},
            "fields": "ts_code,symbol,name,area,industry,list_date",
        },
        {
            "api_name": "trade_cal",
            "params": {"exchange": "SSE", "start_date": start_date, "end_date": end_date},
            "fields": "exchange,cal_date,is_open,pretrade_date",
        },
        {
            "api_name": "daily",
            "params": {"ts_code": "000001.SZ", "start_date": start_date, "end_date": end_date},
            "fields": "ts_code,trade_date,open,high,low,close,vol,amount",
        },
        {
            "api_name": "daily_basic",
            "params": {"ts_code": "000001.SZ", "start_date": start_date, "end_date": end_date},
            "fields": "ts_code,trade_date,close,turnover_rate,pe_ttm,pb,total_mv,circ_mv",
        },
        {
            "api_name": "income",
            "params": {"ts_code": "000001.SZ", "period": "20250331"},
            "fields": "ts_code,ann_date,f_ann_date,end_date,report_type,total_revenue,n_income",
        },
        {
            "api_name": "balancesheet",
            "params": {"ts_code": "000001.SZ", "period": "20250331"},
            "fields": "ts_code,ann_date,f_ann_date,end_date,total_assets,total_liab,total_hldr_eqy_exc_min_int",
        },
        {
            "api_name": "cashflow",
            "params": {"ts_code": "000001.SZ", "period": "20250331"},
            "fields": "ts_code,ann_date,f_ann_date,end_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act",
        },
        {
            "api_name": "fina_indicator",
            "params": {"ts_code": "000001.SZ", "period": "20250331"},
            "fields": "ts_code,ann_date,end_date,eps,roe,netprofit_margin,grossprofit_margin",
        },
        {
            "api_name": "index_daily",
            "params": {"ts_code": "000001.SH", "start_date": start_date, "end_date": end_date},
            "fields": "ts_code,trade_date,open,close,pct_chg,vol,amount",
        },
        {
            "api_name": "fund_basic",
            "params": {"market": "E"},
            "fields": "ts_code,name,management,custodian,fund_type,found_date",
        },
        {
            "api_name": "fund_daily",
            "params": {"ts_code": "510300.SH", "start_date": start_date, "end_date": end_date},
            "fields": "ts_code,trade_date,open,close,vol,amount",
        },
        {
            "api_name": "cb_basic",
            "params": {},
            "fields": "ts_code,bond_short_name,stk_code,stk_short_name,maturity,conv_start_date,conv_end_date",
        },
        {
            "api_name": "fut_basic",
            "params": {"exchange": "DCE", "fut_type": "1"},
            "fields": "ts_code,symbol,name,list_date,delist_date",
        },
        {
            "api_name": "opt_basic",
            "params": {"exchange": "DCE"},
            "fields": "ts_code,name,exercise_type,list_date,delist_date",
        },
        {
            "api_name": "moneyflow",
            "params": {"ts_code": "000001.SZ", "start_date": start_date, "end_date": end_date},
            "fields": "ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_lg_amount,sell_lg_amount,net_mf_amount",
        },
        {
            "api_name": "hk_basic",
            "params": {},
            "fields": "ts_code,name,fullname,enname,market,list_status,list_date",
        },
        {
            "api_name": "shibor",
            "params": {"start_date": start_date, "end_date": end_date},
            "fields": "date,on,1w,2w,1m,3m,6m,1y",
        },
        {
            "api_name": "report_rc",
            "params": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": end_date},
            "fields": "ts_code,name,report_date,org_name,quarter,eps,pe",
        },
        {
            "api_name": "research_report",
            "params": {"ts_code": "000001.SZ", "start_date": "20250101", "end_date": end_date},
            "fields": "ts_code,name,title,org_name,author,publish_date",
        },
        {
            "api_name": "anns_d",
            "params": {"ts_code": "000001.SZ", "ann_date": minute_date},
            "fields": "ann_date,ts_code,name,title,url",
        },
        {
            "api_name": "irm_qa_sz",
            "params": {"ts_code": "000001.SZ", "trade_date": minute_date},
            "fields": "ts_code,name,trade_date,q,a,pub_time,industry",
        },
        {
            "api_name": "ths_hot",
            "params": {"trade_date": minute_date, "market": "热股"},
            "fields": "ts_code,ts_name,hot,concept,rank_time",
        },
        {
            "api_name": "cn_gdp",
            "params": {},
            "fields": "quarter,gdp,gdp_yoy,pi,si,ti",
        },
        {
            "api_name": "stk_mins",
            "params": {
                "ts_code": "000001.SZ",
                "freq": "1min",
                "start_date": f"{minute_date[:4]}-{minute_date[4:6]}-{minute_date[6:]} 09:30:00",
                "end_date": f"{minute_date[:4]}-{minute_date[4:6]}-{minute_date[6:]} 09:40:00",
            },
            "fields": "ts_code,trade_time,open,close,high,low,vol,amount",
        },
    ]

    results: list[dict[str, Any]] = []
    if not args.skip_sdk:
        results.append(sdk_smoke(base_url, token, args.timeout))
        time.sleep(args.pause)

    for test in tests:
        results.append(
            call_api(
                session=session,
                base_url=base_url,
                token=token,
                api_name=test["api_name"],
                params=test["params"],
                fields=test["fields"],
                timeout=args.timeout,
            )
        )
        time.sleep(args.pause)

    out_dir = Path(__file__).resolve().parent
    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary(results, out_dir / "summary.md", base_url, len(token))

    print((out_dir / "summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
