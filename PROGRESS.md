# Seeking Biblical Truth continuous improvement log

Last updated: 2026-08-10 (Cycle 61 across the projects workspace)

## Current state

- Branch: `main`; working tree was clean and aligned with `origin/main` at cycle start.
- Runtime: Obsidian vault plus deterministic Python export consumed by the public portfolio viewer.
- Generated dataset: 55 public notes, one canvas, 62 nodes, and 99 links.
- Local verification: seven exporter contract tests, deterministic regeneration comparison, and Python compilation.
- Automated verification: least-privilege GitHub Actions runs the same tests, freshness comparison, and compilation on Python 3.12.

## Latest cycle: resolve Obsidian wiki-links without false edges

### Why this was selected

[Obsidian's internal-link syntax](https://obsidian.md/help/links) supports vault-root wiki-link paths and optional `.md` suffixes, but the exporter indexed only bare stems. A valid `[[folder/note]]` therefore disappeared, while duplicate bare titles silently linked to whichever file sorted first. This could omit intentional relationships or create a confidently wrong graph edge.

### Changes

- Added a normalized note-reference key supporting percent decoding, forward-slash vault paths, optional leading `./`, optional case-insensitive `.md`, and Unicode-aware case folding.
- Indexed exact vault-relative paths independently from note stems.
- Resolve path-qualified links only through the exact path index.
- Track all files sharing a stem and resolve a bare title only when it is unique, eliminating sorted-first guesses.
- Added fixtures for both supported path forms and for ambiguous bare-title rejection.

### Verification and scores

- Test-first path fixture: expected one `Index.md -> Word of God/Grace.md` edge but received none.
- Test-first ambiguity fixture: expected the exact `B/Grace.md` edge but received an incorrect sorted-first `A/Grace.md` edge.
- `python3 -m unittest discover -s tools -p 'test_*.py'`: all seven tests passed.
- Regeneration to `/tmp/vault-data.cycle61.json` followed by `cmp`: byte-identical, confirming no unintended churn in today's 55-note dataset.
- Current impact measurement: the vault has 41 resolved wikilinks and no path-qualified link syntax yet, so node/link counts remain 62/99 as expected.
- `python3 -m compileall -q tools`: passed.
- `git diff --check`: passed.
- Correctness/reliability: 9/10 (supported path syntax resolves exactly and ambiguous titles no longer create false relationships).
- Verifiability: 9/10 (both prior failure modes have focused fixtures and the real artifact remains freshness-gated).
- Maintainability: 9/10 (normalization and resolution rules are centralized instead of embedded in the extraction loop).
- Performance: 10/10 (dictionary/list lookup adds negligible work; all seven tests finish locally in under 0.1 seconds).
- Security/robustness: 9/10 (exact paths take precedence and ambiguity fails closed).

### Lessons and process improvements

- Preserve a separate exact-path index; flattening a vault to stems discards information needed for correct Obsidian semantics.
- Ambiguity must fail closed rather than depend on filesystem sort order.
- Measure the current artifact delta before deployment: a correctness improvement can be valuable and fully verified even when existing content does not exercise it yet.
- Keep deterministic regeneration in the loop to prove a parser refactor did not perturb unrelated graph data.

## Recent project evolution

- Cycle 60 (`f1b3b7d`): made exports lossless, metadata-safe, fail-fast, fixture-tested, and CI-gated.
- `2f3f238`: expanded ignores for Python environments, OS files, and local secrets.
- `ccb1d88`: corrected vault-sync documentation to use the projects portfolio clone.

## Prioritized opportunities

| Priority | Opportunity | Category | Impact | Effort / risk | Evidence / dependency |
|---|---|---|---|---|---|
| 1 | Report unresolved and ambiguous note links | Observability / maintainability | Medium-high | Medium / low | The current vault has 27 unresolved wiki-link references but generation provides no diagnostic summary |
| 2 | Automate or verify cross-repository viewer-data sync | Reliability / process | Medium-high | Medium / medium | Public deployment still depends on a manual copy and separate portfolio commit |
| 3 | Resolve Markdown links with the same explicit semantics | Correctness / maintainability | Medium | Small-medium / low | Markdown-link handling currently uses a separate filesystem-resolution path and has no dedicated fixtures |
| 4 | Remove the obsolete duplicate local viewer shell | Maintainability / security | Medium | Medium / low | Canonical viewer code lives in the portfolio, while `pages/index.html` duplicates older inline CDN-driven behavior |

## Next cycle

Add deterministic unresolved/ambiguous wiki-link diagnostics to generator output and tests without failing on intentionally uncreated notes.
