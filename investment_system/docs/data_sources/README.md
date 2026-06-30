# Data Source Reference Materials

This directory stores data-source manuals, copied upstream reference packages,
and endpoint notes that are useful when designing adapters.

Files here are not Codex workflow skills. They should not define project stage
order, write policy, evidence gates, or formal research output behavior.

Current references:

- `a-stock-data/`: upstream A-share public-web endpoint catalog and interface
  notes. Use it only as a reference for fallback endpoint patterns, ticker
  normalization, request pacing, and source-specific caveats. When a pattern is
  needed, port the smallest useful part into the owning workflow skill under
  `.codex/skills/<skill>/src/` or `.codex/skills/<skill>/scripts/`.
