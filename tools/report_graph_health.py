#!/usr/bin/env python3
"""Report published note connectivity without writing notes or datasets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__:
    from .vault_dataset_assembly import build_dataset
else:
    from vault_dataset_assembly import build_dataset


SCOPE = (
    "Published notes only; export exclusions omitted. Connectivity uses resolved "
    "wikilink/Markdown note links; canvas mentions are separate. "
    "Isolation does not imply a note needs changes."
)


def ordered(paths) -> list[str]:
    return sorted(paths, key=lambda path: (path.casefold(), path))


def graph_health(data: dict) -> dict:
    """Describe distinct note neighbors, ignoring structural viewer edges."""
    paths = {node["id"] for node in data["nodes"] if node["type"] == "note"}
    canvases = {node["id"] for node in data["nodes"] if node["type"] == "canvas"}
    incoming = {path: set() for path in paths}
    outgoing = {path: set() for path in paths}
    mentions = {path: set() for path in paths}
    for link in data["links"]:
        source, target = link["source"], link["target"]
        if target not in paths:
            continue
        if link["type"] == "canvas" and source in canvases:
            mentions[target].add(source)
        elif link["type"] in {"wikilink", "markdown"} and source in paths and source != target:
            incoming[target].add(source)
            outgoing[source].add(target)

    components = []
    remaining = set(paths)
    for seed in ordered(paths):
        if seed not in remaining:
            continue
        pending = [seed]
        remaining.remove(seed)
        members = set()
        while pending:
            path = pending.pop()
            members.add(path)
            neighbors = (incoming[path] | outgoing[path]) & remaining
            remaining.difference_update(neighbors)
            pending.extend(neighbors)
        components.append(ordered(members))

    isolated = ordered(path for path in paths if not incoming[path] and not outgoing[path])
    return {
        "schemaVersion": 1,
        "scope": SCOPE,
        "counts": {
            "notes": len(paths),
            "noteLinks": sum(len(neighbors) for neighbors in outgoing.values()),
            "isolated": len(isolated),
            "components": len(components),
        },
        "isolated": isolated,
        "withoutIncoming": ordered(path for path in paths if not incoming[path]),
        "withoutOutgoing": ordered(path for path in paths if not outgoing[path]),
        "components": components,
        "notes": [
            {"path": path, "incoming": ordered(incoming[path]),
             "outgoing": ordered(outgoing[path]), "canvasMentions": ordered(mentions[path])}
            for path in ordered(paths)
        ],
    }


def format_report(report: dict) -> str:
    counts = report["counts"]
    lines = ["Vault graph health", report["scope"],
             f"{counts['notes']} notes, {counts['noteLinks']} directed neighbor pairs, "
             f"{counts['components']} components."]
    for label, key in (("Isolated notes", "isolated"),
                       ("Notes without incoming links", "withoutIncoming"),
                       ("Notes without outgoing links", "withoutOutgoing")):
        lines.extend(["", f"{label} ({len(report[key])}):"])
        lines.extend(f"- {path}" for path in report[key])
        if not report[key]:
            lines.append("- none")
    lines.extend(["", f"Connected components ({len(report['components'])}):"])
    for number, members in enumerate(report["components"], 1):
        lines.append(f"Component {number} ({len(members)} notes):")
        lines.extend(f"- {path}" for path in members)
    lines.extend(["", "Canvas mentions (separate from note connectivity):"])
    mentioned = [note for note in report["notes"] if note["canvasMentions"]]
    lines.extend(f"- {note['path']}: {', '.join(note['canvasMentions'])}" for note in mentioned)
    if not mentioned:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true", help="Print versioned JSON to stdout.")
    args = parser.parse_args(argv)
    try:
        if not args.root.is_dir():
            raise ValueError(f"Missing vault: {args.root}")
        report = graph_health(build_dataset(args.root))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n"
                     if args.json else format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
