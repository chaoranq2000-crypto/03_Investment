"""Shared data-source adapters for migrated skill modules."""

__all__ = [
    "AKShareClient",
    "BaoStockClient",
    "PROXY_ENV_KEYS",
    "ResearchClient",
    "clear_proxy_env",
    "env_flag",
    "load_data_source_config",
    "get_tushare_pro",
    "load_dotenv",
    "tencent_code",
    "tencent_bar_direct",
]


def __getattr__(name: str):
    if name in __all__:
        if name == "load_data_source_config":
            from investment_system.core.data_sources.config import load_data_source_config

            return load_data_source_config
        if name in {"AKShareClient", "BaoStockClient", "ResearchClient", "tencent_code", "tencent_bar_direct"}:
            from investment_system.core.data_sources import research_client

            return getattr(research_client, name)
        from investment_system.core.data_sources import tushare_client

        return getattr(tushare_client, name)
    raise AttributeError(f"module 'investment_system.core.data_sources' has no attribute {name!r}")
