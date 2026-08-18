#!/usr/bin/env python3
"""Generate the public graph dataset from this Obsidian vault."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


EXCLUDED_PARTS = {".git", "__pycache__", "pages", "tools"}
EXCLUDED_ROOT_FILES = {"AGENTS.md", "PROGRESS.md", "README.md"}


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def folder_for(path: Path, root: Path) -> str:
    parts = path.relative_to(root).parts
    return parts[0] if len(parts) > 1 else "Root"


def read_source_text(path: Path, root: Path, kind: str) -> str:
    """Decode a source exactly as UTF-8 or fail with its vault-relative path."""
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Invalid UTF-8 in {kind}: {rel(path, root)}") from error


def require_source_within_vault(path: Path, root: Path, kind: str) -> None:
    """Reject source entries whose resolved bytes live outside the vault."""
    relative = rel(path, root)
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError(f"Cannot resolve {kind} source: {relative}") from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"{kind.capitalize()} source resolves outside vault: {relative}"
        ) from error


def excerpt(text: str) -> str:
    cleaned = re.sub(r"```.*?```", "", text, flags=re.S)
    cleaned = re.sub(r"!\[[^\]]*]\([^)]+\)", "", cleaned)
    cleaned = re.sub(r"\[[^\]]+]\([^)]+\)", lambda m: m.group(0).split("](")[0][1:], cleaned)
    cleaned = re.sub(r"[#>*_`\-]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:360]


def is_hidden_part(part: str) -> bool:
    return part.startswith(".")


def is_content_file(path: Path) -> bool:
    return (
        path.as_posix() not in EXCLUDED_ROOT_FILES
        and not any(part in EXCLUDED_PARTS or is_hidden_part(part) for part in path.parts)
    )


def note_reference_key(value: str) -> str:
    normalized = unquote(value).strip().replace("\\", "/").removeprefix("./")
    if normalized.lower().endswith(".md"):
        normalized = normalized[:-3]
    return normalized.casefold()


def markdown_note_destination(value: str) -> str | None:
    """Return a decoded internal Markdown note path, excluding URL/title syntax."""
    raw = value.strip()
    if raw.startswith("<"):
        closing = raw.find(">")
        if closing < 0:
            return None
        destination = raw[1:closing].strip()
    else:
        match = re.fullmatch(
            r"(?P<destination>.+?\.md(?:[?#]\S*)?)"
            r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?",
            raw,
            flags=re.I,
        )
        if not match:
            return None
        destination = match.group("destination")

    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        return None
    decoded_path = unquote(parsed.path).strip().replace("\\", "/")
    if not decoded_path.lower().endswith(".md"):
        return None
    return decoded_path


def build_dataset(root: Path) -> dict:
    root = root.resolve()
    md_files = sorted(path for path in root.rglob("*.md") if is_content_file(path.relative_to(root)))
    canvas_files = sorted(path for path in root.rglob("*.canvas") if is_content_file(path.relative_to(root)))
    for path in md_files:
        require_source_within_vault(path, root, "note")
    for path in canvas_files:
        require_source_within_vault(path, root, "canvas")

    by_title: dict[str, list[str]] = {}
    by_path: dict[str, str] = {}
    known_paths: set[str] = set()
    for path in md_files:
        relative = rel(path, root)
        known_paths.add(relative)
        by_title.setdefault(path.stem.casefold(), []).append(relative)
        # Case-folded, percent-decoded paths must name one note on every filesystem.
        key = note_reference_key(relative)
        existing = by_path.get(key)
        if existing is not None and existing != relative:
            left, right = sorted((existing, relative), key=str.casefold)
            raise ValueError(f"Canonical note path collision: {left} and {right}")
        by_path[key] = relative

    def resolve_wikilink(target_text: str) -> tuple[str | None, list[str]]:
        key = note_reference_key(target_text)
        if "/" in key:
            target = by_path.get(key)
            return target, [target] if target else []
        matches = by_title.get(key, [])
        return (matches[0] if len(matches) == 1 else None), matches

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
        if candidates:
            diagnostic["candidates"] = candidates
            ambiguous_links.append(diagnostic)
        else:
            unresolved_links.append(diagnostic)
        diagnostics_by_key[diagnostic_key] = diagnostic

    for path in md_files:
        relative = rel(path, root)
        text = read_source_text(path, root, "note")
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

        for match in re.finditer(
            r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?]]",
            text,
        ):
            target_text = match.group(1)
            target, candidates = resolve_wikilink(target_text)
            if target and target != relative:
                key = (relative, target, "wikilink")
                if key not in seen_links:
                    links.append({"source": relative, "target": target, "type": "wikilink"})
                    seen_links.add(key)
            elif not target:
                kind = "ambiguous" if candidates else "unresolved"
                record_link_diagnostic(
                    source=relative,
                    reference=target_text,
                    link_type="wikilink",
                    kind=kind,
                    line=text.count("\n", 0, match.start()) + 1,
                    candidates=candidates,
                )

        for match in re.finditer(r"(?<!!)\[[^\]\n]+]\(([^)\n]+)\)", text):
            raw_target = match.group(1)
            target_text = markdown_note_destination(raw_target)
            if target_text is None:
                continue
            target_path = (
                root / target_text.lstrip("/")
                if target_text.startswith("/")
                else path.parent / target_text
            ).resolve()
            try:
                candidate = target_path.relative_to(root).as_posix()
            except ValueError:
                candidate = ""
            target = by_path.get(note_reference_key(candidate)) if candidate else None
            if target and target != relative:
                key = (relative, target, "markdown")
                if key not in seen_links:
                    links.append({"source": relative, "target": target, "type": "markdown"})
                    seen_links.add(key)
            elif not target:
                record_link_diagnostic(
                    source=relative,
                    reference=target_text,
                    link_type="markdown",
                    kind="unresolved",
                    line=text.count("\n", 0, match.start()) + 1,
                )

    for path in canvas_files:
        relative = rel(path, root)
        text = read_source_text(path, root, "canvas")
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


def serialize_dataset(data: dict) -> str:
    """Return the canonical, deterministic representation of a vault dataset."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_dataset_summary(data: dict) -> str:
    """One-screen vault snapshot for --check / --report-links (no note edits)."""
    counts = data.get("counts") or {}
    diagnostics = data.get("linkDiagnostics") or {}
    unresolved = diagnostics.get("unresolved") or []
    ambiguous = diagnostics.get("ambiguous") or []
    folders = data.get("folders") or []
    return "\n".join(
        [
            (
                f"Vault snapshot: {counts.get('notes', 0)} notes, "
                f"{counts.get('canvas', 0)} canvas, {counts.get('links', 0)} links, "
                f"{len(folders)} folders."
            ),
            (
                f"Link health: {len(unresolved)} unresolved, "
                f"{len(ambiguous)} ambiguous."
            ),
        ]
    )


def format_link_diagnostics(data: dict) -> str:
    """Return unresolved and ambiguous note links grouped for human triage."""
    diagnostics = data["linkDiagnostics"]
    unresolved = diagnostics["unresolved"]
    ambiguous = diagnostics["ambiguous"]
    lines = [
        f"Link diagnostics: {len(unresolved)} unresolved, {len(ambiguous)} ambiguous"
    ]
    if not unresolved and not ambiguous:
        return "\n".join(lines + ["", "No unresolved or ambiguous note links."])

    by_source: dict[str, list[tuple[str, dict]]] = {}
    for kind, entries in (("unresolved", unresolved), ("ambiguous", ambiguous)):
        for diagnostic in entries:
            by_source.setdefault(diagnostic["source"], []).append((kind, diagnostic))

    for source in sorted(by_source, key=str.casefold):
        lines.extend(("", source))
        entries = sorted(
            by_source[source],
            key=lambda item: (
                item[1]["lines"][0],
                item[0] != "unresolved",
                item[1]["type"].casefold(),
                item[1]["reference"].casefold(),
            ),
        )
        for kind, diagnostic in entries:
            source_lines = diagnostic["lines"]
            location = (
                f"line {source_lines[0]}"
                if len(source_lines) == 1
                else "lines " + ", ".join(str(line) for line in source_lines)
            )
            lines.append(
                f"  - {kind} {diagnostic['type']} ({location}): "
                f"{diagnostic['reference']}"
            )
            candidates = diagnostic.get("candidates", [])
            if candidates:
                lines.append("    candidates: " + ", ".join(candidates))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Vault root. Defaults to current directory.")
    parser.add_argument("--output", type=Path, default=Path("pages/vault-data.json"), help="Output JSON path.")
    report = parser.add_mutually_exclusive_group()
    report.add_argument(
        "--report-links",
        action="store_true",
        help="Print unresolved/ambiguous links without writing the dataset.",
    )
    report.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed dataset matches the vault and print a summary. Does not write.",
    )
    args = parser.parse_args()

    data = build_dataset(args.root.resolve())
    if args.report_links:
        print(format_dataset_summary(data))
        print()
        print(format_link_diagnostics(data))
        return
    if args.check:
        print(format_dataset_summary(data))
        print()
        print(format_link_diagnostics(data))
        payload = serialize_dataset(data)
        try:
            current = args.output.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            parser.exit(1, f"ERROR: committed dataset missing or unreadable: {args.output}\n")
        if current != payload:
            parser.exit(1, f"ERROR: committed dataset is stale: {args.output}\n")
        print("Committed dataset matches vault sources.")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialize_dataset(data), encoding="utf-8")
    print(f"Wrote {data['counts']} to {args.output}")


if __name__ == "__main__":
    main()
