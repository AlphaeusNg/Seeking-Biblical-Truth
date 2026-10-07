#!/usr/bin/env python3
"""Read-only report of stub exact paths and filename near misses.

Prints EXACT and NEAR MISS sections to stdout. Does not rewrite notes or
stub decisions. An exact canonical path is not also listed as a near miss.
A near miss is a case-folded stub equal to a note filename stem.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from .vault_source_discovery import NoteIndex, discover_vault, note_reference_key
else:
    from vault_source_discovery import NoteIndex, discover_vault, note_reference_key


HEADER = ("Kind", "Source", "Stub", "Lines", "Status")
_SEPARATOR = re.compile(r":?-{3,}:?")
EXACT_HEADER = "EXACT"
NEAR_HEADER = "NEAR MISS"


@dataclass(frozen=True)
class StubRow:
    source: str
    stub: str
    status: str = "pending owner"


@dataclass(frozen=True)
class StubMatch:
    stub: str
    source: str
    note: str


def _cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def parse_stub_rows(text: str) -> list[StubRow]:
    """Return source/stub pairs from the decisions table, ignoring prose."""
    rows: list[StubRow] = []
    in_table = False
    for line in text.splitlines():
        cells = _cells(line)
        if not in_table:
            if cells is not None and tuple(cells) == HEADER:
                in_table = True
            continue
        if cells is None:
            break
        if cells and all(_SEPARATOR.fullmatch(cell) for cell in cells):
            continue
        if len(cells) < len(HEADER):
            continue
        rows.append(StubRow(source=cells[1], stub=cells[2], status=cells[4]))
    if not in_table:
        raise ValueError("Missing stub decisions table header")
    return rows


def classify_stubs(
    index: NoteIndex, rows: list[StubRow]
) -> tuple[list[StubMatch], list[StubMatch]]:
    """Split exact canonical paths from case-folded filename near misses."""
    exact: list[StubMatch] = []
    near: list[StubMatch] = []
    for row in rows:
        exact_path = index.by_path.get(note_reference_key(row.stub))
        if exact_path is not None:
            exact.append(StubMatch(row.stub, row.source, exact_path))
            continue
        for note in index.by_title.get(row.stub.casefold(), []):
            near.append(StubMatch(row.stub, row.source, note))
    return exact, near


def format_report(exact: list[StubMatch], near: list[StubMatch]) -> str:
    lines = [EXACT_HEADER]
    lines.extend(f"{item.stub}\t{item.source}\t{item.note}" for item in exact)
    lines.append("")
    lines.append(NEAR_HEADER)
    lines.extend(f"{item.stub}\t{item.source}\t{item.note}" for item in near)
    return "\n".join(lines) + "\n"


def report_stub_near_misses(root: Path, decisions_text: str) -> str:
    discovered = discover_vault(root)
    exact, near = classify_stubs(discovered.index, parse_stub_rows(decisions_text))
    return format_report(exact, near)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Vault root. Defaults to the repository root.",
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        default=None,
        help="Stub decisions table. Defaults to tools/stub-decisions.md under the vault root.",
    )
    parser.add_argument("--pending-only", action="store_true",
                        help="Inspect only rows still awaiting an owner decision. Writes nothing.")
    parser.add_argument("--json", action="store_true", help="Print structured decisions and exact/near matches to stdout.")
    args = parser.parse_args(argv)
    root = args.root if args.root is not None else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        print(f"ERROR: missing vault: {root}", file=sys.stderr)
        return 2
    decisions = (
        args.decisions
        if args.decisions is not None
        else root / "tools" / "stub-decisions.md"
    )
    try:
        decisions_text = decisions.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        print(f"ERROR: unreadable decisions: {decisions}", file=sys.stderr)
        return 2
    try:
        rows = parse_stub_rows(decisions_text)
    except ValueError as error:
        print(f"ERROR: {error}: {decisions}", file=sys.stderr)
        return 2
    if args.pending_only:
        rows = [row for row in rows if row.status.casefold() == "pending owner"]
    discovered = discover_vault(root)
    exact, near = classify_stubs(discovered.index, rows)
    if args.json:
        records = []
        for row in rows:
            records.append({
                "source": row.source, "stub": row.stub, "status": row.status,
                "exact": [match.note for match in exact if match.stub == row.stub and match.source == row.source],
                "near": [match.note for match in near if match.stub == row.stub and match.source == row.source],
            })
        sys.stdout.write(json.dumps({"decisions": records, "count": len(rows)}, ensure_ascii=False, indent=2) + "\n")
    else:
        prefix = f"Pending owner decisions: {len(rows)}\n\n" if args.pending_only else ""
        sys.stdout.write(prefix + format_report(exact, near))
    return 0


if __name__ == "__main__":
    sys.exit(main())
