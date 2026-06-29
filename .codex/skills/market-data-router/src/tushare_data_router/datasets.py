"""Dataset registry for the skill-owned Tushare router.

The registry is intentionally declarative. Adding endpoint coverage should
usually mean adding a DatasetSpec here rather than writing a new one-off script.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


TargetMode = Literal["stock", "single", "all"]


@dataclass(frozen=True)
class DatasetSpec:
    group: str
    dataset: str
    api_name: str
    fields: str
    description: str
    target_mode: TargetMode = "stock"
    source_type: str = "data_cache"
    date_param: str = ""
    default_params: tuple[tuple[str, Any], ...] = ()

    def params(self) -> dict[str, Any]:
        return dict(self.default_params)


DATASETS: tuple[DatasetSpec, ...] = (
    # market-data-router ownership
    DatasetSpec(
        "market",
        "stock_basic",
        "stock_basic",
        "ts_code,symbol,name,area,industry,list_date,list_status",
        "A-share code/name/listing-status universe.",
        target_mode="all",
        source_type="market_data",
        default_params=(("exchange", ""), ("list_status", "L")),
    ),
    DatasetSpec(
        "market",
        "trade_cal",
        "trade_cal",
        "exchange,cal_date,is_open,pretrade_date",
        "Trading calendar window.",
        target_mode="single",
        source_type="market_data",
        default_params=(("exchange", "SSE"),),
    ),
    DatasetSpec(
        "market",
        "daily",
        "daily",
        "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        "Daily A-share OHLCV.",
        source_type="market_data",
    ),
    DatasetSpec(
        "market",
        "daily_basic",
        "daily_basic",
        "ts_code,trade_date,close,turnover_rate,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,total_share,float_share,total_mv,circ_mv",
        "Daily valuation, turnover, and market-cap metrics.",
        source_type="market_data",
    ),
    DatasetSpec(
        "market",
        "adj_factor",
        "adj_factor",
        "ts_code,trade_date,adj_factor",
        "Adjustment factors for price normalization.",
        source_type="market_data",
    ),
    DatasetSpec(
        "market",
        "moneyflow",
        "moneyflow",
        "ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount,buy_lg_amount,sell_lg_amount,buy_elg_amount,sell_elg_amount,net_mf_amount",
        "Individual-stock fund-flow rows.",
        source_type="market_data",
    ),
    DatasetSpec(
        "market",
        "top_list",
        "top_list",
        "trade_date,ts_code,name,close,pct_change,turnover_rate,amount,l_sell,l_buy,l_amount,net_amount,net_rate,amount_rate,float_values,reason",
        "Dragon-tiger list rows for a trade date.",
        target_mode="single",
        source_type="market_data",
        date_param="trade_date",
    ),
    DatasetSpec(
        "market",
        "limit_list_d",
        "limit_list_d",
        "trade_date,ts_code,name,industry,close,pct_chg,amount,limit_amount,float_mv,total_mv,turnover_ratio,fd_amount,first_time,last_time,open_times,up_stat,limit_times",
        "Daily limit-up/limit-down list.",
        target_mode="single",
        source_type="market_data",
        date_param="trade_date",
    ),
    DatasetSpec(
        "market",
        "margin_detail",
        "margin_detail",
        "trade_date,ts_code,name,rzye,rqye,rzmre,rqyl,rzche,rqchl,rzrqye",
        "Stock-level margin and securities-lending detail.",
        source_type="market_data",
    ),
    DatasetSpec(
        "market",
        "index_daily",
        "index_daily",
        "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        "Index daily OHLCV.",
        target_mode="single",
        source_type="market_data",
        default_params=(("ts_code", "000001.SH"),),
    ),
    DatasetSpec(
        "market",
        "fund_daily",
        "fund_daily",
        "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        "Fund/ETF daily OHLCV.",
        target_mode="single",
        source_type="market_data",
        default_params=(("ts_code", "510300.SH"),),
    ),
    DatasetSpec(
        "market",
        "cb_daily",
        "cb_daily",
        "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        "Convertible-bond daily market data.",
        target_mode="single",
        source_type="market_data",
    ),
    DatasetSpec(
        "market",
        "cb_basic",
        "cb_basic",
        "ts_code,bond_short_name,stk_code,stk_short_name,maturity,conv_start_date,conv_end_date,issue_size,remain_size",
        "Convertible-bond basic metadata.",
        target_mode="all",
        source_type="market_data",
    ),
    DatasetSpec(
        "market",
        "ths_hot",
        "ths_hot",
        "trade_date,ts_code,ts_name,rank,rank_time,hot,concept",
        "Tonghuashun heat ranking.",
        target_mode="single",
        source_type="market_data",
        date_param="trade_date",
        default_params=(("market", "热股"),),
    ),
    DatasetSpec(
        "market",
        "stk_mins",
        "stk_mins",
        "ts_code,trade_time,open,close,high,low,vol,amount",
        "Focused stock minute bars; do not use for broad sweeps.",
        source_type="market_data",
        default_params=(("freq", "1min"),),
    ),
    DatasetSpec(
        "market",
        "cn_gdp",
        "cn_gdp",
        "quarter,gdp,gdp_yoy,pi,pi_yoy,si,si_yoy,ti,ti_yoy",
        "China GDP macro context.",
        target_mode="all",
        source_type="macro_data",
    ),
    DatasetSpec(
        "market",
        "cn_cpi",
        "cn_cpi",
        "month,nt_val,nt_yoy,nt_mom,nt_accu,town_val,town_yoy,town_mom,cnt_val,cnt_yoy,cnt_mom",
        "China CPI macro context.",
        target_mode="all",
        source_type="macro_data",
    ),
    DatasetSpec(
        "market",
        "cn_ppi",
        "cn_ppi",
        "month,ppi_yoy,ppi_mp_yoy,ppi_mp_qm_yoy,ppi_mp_rm_yoy,ppi_mp_p_yoy,ppi_cg_yoy,ppi_cg_f_yoy",
        "China PPI macro context.",
        target_mode="all",
        source_type="macro_data",
    ),
    DatasetSpec(
        "market",
        "cn_pmi",
        "cn_pmi",
        "month,pmi010000,pmi010100,pmi010200,pmi010300,pmi010400,pmi010500",
        "China PMI macro context.",
        target_mode="all",
        source_type="macro_data",
    ),
    DatasetSpec(
        "market",
        "shibor",
        "shibor",
        "date,on,1w,2w,1m,3m,6m,9m,1y",
        "Shibor rate context.",
        target_mode="single",
        source_type="macro_data",
    ),
    DatasetSpec(
        "market",
        "hk_basic",
        "hk_basic",
        "ts_code,name,fullname,enname,market,list_status,list_date",
        "Hong Kong stock basic metadata.",
        target_mode="all",
        source_type="cross_asset_data",
    ),
    DatasetSpec(
        "market",
        "hk_daily",
        "hk_daily",
        "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        "Hong Kong stock daily market data.",
        target_mode="single",
        source_type="cross_asset_data",
    ),
    DatasetSpec(
        "market",
        "us_basic",
        "us_basic",
        "ts_code,name,enname,classify,list_date,delist_date",
        "US stock basic metadata.",
        target_mode="all",
        source_type="cross_asset_data",
    ),
    DatasetSpec(
        "market",
        "us_daily",
        "us_daily",
        "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        "US stock daily market data.",
        target_mode="single",
        source_type="cross_asset_data",
    ),
    DatasetSpec(
        "market",
        "fut_basic",
        "fut_basic",
        "ts_code,symbol,exchange,name,fut_code,multiplier,trade_unit,per_unit,quote_unit,list_date,delist_date",
        "Futures contract basic metadata.",
        target_mode="all",
        source_type="cross_asset_data",
    ),
    DatasetSpec(
        "market",
        "fut_daily",
        "fut_daily",
        "ts_code,trade_date,pre_close,pre_settle,open,high,low,close,settle,vol,amount,oi",
        "Futures daily market data.",
        target_mode="single",
        source_type="cross_asset_data",
    ),
    DatasetSpec(
        "market",
        "opt_basic",
        "opt_basic",
        "ts_code,name,exercise_type,exercise_price,list_date,delist_date",
        "Option contract basic metadata.",
        target_mode="all",
        source_type="cross_asset_data",
    ),
    DatasetSpec(
        "market",
        "opt_daily",
        "opt_daily",
        "ts_code,trade_date,pre_settle,pre_close,open,high,low,close,settle,vol,amount,oi",
        "Option daily market data.",
        target_mode="single",
        source_type="cross_asset_data",
    ),
    # financial-data-router ownership
    DatasetSpec(
        "financial",
        "income",
        "income",
        "ts_code,ann_date,f_ann_date,end_date,report_type,total_revenue,revenue,operate_profit,total_profit,n_income,n_income_attr_p",
        "Income statement rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "balancesheet",
        "balancesheet",
        "ts_code,ann_date,f_ann_date,end_date,report_type,total_assets,total_liab,total_hldr_eqy_exc_min_int,total_share",
        "Balance-sheet rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "cashflow",
        "cashflow",
        "ts_code,ann_date,f_ann_date,end_date,report_type,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,c_cash_equ_end_period",
        "Cash-flow statement rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "fina_indicator",
        "fina_indicator",
        "ts_code,ann_date,end_date,eps,dt_eps,total_revenue_ps,roe,roe_dt,grossprofit_margin,netprofit_margin,debt_to_assets,ocfps",
        "Financial indicators and margins.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "fina_mainbz",
        "fina_mainbz",
        "ts_code,end_date,bz_item,bz_sales,bz_profit,bz_cost,curr_type,update_flag",
        "Main-business composition rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "stock_company",
        "stock_company",
        "ts_code,exchange,chairman,manager,secretary,reg_capital,setup_date,province,city,main_business,business_scope",
        "Listed-company profile and business-scope metadata.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "stk_managers",
        "stk_managers",
        "ts_code,ann_date,name,gender,lev,title,edu,national,birthday,begin_date,end_date,resume",
        "Management team rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "stk_rewards",
        "stk_rewards",
        "ts_code,ann_date,end_date,name,title,reward,hold_vol",
        "Management compensation/shareholding rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "top10_holders",
        "top10_holders",
        "ts_code,ann_date,end_date,holder_name,hold_amount,hold_ratio",
        "Top-ten holder rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "stk_holdernumber",
        "stk_holdernumber",
        "ts_code,ann_date,end_date,holder_num",
        "Shareholder-count rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "share_float",
        "share_float",
        "ts_code,ann_date,float_date,float_share,float_ratio,holder_name,share_type",
        "Restricted-share unlock rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "pledge_detail",
        "pledge_detail",
        "ts_code,ann_date,holder_name,pledge_amount,start_date,end_date,is_release,release_date,pledgor,holding_amount,pledged_amount,p_total_ratio,h_total_ratio",
        "Equity pledge detail rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "dividend",
        "dividend",
        "ts_code,end_date,ann_date,div_proc,stk_div,stk_bo_rate,stk_co_rate,cash_div,cash_div_tax,record_date,ex_date,pay_date",
        "Dividend and capital distribution rows.",
        source_type="financial_data",
    ),
    DatasetSpec(
        "financial",
        "repurchase",
        "repurchase",
        "ts_code,ann_date,end_date,proc,exp_date,vol,amount,high_limit,low_limit",
        "Share repurchase rows.",
        source_type="financial_data",
    ),
    # evidence-miner ownership
    DatasetSpec(
        "evidence",
        "anns_d",
        "anns_d",
        "ann_date,ts_code,name,title,url",
        "Announcement index rows; permission may be separate.",
        source_type="announcement",
        date_param="ann_date",
    ),
    DatasetSpec(
        "evidence",
        "research_report",
        "research_report",
        "ts_code,name,title,org_name,author,publish_date,url",
        "Broker research-report metadata; permission may be separate.",
        source_type="broker_report",
    ),
    DatasetSpec(
        "evidence",
        "stk_surv",
        "stk_surv",
        "ts_code,name,surv_date,fund_visitors,rece_place,rece_mode,rece_org,org_type,comp_rece,content",
        "Institutional survey metadata/content rows.",
        source_type="investor_relations",
    ),
    DatasetSpec(
        "evidence",
        "irm_qa_sz",
        "irm_qa_sz",
        "ts_code,name,trade_date,q,a,pub_time,industry",
        "Shenzhen exchange interactive Q&A rows; permission may be separate.",
        source_type="exchange_qa",
        date_param="trade_date",
    ),
    DatasetSpec(
        "evidence",
        "irm_qa_sh",
        "irm_qa_sh",
        "ts_code,name,trade_date,q,a,pub_time,industry",
        "Shanghai exchange interactive Q&A rows; permission may be separate.",
        source_type="exchange_qa",
        date_param="trade_date",
    ),
    DatasetSpec(
        "evidence",
        "news",
        "news",
        "datetime,content,title,channels",
        "News/context rows; weak evidence unless manually curated.",
        target_mode="single",
        source_type="news",
    ),
    # forecast-normalizer ownership
    DatasetSpec(
        "forecast",
        "report_rc",
        "report_rc",
        "ts_code,name,report_date,org_name,quarter,eps,pe,peg,roe,ev_ebitda,rating,target_price",
        "Broker forecast rows and source-count inputs.",
        source_type="forecast_data",
    ),
    DatasetSpec(
        "forecast",
        "research_report",
        "research_report",
        "ts_code,name,title,org_name,author,publish_date,url",
        "Forecast-related report metadata.",
        source_type="broker_report",
    ),
)


DATASETS_BY_GROUP: dict[str, list[DatasetSpec]] = {}
DATASETS_BY_NAME: dict[str, DatasetSpec] = {}
for spec in DATASETS:
    DATASETS_BY_GROUP.setdefault(spec.group, []).append(spec)
    DATASETS_BY_NAME[f"{spec.group}:{spec.dataset}"] = spec


def list_groups() -> list[str]:
    return sorted(DATASETS_BY_GROUP)


def list_group_datasets(group: str) -> list[DatasetSpec]:
    return sorted(DATASETS_BY_GROUP.get(group, []), key=lambda item: item.dataset)


def get_dataset(group: str, dataset: str) -> DatasetSpec:
    key = f"{group}:{dataset}"
    try:
        return DATASETS_BY_NAME[key]
    except KeyError as exc:
        raise KeyError(f"Unsupported Tushare dataset: group={group} dataset={dataset}") from exc
