# Seeking Biblical Truth continuous improvement log

Last updated: 2026-08-11 (Cycle 96 across the projects workspace; vault Cycle 66)

## Current state

- Branch: `main`; working tree was clean and aligned with `origin/main` at cycle start.
- Runtime: Obsidian vault plus deterministic Python export consumed by the public portfolio viewer.
- Generated dataset: 55 public notes, one canvas, 62 nodes, 99 resolved links, 26 unresolved wiki-links, and zero ambiguous wiki-links.
- Local verification: twenty-one exporter, synchronization, redirect-shell, and workflow-policy contract tests, read-only link and cross-repository reports, deterministic regeneration, and Python compilation.
- Automated verification: least-privilege GitHub Actions runs all isolated tests, source-export freshness comparison, and compilation on Python 3.12 using current v7 actions; sixteen policy assertions prevent workflow drift.

## Latest cycle: modernize and policy-test CI

### Why this was selected

The workflow was already least-privilege, concurrent, and bounded, but setup-python was one major behind the current Node 24 action and none of those guarantees were owned by repository tests. A future edit could silently drop triggers, freshness comparison, or compilation while CI still appeared configured.

### Changes

- Upgraded `actions/setup-python` from v6 to the current v7 major; checkout was already on v7.
- Added one dependency-free workflow policy test with sixteen assertions covering stable triggers, read-only permissions, per-ref stale-run cancellation, timeout, supported action majors, Python 3.12, complete unittest discovery, deterministic regeneration and comparison, compilation, and removal of deprecated majors.
- Kept policy enforcement inside the existing unittest discovery command, so local and hosted gates cannot omit it independently.

### Verification and scores

- Test-first evidence: the workflow policy failed exactly on `actions/setup-python@v6` rather than the required v7 runtime.
- Focused policy run: one test / sixteen assertions passed after the one-line workflow update.
- `python3 -m unittest discover -s tools -p 'test_*.py'`: 21 passed, up from 20.
- `python3 tools/sync_public_viewer.py --check`: source and portfolio data remain current and byte-identical.
- Deterministic regeneration preserved 55 notes, one canvas, 62 nodes, 99 links, 26 unresolved links, and zero ambiguous links.
- Python compilation and `git diff --check` passed.
- Correctness/reliability: 9/10 (the complete existing gate is now an executable invariant).
- Verifiability: 10/10 (sixteen workflow assertions run locally and inside hosted discovery).
- Maintainability: 10/10 (workflow intent is named in one fast dependency-free contract).
- Performance: 10/10 (stale-run cancellation and timeout remain enforced; the policy test is effectively instantaneous).
- Security/robustness: 10/10 (read-only token scope and supported Node 24 action runtimes cannot silently regress).

### Lessons and process improvements

- Treat workflow structure as production code: least privilege and complete gates need tests, not comments or memory.
- Make a policy test part of the same discovery command it requires; self-enforcement prevents a separate policy step from being deleted unnoticed.
- A current action major can be a one-line change, but the compounding value comes from preserving that supported-runtime boundary.

## Recent project evolution

- Cycle 66: upgraded setup-python to v7 and added sixteen self-enforced CI policy assertions.
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
| 2 | Resolve and diagnose Markdown links with explicit path semantics | Correctness / maintainability | Low currently | Small-medium / low | The alternate resolver silently drops failures, but the real exported vault currently contains zero Markdown `.md` links |
| 3 | Add an opt-in paired commit/status helper | Process / reliability | Low-medium | Medium / medium | Dataset writes are unified, but Git histories and pushes correctly remain separate and non-transactional |
| — | Modernize and policy-test GitHub Actions | Process / observability | Medium | Small-medium / low | setup-python v7 plus sixteen policy assertions enforce the complete bounded gate | Completed in Cycle 66 |
| — | Retire the duplicate local viewer without breaking legacy URLs | Maintainability / security | Medium-high | Small-medium / low | Two contract-tested compatibility redirects replace the active 20 KB CDN-driven duplicate | Completed in Cycle 65 |

## Next cycle

Local next: obtain content-owner classification for the 26 unresolved references before changing notes; the remaining tool-only items are lower impact. Workspace next: rotate to another repository after two focused vault cycles and avoid speculative theological edits.
