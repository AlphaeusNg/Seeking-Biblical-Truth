# Seeking Biblical Truth continuous improvement log

Last updated: 2026-08-10 (Cycle 62 across the projects workspace)

## Current state

- Branch: `main`; working tree was clean and aligned with `origin/main` at cycle start.
- Runtime: Obsidian vault plus deterministic Python export consumed by the public portfolio viewer.
- Generated dataset: 55 public notes, one canvas, 62 nodes, 99 resolved links, 26 unresolved wiki-links, and zero ambiguous wiki-links.
- Local verification: eight exporter contract tests, deterministic regeneration comparison, and Python compilation.
- Automated verification: least-privilege GitHub Actions runs the same tests, freshness comparison, and compilation on Python 3.12.

## Latest cycle: make unresolved wiki-links observable

### Why this was selected

The exporter silently discarded wiki-links that could not resolve. The current vault contained 27 such occurrences, but neither generator output nor the public artifact identified them, so maintainers could not distinguish intentional future-note references from typos or missing content. Diagnostics must remain non-blocking because uncreated Obsidian notes are a valid workflow.

### Changes

- Added deterministic `linkDiagnostics.unresolved` and `linkDiagnostics.ambiguous` arrays to the generated payload.
- Deduplicate diagnostics by source, normalized reference, and failure kind, so repeated or percent-encoded equivalents do not inflate the report.
- Preserve a readable decoded reference; ambiguous diagnostics also include every sorted candidate path.
- Added `unresolvedLinks` and `ambiguousLinks` counts without changing successful export behavior.
- Added a fixture proving missing-reference deduplication and candidate-rich ambiguity reporting.
- Extended the general dataset contract to verify diagnostic counts and source-node integrity, and documented the non-blocking schema.

### Verification and scores

- Test-first diagnostic fixture: failed with `KeyError: unresolvedLinks`, proving the schema did not exist.
- Freshness gate: after implementation, the committed-artifact test failed until regeneration captured the diagnostics.
- Current measurement: 27 unresolved occurrences collapse to 26 unique missing references; no ambiguous references exist today.
- `python3 -m unittest discover -s tools -p 'test_*.py'`: all eight tests passed.
- Regeneration to `/tmp/vault-data.cycle62.json` followed by `cmp`: byte-identical.
- Dataset contract: all 26 diagnostic sources are real nodes, counts match their arrays, and existing graph counts remain 55/1/62/99.
- `python3 -m compileall -q tools`: passed.
- Local HTTP smoke: the served `vault-data.json` parsed with the exact 26-unresolved/0-ambiguous contract.
- `git diff --check`: passed.
- Correctness/reliability: 9/10 (unresolved relationships remain non-edges but can no longer disappear unnoticed).
- Verifiability: 10/10 (the real vault's missing/ambiguous totals and every diagnostic source are contract-checked).
- Maintainability: 9/10 (one stable schema separates missing and ambiguous remediation work).
- Performance: 10/10 (normalized-set deduplication is linear and all eight tests finish locally in under 0.1 seconds).
- Security/robustness: 9/10 (diagnostics expose only paths/references already contained in the public vault and do not weaken fail-closed resolution).

### Lessons and process improvements

- Observability should not turn an allowed authoring state into a build failure; record unresolved notes without rejecting them.
- Deduplicate by normalized identity but retain the first human-readable spelling for useful reports.
- Ambiguous diagnostics need candidate paths, not merely a count, so remediation is actionable.
- Additive payload metadata should carry matching counts and integrity checks so downstream tools can trust it.

## Recent project evolution

- Cycle 61 (`cbd457e`): added exact path-aware wiki-link resolution and rejected ambiguous bare-title guesses.
- Cycle 60 (`f1b3b7d`): made exports lossless, metadata-safe, fail-fast, fixture-tested, and CI-gated.
- `2f3f238`: expanded ignores for Python environments, OS files, and local secrets.

## Prioritized opportunities

| Priority | Opportunity | Category | Impact | Effort / risk | Evidence / dependency |
|---|---|---|---|---|---|
| 1 | Automate or verify cross-repository viewer-data sync | Reliability / process | Medium-high | Medium / medium | Public deployment still depends on a manual copy and separate portfolio commit |
| 2 | Resolve and diagnose Markdown links with the same explicit semantics | Correctness / maintainability | Medium | Small-medium / low | Markdown-link handling uses a separate filesystem-resolution path and has no dedicated fixtures or diagnostics |
| 3 | Add a human-readable unresolved-link report mode | Developer experience | Medium | Small / low | Diagnostics are machine-readable in JSON but require manual inspection to triage by source |
| 4 | Remove the obsolete duplicate local viewer shell | Maintainability / security | Medium | Medium / low | Canonical viewer code lives in the portfolio, while `pages/index.html` duplicates older inline CDN-driven behavior |

## Next cycle

Unify Markdown-link resolution with the normalized exact-path model and include unresolved/ambiguous Markdown references in the same diagnostic contract.
