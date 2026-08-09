#!/usr/bin/env python3
"""Generate the public graph dataset from this Obsidian vault."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote


EXCLUDED_PARTS = {".git", "__pycache__", "pages", "tools"}
EXCLUDED_ROOT_FILES = {"AGENTS.md", "PROGRESS.md", "README.md"}


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def folder_for(path: Path, root: Path) -> str:
    parts = path.relative_to(root).parts
    return parts[0] if len(parts) > 1 else "Root"


def excerpt(text: str) -> str:
    cleaned = re.sub(r"```.*?```", "", text, flags=re.S)
    cleaned = re.sub(r"!\[[^\]]*]\([^)]+\)", "", cleaned)
    cleaned = re.sub(r"\[[^\]]+]\([^)]+\)", lambda m: m.group(0).split("](")[0][1:], cleaned)
    cleaned = re.sub(r"[#>*_`\-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:360]


def is_content_file(path: Path) -> bool:
    return (
        path.as_posix() not in EXCLUDED_ROOT_FILES
        and not any(part in EXCLUDED_PARTS for part in path.parts)
    )


def note_reference_key(value: str) -> str:
    normalized = unquote(value).strip().replace("\\", "/").removeprefix("./")
    if normalized.lower().endswith(".md"):
        normalized = normalized[:-3]
    return normalized.casefold()


def build_dataset(root: Path) -> dict:
    md_files = sorted(path for path in root.rglob("*.md") if is_content_file(path.relative_to(root)))
    canvas_files = sorted(path for path in root.rglob("*.canvas") if is_content_file(path.relative_to(root)))

    by_title: dict[str, list[str]] = {}
    by_path: dict[str, str] = {}
    known_paths: set[str] = set()
    for path in md_files:
        relative = rel(path, root)
        known_paths.add(relative)
        by_title.setdefault(path.stem.casefold(), []).append(relative)
        by_path[note_reference_key(relative)] = relative

    def resolve_wikilink(target_text: str) -> str | None:
        key = note_reference_key(target_text)
        if "/" in key:
            return by_path.get(key)
        matches = by_title.get(key, [])
        return matches[0] if len(matches) == 1 else None

    nodes: list[dict] = []
    links: list[dict] = []
    seen_links: set[tuple[str, str, str]] = set()

    for path in md_files:
        relative = rel(path, root)
        text = path.read_text(encoding="utf-8", errors="ignore")
        headings = re.findall(r"^(#{1,4})\s+(.+)$", text, flags=re.M)
        nodes.append(
            {
                "id": relative,
                "path": relative,
                "title": path.stem,
                "type": "note",
                "group": folder_for(path, root),
                "excerpt": excerpt(text),
                "content": text,
                "headings": [heading.strip() for _, heading in headings[:8]],
                "wordCount": len(re.findall(r"\w+", text)),
                "obsidianUri": "obsidian://open?vault=Seeking-Biblical-Truth&file=" + quote(relative),
            }
        )

        for target_text in re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?]]", text):
            target = resolve_wikilink(target_text)
            if target and target != relative:
                key = (relative, target, "wikilink")
                if key not in seen_links:
                    links.append({"source": relative, "target": target, "type": "wikilink"})
                    seen_links.add(key)

        for target_text in re.findall(r"\[[^\]]+]\(([^)]+\.md)(?:#[^)]*)?\)", text):
            target_path = (path.parent / target_text.replace("%20", " ")).resolve()
            try:
                target = target_path.relative_to(root).as_posix()
            except ValueError:
                target = ""
            if target in known_paths and target != relative:
                key = (relative, target, "markdown")
                if key not in seen_links:
                    links.append({"source": relative, "target": target, "type": "markdown"})
                    seen_links.add(key)

    for path in canvas_files:
        relative = rel(path, root)
        text = path.read_text(encoding="utf-8", errors="ignore")
        try:
            canvas = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid canvas JSON: {relative}") from error
        nodes.append(
            {
                "id": relative,
                "path": relative,
                "title": path.stem,
                "type": "canvas",
                "group": "Canvas",
                "excerpt": f"Canvas with {len(canvas.get('nodes', []))} nodes and {len(canvas.get('edges', []))} edges.",
                "content": text,
                "headings": [],
                "wordCount": 0,
                "obsidianUri": "obsidian://open?vault=Seeking-Biblical-Truth&file=" + quote(relative),
            }
        )
        for canvas_node in canvas.get("nodes", []):
            target = canvas_node.get("file")
            if canvas_node.get("type") == "file" and target in known_paths:
                key = (relative, target, "canvas")
                if key not in seen_links:
                    links.append({"source": relative, "target": target, "type": "canvas"})
                    seen_links.add(key)

    groups = sorted({node["group"] for node in nodes})
    for group in groups:
        nodes.append(
            {
                "id": f"folder::{group}",
                "path": "",
                "title": group,
                "type": "folder",
                "group": group,
                "excerpt": f"{group} folder",
                "content": "",
                "headings": [],
                "wordCount": 0,
                "obsidianUri": "",
            }
        )

    for node in list(nodes):
        if node["type"] != "folder":
            links.append({"source": f"folder::{node['group']}", "target": node["id"], "type": "contains"})

    return {
        "generatedFrom": "https://github.com/AlphaeusNg/Seeking-Biblical-Truth",
        "counts": {
            "notes": len(md_files),
            "canvas": len(canvas_files),
            "nodes": len(nodes),
            "links": len(links),
        },
        "nodes": nodes,
        "links": links,
        "folders": groups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Vault root. Defaults to current directory.")
    parser.add_argument("--output", type=Path, default=Path("pages/vault-data.json"), help="Output JSON path.")
    args = parser.parse_args()

    data = build_dataset(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {data['counts']} to {args.output}")


if __name__ == "__main__":
    main()
