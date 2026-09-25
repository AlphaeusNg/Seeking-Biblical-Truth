#!/usr/bin/env python3
"""Resolve wiki, Markdown, and canvas note references."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote, urlsplit

if __package__:
    from .vault_source_discovery import (
        NoteIndex,
        discover_vault,
        exclusion_reason,
        note_reference_key,
        parse_canvas,
        read_source_text,
        rel,
    )
else:
    from vault_source_discovery import (
        NoteIndex,
        discover_vault,
        exclusion_reason,
        note_reference_key,
        parse_canvas,
        read_source_text,
        rel,
    )


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?]]")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]\n]+]\(([^)\n]+)\)")


class Resolution(NamedTuple):
    target: str | None
    candidates: tuple[str, ...]
    excluded: bool


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


def resolve_wikilink(index: NoteIndex, target_text: str) -> Resolution:
    key = note_reference_key(target_text)
    if "/" in key:
        target = index.by_path.get(key)
        if target is None:
            return Resolution(None, (), False)
        return Resolution(target, (target,), target in index.excluded_paths)
    matches = index.by_title.get(key, [])
    if len(matches) == 1:
        target = matches[0]
        return Resolution(target, (target,), target in index.excluded_paths)
    if matches:
        return Resolution(None, tuple(matches), False)
    return Resolution(None, (), False)


def resolve_markdown_reference(
    root: Path,
    source_file: Path,
    raw_target: str,
    index: NoteIndex,
) -> tuple[str | None, Resolution | None]:
    """Return the authored note path and its resolution, or Nones if not a note."""
    target_text = markdown_note_destination(raw_target)
    if target_text is None:
        return None, None
    target_path = (
        root / target_text.lstrip("/")
        if target_text.startswith("/")
        else source_file.parent / target_text
    ).resolve()
    try:
        candidate = target_path.relative_to(root).as_posix()
    except ValueError:
        candidate = ""
    mapped = index.by_path.get(note_reference_key(candidate)) if candidate else None
    if mapped is None:
        return target_text, Resolution(None, (), False)
    return target_text, Resolution(mapped, (mapped,), mapped in index.excluded_paths)


def _clean_move_spec(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("[[") and cleaned.endswith("]]"):
        cleaned = cleaned[2:-2].split("|", 1)[0]
    cleaned = cleaned.replace("\\", "/").strip()
    return cleaned.split("#", 1)[0].split("?", 1)[0].strip()


def _is_path_spec(value: str) -> bool:
    return (
        "/" in value
        or value.startswith("./")
        or value.startswith("../")
        or value.lower().endswith(".md")
    )


def _normalize_new_path(value: str) -> tuple[str | None, bool]:
    """Return a vault-relative .md path, and whether it escapes the vault."""
    parts: list[str] = []
    for part in value.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None, True
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        return None, True
    relative = "/".join(parts)
    if not relative.lower().endswith(".md"):
        relative += ".md"
    return relative, False


def _display_reference(value: str) -> str:
    return unquote(value).strip()


def _occurrence_line(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _format_lines(lines: list[int]) -> str:
    ordered = sorted(set(lines))
    if len(ordered) == 1:
        return f"line {ordered[0]}"
    return "lines " + ", ".join(str(line) for line in ordered)


def _classify_destination(
    spec: str,
    index: NoteIndex,
    source_path: str | None,
) -> tuple[str, str, list[str], str]:
    """Return status, label, candidates, and an optional explicit detail."""
    cleaned = _clean_move_spec(spec)
    if "://" in cleaned:
        return "outside", cleaned, [], ""
    proposed, escaped = _normalize_new_path(cleaned)
    if escaped:
        return "outside", cleaned, [], ""
    resolution = resolve_wikilink(index, cleaned)
    if resolution.target is None and resolution.candidates:
        return "ambiguous", proposed or cleaned, list(resolution.candidates), ""
    if resolution.target is not None:
        lexical_differs = _is_path_spec(cleaned) and proposed != resolution.target
        if lexical_differs:
            detail = (
                f"The proposed path `{proposed}` has the same canonical note "
                f"identity as `{resolution.target}`."
            )
            return "ambiguous", proposed or cleaned, [resolution.target], detail
        if source_path is not None and resolution.target == source_path:
            return "unchanged", resolution.target, [resolution.target], ""
        return "existing", resolution.target, [resolution.target], ""
    return "new", proposed or cleaned, [], ""


def _sorted_rows(rows: dict[tuple, dict]) -> list[str]:
    items = sorted(
        rows.values(),
        key=lambda item: (
            item["source"].casefold(),
            item["lines"][0],
            item.get("node_id", ""),
            item["reference"].casefold(),
        ),
    )
    rendered = []
    for item in items:
        if item["link_type"] == "canvas":
            node = f", node {item['node_id']}" if item.get("node_id") else ""
            rendered.append(
                f"{item['source']}: file `{item['reference']}` "
                f"({_format_lines(item['lines'])}{node})"
            )
        elif item.get("ambiguous"):
            candidates = ", ".join(item["candidates"])
            rendered.append(
                f"{item['source']}: {item['link_type']} `{item['reference']}` "
                f"({_format_lines(item['lines'])}); candidates: {candidates}"
            )
        else:
            rendered.append(
                f"{item['source']}: {item['link_type']} `{item['reference']}` "
                f"({_format_lines(item['lines'])})"
            )
    return rendered


def inspect_rename(root: Path, source_spec: str, destination_spec: str) -> dict:
    """Collect incoming references for a proposed move without modifying files."""
    discovered = discover_vault(root)
    index = discovered.index
    source_cleaned = _clean_move_spec(source_spec)
    source_resolution = resolve_wikilink(index, source_cleaned)
    report = {
        "source_spec": source_spec,
        "source_status": "missing",
        "source_path": "",
        "source_candidates": [],
        "source_exclusion": "",
        "destination_status": "ambiguous",
        "destination_label": "",
        "destination_candidates": [],
        "destination_detail": "",
        "incoming_collected": False,
        "incoming": {},
        "exit_code": 1,
    }
    if source_resolution.target is None and source_resolution.candidates:
        report["source_status"] = "ambiguous"
        report["source_candidates"] = sorted(
            source_resolution.candidates, key=str.casefold
        )
        report["exit_code"] = 0
    elif source_resolution.target is None:
        report["source_status"] = "missing"
    else:
        report["source_status"] = "resolved"
        report["source_path"] = source_resolution.target
        report["exit_code"] = 0
        if source_resolution.excluded:
            report["source_exclusion"] = exclusion_reason(
                index, source_resolution.target
            )

    status, label, candidates, detail = _classify_destination(
        destination_spec,
        index,
        report["source_path"] or None,
    )
    report["destination_status"] = status
    report["destination_label"] = label
    report["destination_candidates"] = sorted(candidates, key=str.casefold)
    report["destination_detail"] = detail
    if report["source_status"] != "resolved":
        return report

    source_path = report["source_path"]
    wikilinks: dict[tuple, dict] = {}
    markdown_links: dict[tuple, dict] = {}
    ambiguous: dict[tuple, dict] = {}
    for path in discovered.md_files:
        relative = rel(path, discovered.root)
        if relative == source_path:
            continue
        text = discovered.note_texts.get(relative)
        if text is None and relative in index.excluded_paths:
            text = read_source_text(path, discovered.root, "note")
        if text is None:
            continue
        for match in WIKILINK_RE.finditer(text):
            target_text = match.group(1)
            resolution = resolve_wikilink(index, target_text)
            reference = _display_reference(target_text)
            line = _occurrence_line(text, match.start())
            if resolution.target == source_path:
                key = (relative, reference)
                _merge_reference(
                    wikilinks,
                    key,
                    source=relative,
                    reference=reference,
                    line=line,
                    link_type="wikilink",
                )
            elif source_path in resolution.candidates and resolution.target is None:
                key = (relative, reference, resolution.candidates)
                _merge_reference(
                    ambiguous,
                    key,
                    source=relative,
                    reference=reference,
                    line=line,
                    link_type="wikilink",
                    ambiguous=True,
                    candidates=resolution.candidates,
                )
        for match in MARKDOWN_LINK_RE.finditer(text):
            target_text, resolution = resolve_markdown_reference(
                discovered.root, path, match.group(1), index
            )
            if target_text is None or resolution is None:
                continue
            if resolution.target != source_path:
                continue
            reference = _display_reference(target_text)
            line = _occurrence_line(text, match.start())
            _merge_reference(
                markdown_links,
                (relative, reference),
                source=relative,
                reference=reference,
                line=line,
                link_type="markdown",
            )

    canvas_rows: dict[tuple, dict] = {}
    for path in discovered.canvas_files:
        relative = rel(path, discovered.root)
        text = read_source_text(path, discovered.root, "canvas")
        canvas = parse_canvas(text, relative)
        cursor = 0
        for node in canvas.get("nodes", []):
            file_value = node.get("file")
            if node.get("type") != "file" or not isinstance(file_value, str):
                continue
            mapped = index.by_path.get(note_reference_key(file_value))
            if mapped != source_path and file_value != source_path:
                continue
            found = text.find(file_value, cursor)
            if found < 0:
                found = text.find(file_value)
            line = 1 if found < 0 else text.count("\n", 0, found) + 1
            if found >= 0:
                cursor = found + len(file_value)
            node_id = node.get("id") if isinstance(node.get("id"), str) else ""
            canvas_rows[(relative, file_value, node_id, line)] = {
                "source": relative,
                "reference": file_value,
                "lines": [line],
                "link_type": "canvas",
                "node_id": node_id,
            }

    report["incoming_collected"] = True
    report["incoming"] = {
        "wikilink": _sorted_rows(wikilinks),
        "markdown": _sorted_rows(markdown_links),
        "canvas": _sorted_rows(canvas_rows),
        "ambiguous": _sorted_rows(ambiguous),
    }
    return report


def _merge_reference(bucket: dict[tuple, dict], key: tuple, **fields) -> None:
    line = fields.pop("line")
    existing = bucket.get(key)
    if existing is None:
        bucket[key] = {**fields, "lines": [line]}
        return
    existing["lines"] = sorted({*existing["lines"], line})
