# a-stock-data Reference Status

Status: reference material and data-source manual only.

`a-stock-data` was moved out of `.codex/skills/a-stock-data/` on 2026-06-30.
It must not be treated as a project workflow skill, stage runner, formal
evidence source, or output generator.

Use it for:

- public-web endpoint discovery;
- ticker normalization examples;
- source-specific pacing and anti-ban notes;
- targeted fallback adapter design after a Tushare permission or coverage gap
  is confirmed.

Do not use it for:

- workflow orchestration;
- project-aware stock universe, sector, evidence, or output contracts;
- formal research claims;
- direct report generation;
- replacing existing workflow skills.

If a pattern from this package is needed, copy only the minimal verified logic
into the owning skill, then add project-aware cache, source metadata, evidence
binding, and quality-audit coverage there.

The upstream package files are preserved here unchanged for reference. Their
internal installation instructions describe the original external package and
do not apply to this repository.
