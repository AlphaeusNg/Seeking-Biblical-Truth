# AGENTS.md — Seeking-Biblical-Truth

**Repo:** https://github.com/AlphaeusNg/Seeking-Biblical-Truth  
**Local:** `/home/alph/projects/Seeking-Biblical-Truth`  
**Hub:** `/home/alph/projects/AGENTS.md`  
**Public viewer:** https://alphaeusng.github.io/pages/seeking-biblical-truth/  
**Viewer lives in:** `/home/alph/projects/alphaeusng.github.io/pages/seeking-biblical-truth/`

## Purpose

Obsidian-oriented **Scripture study vault**: notes, topics, journal, canvas overview. Export tooling builds `vault-data.json` for the portfolio graph/list viewer.

## Structure

```text
Word of God/                 # Primary notes (Topics, OT, NT, …)
Heritage Christian University/
Journal/
Meaning of ideas, words/
My Search for Truth.md
Big Picture.canvas           # Graph source for export
pages/
  index.html                 # Optional local viewer shell
  vault-data.json            # Generated — do not hand-edit casually
tools/
  generate_vault_data.py     # Export Markdown + canvas → vault-data.json
.obsidian/                   # Editor config (repo may track some of it)
```

## Content vs viewer split

| Concern | Repo |
|---|---|
| Notes, theology content, canvas | **This repo** |
| Public interactive viewer UI (D3/list, Firebase editor if any) | **alphaeusng.github.io** `pages/seeking-biblical-truth/` |
| Verse *memory games* | **VerseKeep** (different product) |

## Commands

```bash
cd /home/alph/projects/Seeking-Biblical-Truth

# Rebuild only this repo's export
python3 tools/generate_vault_data.py

# Preferred after content changes: regenerate both tracked copies in one command
python3 tools/sync_public_viewer.py

# Read-only freshness and cross-repository equality check
python3 tools/sync_public_viewer.py --check

# Read-only unresolved/ambiguous link report grouped by source note
python3 tools/generate_vault_data.py --report-links

# Optional local vault viewer
python3 -m http.server 8001
# open http://127.0.0.1:8001/pages/
```

## Conventions

- Prefer clear Markdown; keep wiki-links/obsidian conventions consistent with existing notes.
- After substantive note or canvas changes, run `tools/sync_public_viewer.py` so the source and portfolio copies cannot drift (two repos still require two commits if both changed).
- Don’t put private pastoral counseling notes here unless intended to be public via export.
- Python tooling: `snake_case`, 4-space indent; run `python3 -m compileall tools` after script edits.

## Deploy

1. Commit vault content (+ regenerated `pages/vault-data.json` if tracked).
2. Push this repo.
3. In portfolio repo, commit synced `vault-data.json` (and viewer code if changed); push `main` for Pages.

## Agent checklist

1. Decide content-only vs viewer-UI vs both.
2. Edit notes under this tree; run `python3 tools/sync_public_viewer.py`.
3. Run the same command with `--check` before committing both changed copies.
4. Validate viewer load on portfolio local server.
