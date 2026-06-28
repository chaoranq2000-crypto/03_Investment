from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "src"))

from investment_system.core.skill_module_loader import add_skill_src_paths

add_skill_src_paths()

from financial_data_router.commands import main

if __name__ == "__main__":
    raise SystemExit(main())
