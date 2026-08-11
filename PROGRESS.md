# Seeking Biblical Truth continuous improvement log

Last updated: 2026-08-11 (Cycle 95 across the projects workspace; vault Cycle 65)

## Current state

- Branch: `main`; working tree was clean and aligned with `origin/main` at cycle start.
- Runtime: Obsidian vault plus deterministic Python export consumed by the public portfolio viewer.
- Generated dataset: 55 public notes, one canvas, 62 nodes, 99 resolved links, 26 unresolved wiki-links, and zero ambiguous wiki-links.
- Local verification: twenty exporter, synchronization, and redirect-shell contract tests, read-only link and cross-repository reports, deterministic regeneration, and Python compilation.
- Automated verification: least-privilege GitHub Actions runs all isolated tests, source-export freshness comparison, and compilation on Python 3.12.

## Latest cycle: retire the duplicate viewer without breaking legacy URLs

### Why this was selected

The repository carried a 20 KB inline viewer that duplicated an older version of the canonical portfolio UI and loaded five third-party CDN scripts. The apparent cleanup was to delete it, but a read-only Pages check showed this repository still deploys from `main`/root and both historical URLs are live. Preserving those public routes while removing the stale implementation was the highest-value safe change.

### Changes

- Replaced both the repository root and `/pages/` shells with byte-identical redirects to the canonical portfolio viewer.
- Added canonical metadata and `noindex, follow` so historical routes remain usable without competing in search results.
- Removed all script execution, five CDN dependencies, inline rendering logic, and local `vault-data.json` fetching from the legacy shell.
- Added two contracts that enforce both public redirects, canonical and robots metadata, identical bytes, and an inert no-script/no-CDN/no-data boundary.
- Updated README and agent guidance so canonical UI work and local preview happen only in the portfolio repository.

### Verification and scores

- Test-first evidence: the root shell targeted the obsolete project URL, while `/pages/` had no redirect and still contained the full active viewer; all three redirect/inert assertions failed.
- GitHub Pages source check: the repository is built from `main`/root and both historical URLs returned HTTP 200 before the change, so deletion was rejected in favor of compatibility redirects.
- `python3 -m unittest discover -s tools -p 'test_*.py'`: 20 passed, up from 18.
- Local HTTP checks for `/` and `/pages/` served canonical, no-index redirect markup and no script tags.
- `python3 tools/sync_public_viewer.py --check`: source and portfolio data remain current and byte-identical.
- Deterministic regeneration preserved 55 notes, one canvas, 62 nodes, 99 links, 26 unresolved links, and zero ambiguous links.
- Link reporting, Python compilation, and `git diff --check` passed.
- Correctness/reliability: 10/10 (both public legacy routes are preserved and converge on one maintained viewer).
- Verifiability: 10/10 (file contracts, local HTTP, live-source evidence, data sync, and regeneration agree).
- Maintainability: 10/10 (one canonical viewer replaces two independently evolving implementations).
- Performance: 10/10 (legacy HTML shrank from roughly 20 KB plus five CDN loads to a sub-1 KB redirect).
- Security/robustness: 10/10 (the duplicate route no longer executes remote or inline JavaScript).

### Lessons and process improvements

- Check deployment configuration and live routes before deleting apparently obsolete web files; repository references alone did not reveal the active Pages source.
- Compatibility redirects are a reversible way to remove duplicate attack and maintenance surfaces without breaking bookmarks.
- Make duplicate shells byte-identical and contract-tested so a future change cannot quietly revive a second implementation.
- Documentation is part of architectural cleanup: preview commands must point contributors at the canonical owner.

## Recent project evolution

- Cycle 65: retired the active duplicate viewer behind inert canonical redirects while preserving both legacy Pages URLs.
- Cycle 64: added deterministic, read-only, source-grouped link diagnostics for maintainers.
- Cycle 63 (`170b26d`): added one-command, byte-exact source-to-public viewer synchronization and drift checks.
- Cycle 62 (`3659dc8`): made unresolved and ambiguous wiki-links observable without blocking valid authoring.
- Cycle 61 (`cbd457e`): added exact path-aware wiki-link resolution and rejected ambiguous bare-title guesses.
- Cycle 60 (`f1b3b7d`): made exports lossless, metadata-safe, fail-fast, fixture-tested, and CI-gated.

## Prioritized opportunities

| Priority | Opportunity | Category | Impact | Effort / risk | Evidence / dependency |
|---|---|---|---|---|---|
| 1 | Classify or resolve the 26 reported references | Content correctness / DX | Medium-high | Medium / medium | Seven source notes expose exact missing targets; theological/content intent requires owner judgment |
| 2 | Modernize and policy-test GitHub Actions | Process / observability | Medium | Small-medium / low | CI uses setup-python v6 and has no repository-owned workflow contract despite the current v7 release |
| 3 | Resolve and diagnose Markdown links with explicit path semantics | Correctness / maintainability | Low currently | Small-medium / low | The alternate resolver silently drops failures, but the real exported vault currently contains zero Markdown `.md` links |
| 4 | Add an opt-in paired commit/status helper | Process / reliability | Low-medium | Medium / medium | Dataset writes are unified, but Git histories and pushes correctly remain separate and non-transactional |
| — | Retire the duplicate local viewer without breaking legacy URLs | Maintainability / security | Medium-high | Small-medium / low | Two contract-tested compatibility redirects replace the active 20 KB CDN-driven duplicate | Completed in Cycle 65 |

## Next cycle

Local next: modernize and policy-test the Python CI workflow because the higher-impact unresolved-link work needs content-owner intent. Workspace next: complete that compounding verification cycle before rotating again; avoid editing theological content by inference.
