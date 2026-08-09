#!/usr/bin/env python3
"""Regenerate and synchronize the tracked public vault-viewer datasets."""

from __future__ import annotations

import argparse
import os
import stat
import tempfile
from pathlib import Path

if __package__:
    from .generate_vault_data import build_dataset, serialize_dataset
else:
    from generate_vault_data import build_dataset, serialize_dataset


VAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_OUTPUT = (
    VAULT_ROOT.parent
    / "alphaeusng.github.io"
    / "pages"
    / "seeking-biblical-truth"
    / "vault-data.json"
)


class SyncError(RuntimeError):
    """Raised when public viewer synchronization cannot proceed safely."""


def _matches(path: Path, payload: str) -> bool:
    try:
        return path.is_file() and path.read_text(encoding="utf-8") == payload
    except (OSError, UnicodeError):
        return False


def _write_if_changed(path: Path, payload: str) -> bool:
    if _matches(path, payload):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(payload)
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
        temp_path.chmod(mode)
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return True


def _validate_public_target(public_output: Path) -> None:
    viewer_dir = public_output.parent
    if not viewer_dir.is_dir():
        raise SyncError(f"public viewer directory is missing: {viewer_dir}")
    if not (viewer_dir / "index.html").is_file():
        raise SyncError(f"public viewer entry point is missing: {viewer_dir / 'index.html'}")


def sync_public_viewer(
    vault_root: Path,
    public_output: Path,
    *,
    check: bool = False,
) -> list[str]:
    """Write or verify both generated dataset copies.

    Returns labels for files changed in write mode. Check mode never writes and
    raises ``SyncError`` with a precise list of stale or missing copies.
    """
    vault_root = vault_root.resolve()
    public_output = public_output.resolve()
    if not vault_root.is_dir():
        raise SyncError(f"vault root is missing: {vault_root}")
    _validate_public_target(public_output)

    source_output = vault_root / "pages" / "vault-data.json"
    if source_output.resolve() == public_output:
        raise SyncError("source export and public viewer copy must be different files")
    data = build_dataset(vault_root)
    if not data["counts"]["notes"] and not data["counts"]["canvas"]:
        raise SyncError(f"vault has no exportable notes or canvases: {vault_root}")
    payload = serialize_dataset(data)

    if check:
        issues = []
        for label, path in (
            ("source export", source_output),
            ("public viewer copy", public_output),
        ):
            if not path.is_file():
                issues.append(f"{label} is missing: {path}")
            elif not _matches(path, payload):
                issues.append(f"{label} is stale: {path}")
        if issues:
            raise SyncError("; ".join(issues))
        return []

    changed = []
    for label, path in (
        ("source export", source_output),
        ("public viewer copy", public_output),
    ):
        if _write_if_changed(path, payload):
            changed.append(label)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify both copies without writing them.",
    )
    parser.add_argument(
        "--vault-root",
        type=Path,
        default=VAULT_ROOT,
        help="Vault root. Defaults to this repository.",
    )
    parser.add_argument(
        "--public-output",
        type=Path,
        default=DEFAULT_PUBLIC_OUTPUT,
        help="Portfolio viewer data path. Defaults to the canonical sibling checkout.",
    )
    args = parser.parse_args()

    try:
        changed = sync_public_viewer(
            args.vault_root,
            args.public_output,
            check=args.check,
        )
    except SyncError as error:
        parser.exit(1, f"ERROR: {error}\n")

    if args.check:
        print("Source export and public viewer copy are current and byte-identical.")
    elif changed:
        print("Synchronized " + " and ".join(changed) + ".")
    else:
        print("Source export and public viewer copy were already synchronized.")


if __name__ == "__main__":
    main()
