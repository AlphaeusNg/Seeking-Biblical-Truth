#!/usr/bin/env python3
"""Regenerate and synchronize the tracked public vault-viewer datasets."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from .generate_vault_data import build_dataset, format_dataset_summary, serialize_dataset
else:
    from generate_vault_data import build_dataset, format_dataset_summary, serialize_dataset


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


@dataclass(frozen=True)
class RepositoryStatus:
    """Git state relevant to a synchronized dataset repository."""

    label: str
    root: Path
    target: str
    short_status: str
    staged: tuple[str, ...]
    unstaged: tuple[str, ...]
    untracked: tuple[str, ...]


@dataclass(frozen=True)
class FileSnapshot:
    """Original generated-file state used to roll back a partial pair write."""

    existed: bool
    content: bytes
    mode: int


def _matches(path: Path, payload: str) -> bool:
    try:
        return path.is_file() and path.read_text(encoding="utf-8") == payload
    except (OSError, UnicodeError):
        return False


def _replace_bytes(path: Path, payload: bytes, mode: int) -> None:
    """Atomically replace one generated file with exact bytes and permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
        temp_path.chmod(mode)
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _write_if_changed(path: Path, payload: str) -> bool:
    if _matches(path, payload):
        return False
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    _replace_bytes(path, payload.encode("utf-8"), mode)
    return True


def _snapshot_file(path: Path) -> FileSnapshot:
    """Capture bytes and permissions before any file in a pair is changed."""
    try:
        return FileSnapshot(
            existed=True,
            content=path.read_bytes(),
            mode=stat.S_IMODE(path.stat().st_mode),
        )
    except FileNotFoundError:
        return FileSnapshot(existed=False, content=b"", mode=0o644)


def _restore_file(path: Path, snapshot: FileSnapshot) -> None:
    if snapshot.existed:
        _replace_bytes(path, snapshot.content, snapshot.mode)
    else:
        path.unlink(missing_ok=True)


def _validate_public_target(public_output: Path) -> None:
    viewer_dir = public_output.parent
    if not viewer_dir.is_dir():
        raise SyncError(f"public viewer directory is missing: {viewer_dir}")
    if not (viewer_dir / "index.html").is_file():
        raise SyncError(f"public viewer entry point is missing: {viewer_dir / 'index.html'}")


def _run_git(directory: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise SyncError(f"could not run Git: {error}") from error
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise SyncError(f"Git failed in {directory}: {detail}")
    return result.stdout


def _nul_paths(output: str) -> tuple[str, ...]:
    return tuple(path for path in output.split("\0") if path)


def _repository_status(label: str, target: Path) -> RepositoryStatus:
    root = Path(_run_git(target.parent, "rev-parse", "--show-toplevel").strip()).resolve()
    try:
        relative_target = target.resolve().relative_to(root).as_posix()
    except ValueError as error:
        raise SyncError(f"{label} target is outside its Git repository: {target}") from error
    return RepositoryStatus(
        label=label,
        root=root,
        target=relative_target,
        short_status=_run_git(root, "status", "--short", "--untracked-files=all").rstrip(),
        staged=_nul_paths(_run_git(root, "diff", "--cached", "--name-only", "-z")),
        unstaged=_nul_paths(_run_git(root, "diff", "--name-only", "-z")),
        untracked=_nul_paths(
            _run_git(root, "ls-files", "--others", "--exclude-standard", "-z")
        ),
    )


def repository_statuses(
    vault_root: Path,
    public_output: Path,
) -> tuple[RepositoryStatus, RepositoryStatus]:
    """Return complete read-only Git status for both dataset repositories."""
    vault_root = vault_root.resolve()
    public_output = public_output.resolve()
    statuses = (
        _repository_status("Source repository", vault_root / "pages" / "vault-data.json"),
        _repository_status("Public repository", public_output),
    )
    if statuses[0].root == statuses[1].root:
        raise SyncError("source export and public viewer copy must use separate Git repositories")
    return statuses


def format_repository_statuses(statuses: tuple[RepositoryStatus, ...]) -> str:
    sections = []
    for status in statuses:
        body = status.short_status or "clean"
        sections.append(
            f"{status.label} ({status.root}):\n"
            + "\n".join(f"  {line}" for line in body.splitlines())
        )
    return "\n".join(sections)


def commit_staged_repositories(
    vault_root: Path,
    public_output: Path,
    *,
    message: str = "Sync public vault data",
) -> list[tuple[str, str]]:
    """Commit explicitly staged sync changes in each repository, without pushing."""
    if not message.strip():
        raise SyncError("commit message must not be empty")
    statuses = repository_statuses(vault_root, public_output)
    issues = []
    for status in statuses:
        forgotten = status.unstaged + status.untracked
        if forgotten:
            issues.append(
                f"{status.label} has unstaged or untracked changes: "
                + ", ".join(forgotten)
            )
        if status.staged and status.target not in status.staged:
            issues.append(
                f"{status.label} has staged changes but not its dataset: {status.target}"
            )
    if issues:
        raise SyncError("; ".join(issues))

    pending = [status for status in statuses if status.staged]
    for status in pending:
        _run_git(status.root, "var", "GIT_AUTHOR_IDENT")
        _run_git(status.root, "var", "GIT_COMMITTER_IDENT")

    committed = []
    for status in pending:
        try:
            _run_git(status.root, "commit", "-m", message.strip())
            revision = _run_git(status.root, "rev-parse", "--short", "HEAD").strip()
        except SyncError as error:
            completed = ", ".join(label for label, _ in committed)
            prefix = f"{completed} committed; " if completed else ""
            raise SyncError(
                f"{prefix}{status.label} commit failed. No pushes were performed. {error}"
            ) from error
        committed.append((status.label, revision))
    return committed


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

    targets = (
        ("source export", source_output),
        ("public viewer copy", public_output),
    )
    snapshots = {path: _snapshot_file(path) for _, path in targets}
    changed = []
    written = []
    try:
        for label, path in targets:
            if _write_if_changed(path, payload):
                changed.append(label)
                written.append(path)
    except BaseException as error:
        rollback_failures = []
        for path in reversed(written):
            try:
                _restore_file(path, snapshots[path])
            except BaseException as rollback_error:
                rollback_failures.append(f"{path}: {rollback_error}")
        if rollback_failures:
            raise SyncError(
                "dataset sync failed and rollback was incomplete: "
                + "; ".join(rollback_failures)
            ) from error
        raise
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--check",
        action="store_true",
        help="Verify both copies without writing them.",
    )
    action.add_argument(
        "--git-status",
        action="store_true",
        help="Verify both copies, then show read-only Git status for both repositories.",
    )
    action.add_argument(
        "--commit-staged",
        action="store_true",
        help="Verify both copies, then separately commit already-staged changes; never push.",
    )
    parser.add_argument(
        "--commit-message",
        help="Commit message for --commit-staged (default: Sync public vault data).",
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
    if args.commit_message is not None and not args.commit_staged:
        parser.error("--commit-message requires --commit-staged")

    try:
        changed = sync_public_viewer(
            args.vault_root,
            args.public_output,
            check=args.check or args.git_status or args.commit_staged,
        )
        statuses = None
        committed = None
        if args.git_status:
            statuses = repository_statuses(args.vault_root, args.public_output)
        elif args.commit_staged:
            committed = commit_staged_repositories(
                args.vault_root,
                args.public_output,
                message=args.commit_message or "Sync public vault data",
            )
    except SyncError as error:
        parser.exit(1, f"ERROR: {error}\n")

    if args.check:
        print("Source export and public viewer copy are current and byte-identical.")
        source_output = args.vault_root.resolve() / "pages" / "vault-data.json"
        try:
            print(format_dataset_summary(json.loads(source_output.read_text(encoding="utf-8"))))
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    elif args.git_status:
        print("Source export and public viewer copy are current and byte-identical.")
        source_output = args.vault_root.resolve() / "pages" / "vault-data.json"
        try:
            print(format_dataset_summary(json.loads(source_output.read_text(encoding="utf-8"))))
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
        print(format_repository_statuses(statuses))
    elif args.commit_staged:
        if committed:
            for label, revision in committed:
                print(f"Committed {label} at {revision}.")
        else:
            print("No staged dataset changes to commit in either repository.")
        print("No pushes were performed; push each repository separately.")
    elif changed:
        print("Synchronized " + " and ".join(changed) + ".")
    else:
        print("Source export and public viewer copy were already synchronized.")


if __name__ == "__main__":
    main()
