#!/usr/bin/env python3
"""Assemble the public vault dataset from discovered sources and resolved links."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote, unquote

if __package__:
    from .vault_link_resolution import (
        MARKDOWN_LINK_RE,
        WIKILINK_RE,
        resolve_markdown_reference,
        resolve_wikilink,
    )
    from .vault_source_discovery import (
        discover_vault,
        exclusion_reason,
        note_reference_key,
        parse_canvas,
        read_source_text,
        rel,
    )
else:
    from vault_link_resolution import (
        MARKDOWN_LINK_RE,
        WIKILINK_RE,
        resolve_markdown_reference,
        resolve_wikilink,
    )
    from vault_source_discovery import (
        discover_vault,
        exclusion_reason,
        note_reference_key,
        parse_canvas,
        read_source_text,
        rel,
    )


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


def serialize_dataset(data: dict) -> str:
    """Return the canonical, deterministic representation of a vault dataset."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def _excluded_canvas_target(file_value: str, index) -> str | None:
    if file_value in index.excluded_paths:
        return file_value
    resolved = index.by_path.get(note_reference_key(file_value))
    if resolved in index.excluded_paths:
        return resolved
    return None


def _publish_canvas(text: str, canvas: dict, index) -> tuple[str, dict]:
    """Keep the original canvas text unless it points at an excluded note."""
    if not index.excluded_paths:
        return text, canvas
    removed_ids: set[str] = set()
    kept_nodes = []
    removed = False
    for node in canvas.get("nodes", []):
        file_value = node.get("file")
        if (
            node.get("type") == "file"
            and isinstance(file_value, str)
            and _excluded_canvas_target(file_value, index) is not None
        ):
            removed = True
            node_id = node.get("id")
            if isinstance(node_id, str):
                removed_ids.add(node_id)
            continue
        kept_nodes.append(node)
    if not removed:
        return text, canvas
    kept_edges = [
        edge
        for edge in canvas.get("edges", [])
        if edge.get("fromNode") not in removed_ids and edge.get("toNode") not in removed_ids
    ]
    published = dict(canvas)
    published["nodes"] = kept_nodes
    published["edges"] = kept_edges
    return json.dumps(published, indent=2, ensure_ascii=False), published


def assemble_dataset(discovered) -> dict:
    """Build nodes, resolved edges, and link diagnostics from one discovery pass."""
    root = discovered.root
    index = discovered.index
    md_files = discovered.md_files
    canvas_files = discovered.canvas_files
    known_paths = {
        rel(path, root)
        for path in md_files
        if rel(path, root) not in index.excluded_paths
    }

    nodes: list[dict] = []
    links: list[dict] = []
    seen_links: set[tuple[str, str, str]] = set()
    unresolved_links: list[dict] = []
    ambiguous_links: list[dict] = []
    diagnostics_by_key: dict[tuple[str, str, str], dict] = {}

    def record_link_diagnostic(
        *,
        source: str,
        reference: str,
        link_type: str,
        kind: str,
        line: int,
        candidates: list[str] | None = None,
        reason: str | None = None,
    ) -> None:
        diagnostic_key = (source, note_reference_key(reference), kind)
        diagnostic = diagnostics_by_key.get(diagnostic_key)
        if diagnostic is not None:
            diagnostic["lines"] = sorted({*diagnostic["lines"], line})
            return

        diagnostic = {
            "source": source,
            "reference": unquote(reference).strip(),
            "type": link_type,
            "lines": [line],
        }
        if reason:
            diagnostic["reason"] = reason
        if candidates:
            diagnostic["candidates"] = candidates
            ambiguous_links.append(diagnostic)
        else:
            unresolved_links.append(diagnostic)
        diagnostics_by_key[diagnostic_key] = diagnostic

    def record_resolution(
        *,
        source: str,
        reference: str,
        link_type: str,
        line: int,
        target: str | None,
        candidates: tuple[str, ...] | list[str],
        excluded: bool,
    ) -> None:
        if excluded and target and target != source:
            record_link_diagnostic(
                source=source,
                reference=reference,
                link_type=link_type,
                kind="excluded",
                line=line,
                reason=exclusion_reason(index, target),
            )
            return
        if target and target != source:
            key = (source, target, link_type)
            if key not in seen_links:
                links.append({"source": source, "target": target, "type": link_type})
                seen_links.add(key)
            return
        if not target:
            kind = "ambiguous" if candidates else "unresolved"
            display = list(candidates)
            if candidates and index.excluded_paths:
                display = [
                    f"{candidate} (excluded from export)"
                    if candidate in index.excluded_paths
                    else candidate
                    for candidate in candidates
                ]
            record_link_diagnostic(
                source=source,
                reference=reference,
                link_type=link_type,
                kind=kind,
                line=line,
                candidates=display if candidates else None,
            )

    note_count = 0
    for path in md_files:
        relative = rel(path, root)
        if relative in index.excluded_paths:
            continue
        text = discovered.note_texts[relative]
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
        note_count += 1

        for match in WIKILINK_RE.finditer(text):
            target_text = match.group(1)
            resolution = resolve_wikilink(index, target_text)
            record_resolution(
                source=relative,
                reference=target_text,
                link_type="wikilink",
                line=text.count("\n", 0, match.start()) + 1,
                target=resolution.target,
                candidates=resolution.candidates,
                excluded=resolution.excluded,
            )

        for match in MARKDOWN_LINK_RE.finditer(text):
            target_text, resolution = resolve_markdown_reference(
                root, path, match.group(1), index
            )
            if target_text is None or resolution is None:
                continue
            record_resolution(
                source=relative,
                reference=target_text,
                link_type="markdown",
                line=text.count("\n", 0, match.start()) + 1,
                target=resolution.target,
                candidates=resolution.candidates,
                excluded=resolution.excluded,
            )

    for path in canvas_files:
        relative = rel(path, root)
        text = read_source_text(path, root, "canvas")
        canvas = parse_canvas(text, relative)
        published_text, published_canvas = _publish_canvas(text, canvas, index)
        nodes.append(
            {
                "id": relative,
                "path": relative,
                "title": path.stem,
                "type": "canvas",
                "group": "Canvas",
                "excerpt": (
                    f"Canvas with {len(published_canvas.get('nodes', []))} nodes "
                    f"and {len(published_canvas.get('edges', []))} edges."
                ),
                "content": published_text,
                "headings": [],
                "wordCount": 0,
                "obsidianUri": "obsidian://open?vault=Seeking-Biblical-Truth&file=" + quote(relative),
            }
        )
        cursor = 0
        for canvas_node in canvas.get("nodes", []):
            target = canvas_node.get("file")
            if canvas_node.get("type") == "file" and target in known_paths:
                key = (relative, target, "canvas")
                if key not in seen_links:
                    links.append({"source": relative, "target": target, "type": "canvas"})
                    seen_links.add(key)
            elif (
                canvas_node.get("type") == "file"
                and isinstance(target, str)
                and index.excluded_paths
            ):
                excluded_path = _excluded_canvas_target(target, index)
                if excluded_path is None:
                    continue
                found = text.find(target, cursor)
                if found < 0:
                    found = text.find(target)
                line = 1 if found < 0 else text.count("\n", 0, found) + 1
                if found >= 0:
                    cursor = found + len(target)
                record_link_diagnostic(
                    source=relative,
                    reference=target,
                    link_type="canvas",
                    kind="excluded",
                    line=line,
                    reason=exclusion_reason(index, excluded_path),
                )

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
            "notes": note_count,
            "canvas": len(canvas_files),
            "nodes": len(nodes),
            "links": len(links),
            "unresolvedLinks": len(unresolved_links),
            "ambiguousLinks": len(ambiguous_links),
        },
        "nodes": nodes,
        "links": links,
        "folders": groups,
        "linkDiagnostics": {
            "unresolved": unresolved_links,
            "ambiguous": ambiguous_links,
        },
    }


def build_dataset(root: Path) -> dict:
    """Discover sources, resolve links, and assemble one public dataset."""
    return assemble_dataset(discover_vault(root))
