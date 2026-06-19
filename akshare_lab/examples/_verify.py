"""Verify all modules work (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cache import get_stats, _make_key, _cache_path, PROJECT_ROOT, CACHE_DIR
from akshare_utils import configure_chinese_font, list_installed_cn_fonts, save_csv, OUTPUT_DIR, DATA_DIR
import pandas as pd

print("=== Module import OK ===")
print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"CACHE_DIR:   {CACHE_DIR}")
print(f"OUTPUT_DIR:  {OUTPUT_DIR}")
print(f"DATA_DIR:    {DATA_DIR}")
print(f"cache key:   {_make_key('kline', '600519', period='daily')}")
print(f"cache path:  {_cache_path(_make_key('kline', '600519'))}")
print()

print("=== Font detection ===")
font = configure_chinese_font(force=False)
print(f"Active font: {font}")
print()

print("=== Installed CN fonts ===")
print(list_installed_cn_fonts().to_string(index=False))
print()

print("=== Cache stats ===")
print(get_stats().to_string(index=False))
print()

# Test save_csv with fake data
df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
p = save_csv(df, "test_small")
print(f"save_csv OK: {p}")
print()

# Verify cache key differentiation
k1 = _make_key("kline", "600519", period="daily")
k2 = _make_key("kline", "600519", period="weekly")
k3 = _make_key("kline", "000001", period="daily")
print(f"k1={k1}, k2={k2}, k3={k3}")
assert k1 != k2, "Different params must give different keys"
assert k1 != k3, "Different symbols must give different keys"
print("Cache key uniqueness: PASS")
