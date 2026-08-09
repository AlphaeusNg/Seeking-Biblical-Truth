# Seeking Biblical Truth continuous improvement log

Last updated: 2026-08-10 (Cycle 78 across the projects workspace; vault Cycle 63)

## Current state

- Branch: `main`; working tree was clean and aligned with `origin/main` at cycle start.
- Runtime: Obsidian vault plus deterministic Python export consumed by the public portfolio viewer.
- Generated dataset: 55 public notes, one canvas, 62 nodes, 99 resolved links, 26 unresolved wiki-links, and zero ambiguous wiki-links.
- Local verification: fifteen exporter/synchronization contract tests, read-only cross-repository equality checking, and Python compilation.
- Automated verification: least-privilege GitHub Actions runs the same isolated tests, source-export freshness comparison, and compilation on Python 3.12.

## Latest cycle: make viewer-data synchronization one command and verifiable

### Why this was selected

The deterministic exporter protected only `pages/vault-data.json` in this repository. Publishing still required a manual copy to a separately committed portfolio repository, with no canonical read-only check to identify which side had drifted. That left the public viewer vulnerable to silently serving old content even when both repositories' independent CI checks passed.

### Changes

- Added `tools/sync_public_viewer.py`, which builds one canonical in-memory payload and byte-synchronizes the source export and portfolio viewer copy.
- Added `--check` mode that never writes and reports source-export drift separately from public-copy drift.
- Validate the canonical viewer directory and entry point before either write, preventing a bad checkout path from creating a partial export.
- Preserve unchanged files and use same-directory atomic replacement for changed files.
- Extracted the generator's canonical serializer so standalone generation and cross-repository sync cannot disagree about formatting.
- Added seven isolated contracts for synchronized output, idempotence, precise source/public drift detection, invalid UTF-8 handling, CLI failure status, check-mode immutability, and missing/empty source or target refusal.
- Replaced manual-copy guidance with the one-command sync/check workflow.

### Verification and scores

- Test-first sync fixture: failed with `ModuleNotFoundError: tools.sync_public_viewer`, proving no unified workflow existed.
- `python3 -m unittest tools.test_sync_public_viewer`: all seven synchronization contracts passed.
- Real `python3 tools/sync_public_viewer.py --check`: confirmed both tracked copies are current and byte-identical.
- Real write-mode rerun reported both files already synchronized, proving idempotence without modifying either repository's dataset.
- `python3 -m unittest discover -s tools -p 'test_*.py'`: all fifteen exporter and synchronization tests passed.
- Deterministic regeneration comparison, Python compilation, diff checks, and the complete portfolio Python/site/Chromium/JavaScript gate passed.
- Correctness/reliability: 9/10 (one generated payload now feeds both tracked copies and drift is identified precisely).
- Verifiability: 10/10 (write, no-op, read-only, corrupt-file, wrong-target, and both drift classes are executable contracts).
- Maintainability: 9/10 (one serializer and one documented command replace duplicated operator steps).
- Performance: 10/10 (one small vault scan; unchanged files incur no writes).
- Security/robustness: 9/10 (target identity is validated before mutation and malformed tracked files are safely diagnosed or repaired).

### Lessons and process improvements

- Cross-repository deployment cannot be transactional at the Git layer, but generation can still be single-source and pre-commit equality can be fail-closed.
- Validate every destination before the first write; otherwise a path typo can update one repository and leave the second silently stale.
- A verification mode should name the drifting boundary and guarantee immutability, making repair obvious and safe to automate later.
- Avoid rewriting identical generated files so sync checks do not create noisy commits or misleading mtimes.

## Recent project evolution

- Cycle 63: added one-command, byte-exact source-to-public viewer synchronization and drift checks.
- Cycle 62 (`3659dc8`): made unresolved and ambiguous wiki-links observable without blocking valid authoring.
- Cycle 61 (`cbd457e`): added exact path-aware wiki-link resolution and rejected ambiguous bare-title guesses.
- Cycle 60 (`f1b3b7d`): made exports lossless, metadata-safe, fail-fast, fixture-tested, and CI-gated.
- `2f3f238`: expanded ignores for Python environments, OS files, and local secrets.

## Prioritized opportunities

| Priority | Opportunity | Category | Impact | Effort / risk | Evidence / dependency |
|---|---|---|---|---|---|
| 1 | Resolve and diagnose Markdown links with the same explicit semantics | Correctness / maintainability | Medium | Small-medium / low | Markdown-link handling uses a separate filesystem-resolution path and silently drops failures |
| 2 | Add a human-readable unresolved-link report mode | Developer experience | Medium | Small / low | Diagnostics are machine-readable in JSON but require manual inspection to triage by source |
| 3 | Remove the obsolete duplicate local viewer shell | Maintainability / security | Medium | Medium / low | Canonical viewer code lives in the portfolio, while `pages/index.html` duplicates older inline CDN-driven behavior |
| 4 | Add an opt-in paired commit/status helper | Process / reliability | Low-medium | Medium / medium | Dataset writes are unified, but Git histories and pushes correctly remain separate and non-transactional |

## Next cycle

Unify Markdown-link resolution with the normalized exact-path model and include unresolved/ambiguous Markdown references in the same diagnostic contract.
