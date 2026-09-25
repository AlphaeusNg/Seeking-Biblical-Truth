#!/usr/bin/env python3
"""Generate the public graph dataset from this Obsidian vault.

Source discovery, link resolution, dataset assembly, and diagnostic formatting
are separate stages. Read-only previews do not write either dataset copy.
Export exclusion does not make files private in a public Git repository.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .vault_dataset_assembly import build_dataset, serialize_dataset
    from .vault_diagnostic_format import (
        PREVIEW_WRITES_NOTHING,
        format_dataset_summary,
        format_exclusion_preview,
        format_export_changes,
        format_link_diagnostics,
        format_rename_preview,
        format_unresolved_link_checklist,
        unresolved_reference_kind,
    )
    from .vault_link_resolution import inspect_rename
    from .vault_source_discovery import discover_vault, is_content_file
else:
    from vault_dataset_assembly import build_dataset, serialize_dataset
    from vault_diagnostic_format import (
        PREVIEW_WRITES_NOTHING,
        format_dataset_summary,
        format_exclusion_preview,
        format_export_changes,
        format_link_diagnostics,
        format_rename_preview,
        format_unresolved_link_checklist,
        unresolved_reference_kind,
    )
    from vault_link_resolution import inspect_rename
    from vault_source_discovery import discover_vault, is_content_file


def _exclusion_preview(root: Path) -> str:
    discovered = discover_vault(root)
    excluded = [
        (path, ", ".join(discovered.index.excluded_reasons[path]))
        for path in sorted(discovered.index.excluded_paths, key=str.casefold)
    ]
    return format_exclusion_preview(excluded, discovered.unmatched_policy_paths)


def _load_committed_dataset(path: Path) -> dict:
    try:
        current = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"committed dataset missing or unreadable: {path}") from error
    try:
        data = json.loads(current)
    except json.JSONDecodeError as error:
        raise ValueError(f"committed dataset is not JSON: {path}") from error
    if not isinstance(data, dict):
        raise ValueError(f"committed dataset is not a JSON object: {path}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Vault root. Defaults to current directory.")
    parser.add_argument("--output", type=Path, default=Path("pages/vault-data.json"), help="Output JSON path.")
    parser.add_argument(
        "--checklist",
        type=Path,
        default=Path("tools/unresolved-links.md"),
        help="Unresolved-link checklist path.",
    )
    report = parser.add_mutually_exclusive_group()
    report.add_argument(
        "--report-links",
        action="store_true",
        help="Print unresolved/ambiguous links without writing the dataset.",
    )
    report.add_argument(
        "--write-checklist",
        action="store_true",
        help="Write the grouped unresolved-link checklist without writing the dataset.",
    )
    report.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed dataset and unresolved-link checklist. Does not write.",
    )
    report.add_argument(
        "--preview-rename",
        nargs=2,
        metavar=("SOURCE", "DESTINATION"),
        help="List incoming links for a proposed note move. Does not modify files.",
    )
    report.add_argument(
        "--preview-exclusions",
        action="store_true",
        help=(
            "List draft notes excluded from export without writing datasets. "
            "Export exclusion does not make files private in a public Git repository."
        ),
    )
    report.add_argument(
        "--preview-export",
        action="store_true",
        help=(
            "Print a semantic before/after export report. "
            "Writes neither dataset copy."
        ),
    )
    args = parser.parse_args()

    if args.preview_rename:
        source, destination = args.preview_rename
        preview = inspect_rename(args.root, source, destination)
        print(format_rename_preview(preview))
        if preview["exit_code"]:
            raise SystemExit(preview["exit_code"])
        return
    if args.preview_exclusions:
        print(_exclusion_preview(args.root))
        return
    if args.preview_export:
        try:
            before = _load_committed_dataset(args.output)
        except ValueError as error:
            print("Export preview")
            print(PREVIEW_WRITES_NOTHING)
            print(error)
            raise SystemExit(1) from error
        after = build_dataset(args.root.resolve())
        print(format_export_changes(before, after))
        return

    data = build_dataset(args.root.resolve())
    if args.report_links:
        print(format_dataset_summary(data))
        print()
        print(format_link_diagnostics(data))
        return
    if args.write_checklist:
        args.checklist.parent.mkdir(parents=True, exist_ok=True)
        args.checklist.write_text(
            format_unresolved_link_checklist(data), encoding="utf-8"
        )
        print(
            f"Wrote {data['counts']['unresolvedLinks']} unresolved links "
            f"to {args.checklist}"
        )
        return
    if args.check:
        print(format_dataset_summary(data))
        print()
        print(format_link_diagnostics(data))
        payload = serialize_dataset(data)
        expected_checklist = format_unresolved_link_checklist(data)
        issues = []
        try:
            current = args.output.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            issues.append(f"committed dataset missing or unreadable: {args.output}")
        else:
            if current != payload:
                issues.append(f"committed dataset is stale: {args.output}")
        try:
            current_checklist = args.checklist.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            issues.append(
                "committed unresolved-link checklist missing or unreadable: "
                f"{args.checklist}"
            )
        else:
            if current_checklist != expected_checklist:
                issues.append(
                    "committed unresolved-link checklist is stale: "
                    f"{args.checklist}"
                )
        if issues:
            parser.exit(1, "ERROR: " + "; ".join(issues) + "\n")
        print("Committed dataset matches vault sources.")
        print("Committed unresolved-link checklist matches vault sources.")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialize_dataset(data), encoding="utf-8")
    print(f"Wrote {data['counts']} to {args.output}")


if __name__ == "__main__":
    main()
