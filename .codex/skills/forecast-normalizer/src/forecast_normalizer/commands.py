"""CLI command map for the forecast-normalizer skill."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print("Usage: forecast-normalizer <command> [args]\n")
        print("Commands:")
        print("  status                   Show migration status for forecast commands.")
        return 0
    if args[0] == "status":
        print("forecast-normalizer CLI exists; forecast normalization logic is deferred.")
        print("Do not assume Wind or iFind access; use curated/user-provided forecasts.")
        return 0
    print(f"Unknown command for forecast-normalizer: {args[0]}", file=sys.stderr)
    return 2
