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
- `pages/`: public static viewer for GitHub Pages.
  - `pages/index.html`: interactive graph and note browser.
  - `pages/vault-data.json`: generated graph data from the real notes.
- `tools/`: maintenance scripts.
  - `tools/generate_vault_data.py`: regenerates the public viewer dataset from Markdown and canvas files.
- `index.html`: compatibility redirect to `pages/`.

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

Run locally:

```bash
python3 -m http.server 8001
```

Open:

```text
http://127.0.0.1:8001/pages/
```

The public viewer defaults to rendered Markdown note previews and lets users toggle to the raw `.md` source. Internal wiki links, regular Markdown links, backlinks, and Obsidian deep links are all preserved where possible in the static web view.

Regenerate graph data after changing notes:

```bash
python3 tools/generate_vault_data.py
```

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
- Keep public web files in `pages/`.
- Preserve the rendered/raw note toggle in the public viewer unless there is a stronger replacement.
- Do not commit API keys, private local paths, generated caches, or broken prototypes.
- Do not reintroduce `bible_repo/holybooks` as a gitlink unless a valid `.gitmodules` URL is also committed.
- After editing notes, run `python3 tools/generate_vault_data.py` and validate that `pages/vault-data.json` parses.
- If the portfolio repo also needs the updated viewer data, copy `pages/vault-data.json` into `/home/alph/codex/alphaeusng.github.io/pages/seeking-biblical-truth/vault-data.json`.
