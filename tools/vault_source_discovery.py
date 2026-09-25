#!/usr/bin/env python3
"""Discover vault Markdown and canvas sources before link resolution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote


EXCLUDED_PARTS = {".git", "__pycache__", "pages", "tools"}
EXCLUDED_ROOT_FILES = {"AGENTS.md", "PROGRESS.md", "README.md"}
EXPORT_EXCLUSIONS_FILE = Path("tools") / "export-exclusions.txt"
_DRAFT_TRUE = re.compile(
    r"""^draft:\s*(?:true|"true"|'true')\s*(?:#.*)?$""",
    re.IGNORECASE,
)


# Export exclusion omits draft notes from the generated dataset only.
# Export exclusion does not make files private in a public Git repository.


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_source_text(path: Path, root: Path, kind: str) -> str:
    """Decode a source exactly as UTF-8 or fail with its vault-relative path."""
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Invalid UTF-8 in {kind}: {rel(path, root)}") from error


def parse_canvas(text: str, relative: str) -> dict:
    """Parse the canvas fields consumed by the exporter or fail predictably."""
    try:
        canvas = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid canvas JSON: {relative}") from error
    if not isinstance(canvas, dict):
        raise ValueError(f"Invalid canvas structure: {relative} (root must be an object)")

    for field_name in ("nodes", "edges"):
        entries = canvas.get(field_name, [])
        if not isinstance(entries, list) or any(
            not isinstance(entry, dict) for entry in entries
        ):
            raise ValueError(
                f"Invalid canvas structure: {relative} ({field_name} must be an array of objects)"
            )
    for node in canvas.get("nodes", []):
        if node.get("type") == "file" and not isinstance(node.get("file"), str):
            raise ValueError(
                f"Invalid canvas structure: {relative} (file nodes require a file path)"
            )
    return canvas


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


def has_draft_frontmatter(text: str) -> bool:
    """True only when the opening YAML block sets draft to true."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return False
        if _DRAFT_TRUE.fullmatch(stripped):
            return True
    return False


def load_exclusion_paths(root: Path) -> set[str]:
    """Return exact vault-relative note paths listed for export exclusion."""
    policy = root / EXPORT_EXCLUSIONS_FILE
    if not policy.is_file():
        return set()
    relative = EXPORT_EXCLUSIONS_FILE.as_posix()
    try:
        resolved = policy.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError(
            f"Export exclusion policy resolves outside vault: {relative}"
        ) from error
    try:
        text = resolved.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Invalid UTF-8 in export exclusion policy: {relative}") from error
    listed: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        listed.add(stripped.replace("\\", "/"))
    return listed


class NoteIndex:
    """Canonical path index used by collision checks and link resolution."""

    def __init__(self) -> None:
        self.by_title: dict[str, list[str]] = {}
        self.by_path: dict[str, str] = {}
        self.excluded_paths: set[str] = set()
        self.excluded_reasons: dict[str, list[str]] = {}


@dataclass
class DiscoveredVault:
    """Sources that passed containment, with draft notes kept out of export."""

    root: Path
    md_files: list[Path]
    canvas_files: list[Path]
    note_texts: dict[str, str]
    index: NoteIndex
    unmatched_policy_paths: list[str] = field(default_factory=list)


def exclusion_reason(index: NoteIndex, relative: str) -> str:
    details = index.excluded_reasons.get(relative) or ["draft"]
    return "excluded from export (" + ", ".join(details) + ")"


def discover_vault(root: Path) -> DiscoveredVault:
    """Find contained sources, reject path collisions, and classify drafts."""
    root = root.resolve()
    md_files = sorted(
        path for path in root.rglob("*.md") if is_content_file(path.relative_to(root))
    )
    canvas_files = sorted(
        path
        for path in root.rglob("*.canvas")
        if is_content_file(path.relative_to(root))
    )
    for path in md_files:
        require_source_within_vault(path, root, "note")
    for path in canvas_files:
        require_source_within_vault(path, root, "canvas")

    index = NoteIndex()
    for path in md_files:
        relative = rel(path, root)
        index.by_title.setdefault(path.stem.casefold(), []).append(relative)
        # Case-folded, percent-decoded paths must name one note on every filesystem.
        key = note_reference_key(relative)
        existing = index.by_path.get(key)
        if existing is not None and existing != relative:
            left, right = sorted((existing, relative), key=str.casefold)
            raise ValueError(f"Canonical note path collision: {left} and {right}")
        index.by_path[key] = relative

    listed = load_exclusion_paths(root)
    note_paths = set(index.by_path.values())
    note_texts: dict[str, str] = {}
    for path in md_files:
        relative = rel(path, root)
        text = read_source_text(path, root, "note")
        reasons: list[str] = []
        if relative in listed:
            reasons.append("policy path")
        if has_draft_frontmatter(text):
            reasons.append("frontmatter")
        if reasons:
            index.excluded_paths.add(relative)
            index.excluded_reasons[relative] = reasons
            continue
        note_texts[relative] = text

    unmatched = sorted(
        (path for path in listed if path not in note_paths),
        key=str.casefold,
    )
    return DiscoveredVault(
        root=root,
        md_files=md_files,
        canvas_files=canvas_files,
        note_texts=note_texts,
        index=index,
        unmatched_policy_paths=unmatched,
    )
