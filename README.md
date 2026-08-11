# Seeking Biblical Truth

An Obsidian vault for rigorous exploration of Scripture, doctrine, truth-seeking, and Christian reasoning.

## Original Intent

Welcome to my Obsidian Knowledge Base. This guide exists to help people access and explore my thoughts, and contribute if they want to.

The deeper idea is a Christian discussion and study environment where the main goal is **an open search for the closest Biblical truth**.

Important ideas from the original README:

- Use Obsidian to browse the vault as an interconnected knowledge base.
- Make everything easy to link to everything else.
- Build toward better tools for theological dialogue.
- Explore a robust “truth weight” metric for claims, likely determined by community and similar in spirit to Community Notes.
- Make it easy for laypeople and scholars to contribute or refute ongoing discussions.
- Summarize long chains of discussion accurately.
- Preserve graph-style visualization, while improving on Obsidian’s limitations around nested ideas such as books, chapters, and verses.

## Repository Structure

- `Word of God/`: Scripture notes and topical studies.
- `Heritage Christian University/`: coursework and study notes.
- `Meaning of ideas, words/`: definitions and concept notes.
- `Journal/`: journal notes.
- `Big Picture.canvas`: Obsidian canvas used by the graph generator.
- `.obsidian/`: Obsidian settings and selected plugins for the full local vault experience.
- `pages/`: generated export plus compatibility route for GitHub Pages.
  - `pages/index.html`: redirect to the canonical portfolio viewer.
  - `pages/vault-data.json`: generated graph data from the real notes.
- `tools/`: maintenance scripts.
  - `tools/generate_vault_data.py`: regenerates this repo's viewer dataset from Markdown and canvas files.
  - `tools/sync_public_viewer.py`: regenerates and byte-synchronizes both tracked dataset copies, reports both Git worktrees, and can commit explicitly staged sync changes without pushing.
- `index.html`: compatibility redirect to the canonical portfolio viewer.

## View In Obsidian

1. Install Obsidian: https://obsidian.md/download
2. Clone this repository:

```bash
git clone https://github.com/AlphaeusNg/Seeking-Biblical-Truth.git
cd Seeking-Biblical-Truth
```

3. In Obsidian, choose **Open folder as vault** and select this folder.
4. Use Obsidian graph view, canvases, backlinks, and installed vault plugins for the full experience.

The public web viewer includes `obsidian://open?vault=Seeking-Biblical-Truth` links. Those links work after this folder is opened as an Obsidian vault with the matching vault name.

## Public Viewer

The canonical viewer is:

```text
https://alphaeusng.github.io/pages/seeking-biblical-truth/
```

The historical GitHub Pages paths for this repository remain as no-index
redirects. To preview the canonical UI locally, serve the sibling portfolio
checkout:

```bash
cd /home/alph/projects/alphaeusng.github.io
python3 -m http.server 8001
# open http://127.0.0.1:8001/pages/seeking-biblical-truth/
```

The public viewer defaults to rendered Markdown note previews and lets users toggle to the raw `.md` source. Internal wiki links, regular Markdown links, backlinks, and Obsidian deep links are all preserved where possible in the static web view.

Regenerate and synchronize graph data after changing notes. The canonical
portfolio checkout must exist beside this repo under `/home/alph/projects/`:

```bash
python3 tools/sync_public_viewer.py
```

Validate the exporter and confirm both committed copies are current and
byte-identical:

```bash
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/sync_public_viewer.py --check
python3 -m compileall -q tools
```

The same lossless-export, link-integrity, freshness, and Python checks run in
least-privilege GitHub Actions on every `main` push and pull request.
Source notes and canvases must be valid UTF-8. Export fails with the exact
vault-relative path instead of deleting undecodable bytes, and valid source
newline sequences are preserved in public note content.

The generated `linkDiagnostics` section reports missing internal Markdown and
wiki-link references, plus ambiguous wiki-links, without failing the export.
Markdown note links honor source-relative and vault-root paths, URL encoding,
anchors, optional titles, and canonical path casing. Repeated equivalent
references in one note are collapsed with every distinct source line retained,
while ambiguous entries list every candidate path; external URLs are
intentionally excluded from vault diagnostics. The human-readable report prints
those line numbers so each reference can be reviewed in context without
changing note content.

For a deterministic human-readable report grouped by source note, run:

```bash
python3 tools/generate_vault_data.py --report-links
```

Report mode is read-only: it rebuilds diagnostics from the vault sources in
memory and does not touch either tracked dataset copy.

### Optional two-repository handoff

After synchronizing, inspect both repositories from one read-only command:

```bash
python3 tools/sync_public_viewer.py --git-status
```

The command first proves both dataset copies are current and byte-identical,
then prints the complete short Git status for this vault and the sibling
portfolio. To create the two local commits, explicitly stage the intended
source notes/canvases and both generated datasets, then opt in:

```bash
git add -- 'path/to/edited-note.md' pages/vault-data.json
git -C ../alphaeusng.github.io add -- pages/seeking-biblical-truth/vault-data.json
python3 tools/sync_public_viewer.py --commit-staged --commit-message "Sync public vault data"
```

The helper aborts before either commit if a repository contains any unstaged or
untracked work, or if a repository has staged changes without its dataset. It
commits each repository's already-staged index separately and never stages,
pushes, or claims cross-repository atomicity. Review the resulting commits and
push the two repositories separately.

## Contributing

```bash
git checkout -b your-branch-name
git add .
git commit -m "Describe your changes"
git push origin your-branch-name
```

Then open a pull request on GitHub.

## For Future Agents

- Treat this repo primarily as an Obsidian vault, not as an app codebase.
- Keep notes and canvases in content folders, not in `pages/` or `tools/`.
- Put maintenance scripts in `tools/`.
- Keep the generated export and compatibility redirect in `pages/`; edit the
  canonical viewer only in the sibling portfolio repository.
- Preserve the canonical viewer's rendered/raw note toggle unless there is a stronger replacement.
- Do not commit API keys, private local paths, generated caches, or broken prototypes.
- Do not reintroduce `bible_repo/holybooks` as a gitlink unless a valid `.gitmodules` URL is also committed.
- After editing notes, run `python3 tools/sync_public_viewer.py`; it updates both the source export and the portfolio viewer copy from one canonical in-memory payload.
- Run `python3 tools/sync_public_viewer.py --check` before committing. Commit and push each repository separately when both copies changed.
