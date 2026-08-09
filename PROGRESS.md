# Seeking Biblical Truth continuous improvement log

Last updated: 2026-08-10 (Cycle 60 across the projects workspace)

## Current state

- Branch: `main`; working tree was clean and aligned with `origin/main` at cycle start.
- Runtime: Obsidian vault plus deterministic Python export consumed by the public portfolio viewer.
- Generated dataset: 55 public notes, one canvas, 62 nodes, and 99 links.
- Local verification: five exporter contract tests, deterministic regeneration comparison, and Python compilation.
- Automated verification: least-privilege GitHub Actions runs the same tests, freshness comparison, and compilation on Python 3.12.

## Latest cycle: make public vault export lossless and verifiable

### Why this was selected

The exporter silently truncated every note and canvas body at 7,000 characters. Three real notes exceeded that limit, so the public viewer omitted 11,262 characters while appearing successful. Invalid canvas JSON was also silently skipped, and repository metadata was published as theological content. No tests or CI protected any of these behaviors.

### Changes

- Export complete Markdown and canvas source instead of slicing content at 7,000 characters.
- Raise a path-specific error for invalid canvas JSON instead of dropping the canvas silently.
- Exclude root `AGENTS.md`, `PROGRESS.md`, and `README.md` metadata while preserving the intentional root note `My Search for Truth.md` and all nested content notes.
- Add five unit contracts for full content, invalid canvases, public-note filtering, generated-artifact freshness, unique nodes, counts, and link endpoint integrity.
- Add least-privilege GitHub Actions with automatic test discovery, deterministic CLI regeneration comparison, Python 3.12, bounded runtime, and stale-run cancellation.
- Document the complete local validation sequence in `README.md` and regenerate `pages/vault-data.json`.

### Verification and scores

- Test-first evidence: long-content and malformed-canvas fixtures initially failed; the metadata fixture then found all three repository files in the public note set.
- Restored content: `My background.md` gained 5,847 characters, `The purpose of Baptism.md` gained 280, and `Women role in ministry.md` gained 5,135; all exported note bodies now exactly match their source text.
- Dataset contract: metadata is absent, `My Search for Truth.md` remains present, node IDs are unique, all 99 link endpoints resolve, and recorded counts match the arrays.
- `python3 -m unittest discover -s tools -p 'test_*.py'`: all five tests passed.
- Regeneration to `/tmp/vault-data.cycle60.json` followed by `cmp`: byte-identical.
- `python3 -m compileall -q tools`: passed.
- Local HTTP smoke: `/pages/` and `/pages/vault-data.json` returned HTTP 200, and the served dataset matched the 55/1/62/99 count contract.
- `git diff --check`: passed.
- Correctness/reliability: 10/10 (silent content loss and silent canvas omission are eliminated).
- Verifiability: 9/10 (fixtures, freshness, link integrity, and hosted CI now gate the exporter).
- Maintainability: 9/10 (public-vault boundaries and exporter expectations are explicit).
- Performance: 9/10 (the corrected artifact is only about 174 KB and tests finish in roughly 0.03 seconds locally).
- Security/robustness: 9/10 (agent/state metadata no longer leaks into the public note browser; malformed canvases fail closed).

### Lessons and process improvements

- Compare exported content lengths to source lengths; successful JSON parsing cannot reveal silent truncation.
- Generated-artifact freshness is best tested both in-process and through the real CLI output path.
- State files require an explicit export boundary or process documentation becomes accidental product content.
- Run package-importing unittest targets from the repository root; an initial invocation from `tools/` failed because the `tools` namespace was no longer importable.

## Recent project evolution

- `2f3f238`: expanded ignores for Python environments, OS files, and local secrets.
- `ccb1d88`: corrected vault-sync documentation to use the projects portfolio clone.
- `89c8270`: organized the public viewer and vault export tooling.

## Prioritized opportunities

| Priority | Opportunity | Category | Impact | Effort / risk | Evidence / dependency |
|---|---|---|---|---|---|
| 1 | Resolve and test path-qualified Obsidian wiki-links | Correctness / verification | Medium-high | Small-medium / low | Export lookup indexes only note stems, so `[[folder/note]]` links cannot resolve even when the target exists |
| 2 | Report unresolved and ambiguous note links | Observability / maintainability | Medium | Medium / low | The current vault has 27 unresolved wiki-link references but generation provides no diagnostic summary |
| 3 | Automate or verify cross-repository viewer-data sync | Reliability / process | Medium-high | Medium / medium | Public deployment still depends on a manual copy and separate portfolio commit |
| 4 | Remove the obsolete duplicate local viewer shell | Maintainability / security | Medium | Medium / low | Canonical viewer code lives in the portfolio, while `pages/index.html` duplicates older inline CDN-driven behavior |

## Next cycle

Add fixture-backed path-aware Obsidian link resolution without changing how unresolved references are treated, then measure its effect on the current vault graph.
