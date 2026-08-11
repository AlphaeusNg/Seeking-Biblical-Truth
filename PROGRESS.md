# Seeking Biblical Truth continuous improvement log

Last updated: 2026-08-11 (Cycle 135 across the projects workspace; vault Cycle 70)

## Current state

- Branch: `main`; working tree was clean and aligned with `origin/main` at cycle start.
- Runtime: Obsidian vault plus deterministic Python export consumed by the public portfolio viewer.
- Generated dataset: 55 public notes, one canvas, 62 nodes, 99 resolved links, 26 unresolved wiki-links, and zero ambiguous wiki-links.
- Local verification: thirty exporter, synchronization, redirect-shell,
  and workflow-policy contract tests, read-only link and cross-repository
  reports, deterministic regeneration, and Python compilation.
- Automated verification: least-privilege GitHub Actions runs all isolated tests, source-export freshness comparison, and compilation on Python 3.12 using current v7 actions; sixteen policy assertions prevent workflow drift.

## Latest cycle: locate unresolved references at their source lines

### Why this was selected

Resolving the 26 reported references still requires content-owner judgment, so
the notes themselves remained untouched. The read-only report named each source
file and target but not the occurrence lines; duplicate targets were collapsed
without retaining where every occurrence appeared. That made safe owner review
needlessly manual.

### Changes

- Switched wiki-link and Markdown-link discovery from value-only matching to
  position-aware matching while preserving existing resolution behavior.
- Added a sorted, unique, positive `lines` array to every unresolved or
  ambiguous diagnostic; equivalent duplicate targets retain all distinct source
  lines while remaining one diagnostic.
- Updated the human report to print `line N` or `lines N, M` and sort each
  source group by first occurrence, making the output follow note context.
- Strengthened existing exporter fixtures across wiki, ambiguous, Markdown,
  duplicate, CLI, and whole-vault integrity paths.
- Synchronized the canonical metadata-only dataset to both tracked repositories;
  note/canvas content and the 55-note/99-link graph remain unchanged.
- Aligned the portfolio consumer contract with both supported diagnostic types
  (`wikilink` and `markdown`) and required non-empty, sorted, unique positive
  source lines through isolated mutation fixtures.

### Verification and scores

- Test-first evidence: all three focused source-location contracts failed; the
  old schema had no `lines` field and the report had no location text.
- Downstream test-first evidence: the portfolio validator helper did not exist,
  and review exposed that its inline check rejected the exporter's supported
  `markdown` diagnostic type.
- Focused source and downstream schema suites passed after implementation.
- Canonical sync and read-only check report byte-identical source/public copies.
- The real report still contains 26 unresolved and zero ambiguous references;
  it now reveals 27 occurrence lines, including `Eph 5_25-27` on lines 3 and 5.
- Full source discovery passed all 30 exporter, synchronization, redirect, and
  workflow tests; Python compilation and `git diff --check` passed.
- The paired portfolio gate passed 24 Python contracts, deterministic finance
  and sitemap checks, all site contracts, four Chromium journeys, recursive
  syntax checks, and a zero-vulnerability npm audit.
- Correctness/reliability: 7/10 → 9/10 (deduplication no longer discards distinct source locations).
- Verifiability: 7/10 → 10/10 (producer and consumer enforce the same located two-syntax schema).
- Maintainability: 7/10 → 9/10 (one diagnostic recorder owns deduplication and location merging).
- Performance: 10/10 → 10/10 (position accounting remains negligible for 55 small notes).
- Security/robustness: 9/10 → 9/10 (strict UTF-8 and containment behavior are unchanged).
- Developer/content-owner experience: 5/10 → 9/10 (every unresolved target now points directly to review context).

### Lessons and process improvements

- Deduplication should remove repeated decisions, not erase occurrence evidence;
  aggregate locations on the canonical diagnostic key.
- Validate generated schemas at both producer and consumer boundaries. A branch
  with zero live examples can otherwise drift despite having source fixtures.
- When content intent blocks safe edits, improve the evidence available to the
  owner without guessing at the content decision.

## Previous cycle: make the two-repository Git handoff observable and opt-in

### Why this was selected

The 26 unresolved references remain content-owner decisions, so speculative
theological edits were excluded. Dataset generation and copying already used
one canonical payload, but operators still had to inspect and commit two Git
repositories manually. That gap made it easy to forget one repository, include
unstaged work accidentally, or assume the two histories were transactional.

### Changes

- Added `--git-status`, a read-only action that first verifies both generated
  copies and then reports the complete short status of the source and public
  repositories from one command.
- Added `--commit-staged`, which requires current byte-identical datasets,
  refuses all commits if either repository has unstaged or untracked work, and
  requires the relevant dataset in every non-empty index.
- Preflights Git author and committer identities in every pending repository
  before creating the first commit, then reports each resulting short revision.
- Kept staging and pushing explicitly outside the helper; separate commits are
  honest about Git's non-transactional cross-repository boundary and safe to
  retry if a later repository hook fails.
- Added four isolated CLI contracts covering read-only reporting, all-or-none
  preflight refusal, dataset-index enforcement, separate commits, clean final
  status, custom messages, and the no-push guarantee; coverage rose from 26 to
  30 tests.
- Documented the intentional stage/status/commit/push workflow and safeguards.

### Verification and scores

- Test-first evidence: all three initial CLI contracts failed with argparse
  errors because neither opt-in action existed.
- Focused regression passed all new status/commit paths after implementation;
  self-review added the fourth dataset-index enforcement contract.
- Full discovery passed 30 tests; the source export and portfolio copy remain
  current and byte-identical, and Python compilation plus `git diff --check`
  passed.
- A real `--git-status` run named exactly the two files changed by this cycle in
  the vault repository and reported the sibling portfolio repository clean.
- Correctness/reliability: 6/10 → 9/10 (forgotten or partially prepared Git
  state now fails before either commit).
- Verifiability: 5/10 → 10/10 (both repositories and every mutation boundary
  have isolated real-Git fixtures).
- Maintainability: 7/10 → 9/10 (one script owns generation, freshness, status,
  and the conservative commit handoff).
- Developer experience: 5/10 → 9/10 (one report and one explicit commit action
  replace error-prone directory switching while retaining operator control).
- Security/robustness: 6/10 → 9/10 (the helper cannot stage, push, or silently
  include forgotten work).

### Lessons and process improvements

- Cross-repository convenience should expose the non-atomic boundary instead
  of pretending it can provide a transaction.
- Staging is the operator's intent boundary: tooling may validate it, but should
  not infer a note/content scope and stage files automatically.
- Repository-specific test discovery paths belong in the cycle load checklist;
  the initial `tools/tests` assumption failed before the documented `tools`
  command restored a green baseline.

## Previous cycle: fail closed on undecodable vault sources

### Why this was selected

The 26 unresolved references remain content-owner decisions, so changing them
would be speculative. Exporter review exposed a higher-confidence correctness
bug: Markdown and canvas reads used `errors="ignore"`. Invalid UTF-8 bytes were
silently deleted, which could alter public note content or even turn corrupt
canvas bytes into apparently valid JSON despite the lossless-export promise.

### Changes

- Added one byte-preserving UTF-8 source reader shared by Markdown and canvas
  ingestion.
- Invalid UTF-8 now aborts export with a concise source kind and vault-relative
  path while retaining the original `UnicodeDecodeError` as its cause.
- Reading bytes before decoding also preserves CRLF and other valid source
  newline sequences instead of applying universal-newline conversion.
- Added three isolated contracts for CRLF preservation, corrupt note failure,
  and corrupt-but-otherwise-valid canvas failure; coverage increased from 23
  to 26 tests.
- Documented the strict source-encoding and newline contract.

### Verification and scores

- Test-first evidence: all three contracts failed—the CRLF body was normalized
  to LF, and neither invalid source raised an error.
- Focused regression: all three passed after the shared reader replaced both
  permissive calls.
- Full discovery passed 26 tests in 0.090s; source regeneration and the public
  portfolio copy remain current and byte-identical.
- The read-only report remains exactly 26 unresolved wiki-links across seven
  notes and zero ambiguous links; canonical output did not change.
- Python compilation and `git diff --check` passed; hosted evidence is recorded
  in the Cycle 116 completion summary.
- Correctness/reliability: 5/10 → 10/10 (source text is preserved exactly or
  rejected rather than silently rewritten).
- Verifiability: 7/10 → 10/10 (note, canvas, and newline-loss modes have direct
  isolated fixtures).
- Maintainability: 8/10 → 9/10 (one reader owns encoding policy and contextual
  errors).
- Performance: 10/10 → 10/10 (one byte read and UTF-8 decode replaces one text
  read for this small vault).
- Security/robustness: 6/10 → 9/10 (malformed input can no longer bypass JSON or
  content checks through discarded bytes).

### Lessons and process improvements

- Never combine “lossless” export with permissive decode errors; silent repair
  is data corruption even when the resulting text looks plausible.
- A corrupt fixture should include bytes around otherwise valid structure so
  tests prove the decoder—not a later parser—owns the failure.
- When the top content opportunity needs owner intent, continue with a
  reversible tooling defect supported by direct evidence.

## Previous cycle: resolve and diagnose explicit Markdown note paths

### Why this was selected

The higher-impact content backlog requires owner intent for 26 theological and
Scripture references, so speculative note edits were excluded. The safe
exporter branch for regular Markdown `.md` links decoded only `%20`, understood
only exact-case source-relative paths, treated vault-root paths as filesystem
escapes, and silently discarded every resolution failure.

### Changes

- Added URL-aware Markdown note destination parsing with fragment/query and
  optional title removal, complete percent decoding, and external-URL exclusion.
- Resolved both source-relative and vault-root paths through the same
  case-insensitive canonical note index used by explicit wiki paths.
- Kept resolved targets inside the vault even across `..` segments or symlinks;
  escape attempts become visible unresolved diagnostics.
- Added Markdown diagnostic deduplication alongside wiki diagnostics while
  preserving self-link and duplicate-edge behavior.
- Added two isolated contracts spanning relative paths, vault-root paths,
  casing, URL encoding, fragments, titles, missing duplicates, root escapes,
  and ignored HTTPS `.md` URLs; documented the expanded contract.

### Verification and scores

- Test-first evidence: the path fixture resolved only the relative edge and
  missed the vault-root target; the diagnostic fixture reported zero instead
  of two unresolved internal links.
- Focused regression: both new fixtures passed after implementation.
- `python3 -m unittest discover -s tools -p 'test_*.py'`: 23 passed in 0.110s
  (up from 21).
- `python3 tools/sync_public_viewer.py --check`: source export and portfolio
  copy remain current and byte-identical.
- The read-only report remains exactly 26 unresolved wiki-links across seven
  notes and zero ambiguous links; the real vault has no internal Markdown
  `.md` links, so both committed datasets remain byte-identical.
- Python compilation and `git diff --check` passed.
- Correctness/reliability: 5/10 → 9/10 (explicit Markdown paths now share
  deterministic vault semantics instead of filesystem accidents).
- Verifiability: 4/10 → 9/10 (success, failure, deduplication, containment, and
  external exclusion all have fixtures).
- Maintainability: 6/10 → 8/10 (destination parsing is isolated and canonical
  path lookup is reused).
- Performance: 10/10 → 10/10 (linear note scanning and indexed lookup are
  unchanged in practical cost).
- Security/robustness: 6/10 → 9/10 (resolved paths cannot escape the vault and
  external URLs cannot pollute internal diagnostics).

### Lessons and process improvements

- A resolver should never silently drop internal failures while a parallel
  link syntax has diagnostics; link-integrity semantics need to converge.
- Parse URL structure before filesystem resolution, then canonicalize through
  the known-note index rather than trusting raw path casing.
- When the live corpus lacks a syntax branch, preserve future correctness with
  isolated fixtures and require byte-identical production output.

## Previous cycle: modernize and policy-test CI

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

- Cycle 69: added verified dual-repository status and conservative staged-only
  commits without automatic staging or pushing.
- Cycle 68: made note/canvas UTF-8 decoding lossless and fail-closed with exact
  relative-path diagnostics.
- Cycle 67: added path-aware Markdown note resolution and unresolved-link
  diagnostics without changing the current public dataset.
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
| — | Preserve source locations for link diagnostics | Observability / DX | Medium | Small-medium / low | Twenty-six diagnostics now retain 27 exact occurrence lines and the public consumer validates the shared schema | Completed in Cycle 70 |
| — | Add an opt-in paired commit/status helper | Process / reliability | Low-medium | Medium / medium | Read-only dual status and preflighted staged-only commits preserve separate histories and never push | Completed in Cycle 69 |
| — | Fail closed on invalid UTF-8 source bytes | Correctness / robustness | High | Small / low | Note/canvas corruption and newline preservation now have isolated contracts | Completed in Cycle 68 |
| — | Resolve and diagnose Markdown links with explicit path semantics | Correctness / maintainability | Low currently | Small-medium / low | Relative/root paths and internal failures now share canonical resolution and diagnostics | Completed in Cycle 67 |
| — | Modernize and policy-test GitHub Actions | Process / observability | Medium | Small-medium / low | setup-python v7 plus sixteen policy assertions enforce the complete bounded gate | Completed in Cycle 66 |
| — | Retire the duplicate local viewer without breaking legacy URLs | Maintainability / security | Medium-high | Small-medium / low | Two contract-tested compatibility redirects replace the active 20 KB CDN-driven duplicate | Completed in Cycle 65 |

## Next cycle

Local next: obtain content-owner classification for the 26 unresolved references
before changing notes; no remaining high-confidence content correction should
guess at theological intent. Workspace next: rotate to CardFitSG and inspect its
current correctness and verification backlog.
