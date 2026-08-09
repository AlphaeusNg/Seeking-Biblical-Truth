# Seeking Biblical Truth continuous improvement log

Last updated: 2026-08-10 (Cycle 79 across the projects workspace; vault Cycle 64)

## Current state

- Branch: `main`; working tree was clean and aligned with `origin/main` at cycle start.
- Runtime: Obsidian vault plus deterministic Python export consumed by the public portfolio viewer.
- Generated dataset: 55 public notes, one canvas, 62 nodes, 99 resolved links, 26 unresolved wiki-links, and zero ambiguous wiki-links.
- Local verification: eighteen exporter/synchronization contract tests, read-only link and cross-repository reports, deterministic regeneration, and Python compilation.
- Automated verification: least-privilege GitHub Actions runs all isolated tests, source-export freshness comparison, and compilation on Python 3.12.

## Latest cycle: make link diagnostics human-readable

### Why this was selected

Cycle 78 queued Markdown-link resolution, but a real-vault inventory found zero ordinary Markdown `.md` links. In contrast, the generated artifact contains 26 real unresolved wiki-link diagnostics spread across seven source notes, and maintainers had to inspect raw JSON to find them. The cycle therefore pivoted to the higher-impact adjacent need: deterministic, read-only triage output.

### Changes

- Added `format_link_diagnostics()` to group unresolved and ambiguous references by source note.
- Report entries name the failure kind and link syntax; ambiguous entries include every candidate path.
- Added `--report-links` to rebuild and print current diagnostics directly from vault sources without writing the requested or default dataset output.
- Defined explicit zero-diagnostic output so a clean vault is visibly distinguishable from a broken or empty report.
- Added three contracts for exact grouped/candidate-rich formatting, empty output, CLI status/output, and read-only preservation of a supplied output file.
- Documented the diagnostic command in the project and agent workflows.

### Verification and scores

- Test-first report fixture: failed with `ImportError: cannot import name 'format_link_diagnostics'`, proving the human report did not exist.
- `python3 -m unittest tools.test_generate_vault_data`: all eleven exporter/report contracts passed.
- Real `python3 tools/generate_vault_data.py --report-links`: reported 26 unresolved, zero ambiguous, grouped under seven source notes.
- The report identified missing verse/concept targets without changing the valid 55/1/62/99 graph contract.
- The complete eighteen-test, deterministic freshness, sync equality, compilation, and diff gate passed; both tracked dataset hashes remained `ba0b947c…`.
- Correctness/reliability: 8/10 (diagnostic state is surfaced accurately, though content owners must decide which missing notes are intentional).
- Verifiability: 10/10 (exact non-empty, candidate-rich, empty, CLI, and non-writing contracts execute deterministically).
- Maintainability: 9/10 (one formatter consumes the existing stable diagnostic schema; no second scanner was introduced).
- Performance: 10/10 (one existing vault scan; report output is linear in diagnostic count).
- Security/robustness: 9/10 (read-only mode cannot overwrite a path supplied through `--output`).

### Lessons and process improvements

- Measure current usage before hardening hypothetical syntax; zero Markdown links changed the impact calculation materially.
- A pivot is valuable when it reuses the same evidence boundary and addresses real current data rather than expanding scope.
- Human output should be generated from the same in-memory model as machine output so counts, ordering, and candidates cannot drift.
- Explicit empty-state text makes automation and manual triage distinguish “clean” from “printed nothing.”

## Recent project evolution

- Cycle 64: added deterministic, read-only, source-grouped link diagnostics for maintainers.
- Cycle 63 (`170b26d`): added one-command, byte-exact source-to-public viewer synchronization and drift checks.
- Cycle 62 (`3659dc8`): made unresolved and ambiguous wiki-links observable without blocking valid authoring.
- Cycle 61 (`cbd457e`): added exact path-aware wiki-link resolution and rejected ambiguous bare-title guesses.
- Cycle 60 (`f1b3b7d`): made exports lossless, metadata-safe, fail-fast, fixture-tested, and CI-gated.

## Prioritized opportunities

| Priority | Opportunity | Category | Impact | Effort / risk | Evidence / dependency |
|---|---|---|---|---|---|
| 1 | Classify or resolve the 26 reported references | Content correctness / DX | Medium-high | Medium / medium | Seven source notes now expose the exact missing verse/concept targets; theological/content intent must be preserved |
| 2 | Remove the obsolete duplicate local viewer shell | Maintainability / security | Medium | Medium / low | Canonical viewer code lives in the portfolio, while `pages/index.html` duplicates older inline CDN-driven behavior |
| 3 | Resolve and diagnose Markdown links with explicit path semantics | Correctness / maintainability | Low currently | Small-medium / low | The alternate resolver silently drops failures, but the real exported vault currently contains zero Markdown `.md` links |
| 4 | Add an opt-in paired commit/status helper | Process / reliability | Low-medium | Medium / medium | Dataset writes are unified, but Git histories and pushes correctly remain separate and non-transactional |

## Next cycle

Pause after two consecutive cross-repository/vault cycles and rotate to KoboForge, which has not yet received a cycle in the current workspace sweep. On return, inspect the duplicate local viewer before changing content-intent-sensitive unresolved references.
