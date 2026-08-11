from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.sync_public_viewer import SyncError, sync_public_viewer


SYNC_SCRIPT = Path(__file__).with_name("sync_public_viewer.py")


class PublicViewerSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        projects = Path(self.temp_dir.name)
        self.vault_root = projects / "Seeking-Biblical-Truth"
        self.vault_root.mkdir()
        (self.vault_root / "Index.md").write_text("# Index\n", encoding="utf-8")
        self.public_output = (
            projects
            / "alphaeusng.github.io"
            / "pages"
            / "seeking-biblical-truth"
            / "vault-data.json"
        )
        self.public_output.parent.mkdir(parents=True)
        (self.public_output.parent / "index.html").write_text(
            "<!doctype html>\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_sync_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SYNC_SCRIPT),
                "--vault-root",
                str(self.vault_root),
                "--public-output",
                str(self.public_output),
                *arguments,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def git(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    def initialize_repositories(self) -> tuple[Path, Path]:
        sync_public_viewer(self.vault_root, self.public_output)
        public_root = self.public_output.parents[2]
        for root in (self.vault_root, public_root):
            self.git(root, "init", "--quiet", "--initial-branch=main")
            self.git(root, "config", "user.name", "Sync Test")
            self.git(root, "config", "user.email", "sync-test@example.com")
            self.git(root, "add", ".")
            self.git(root, "commit", "--quiet", "-m", "Baseline")
        return self.vault_root, public_root

    def test_sync_writes_identical_source_and_public_payloads_idempotently(self) -> None:
        changed = sync_public_viewer(self.vault_root, self.public_output)
        source_output = self.vault_root / "pages" / "vault-data.json"

        self.assertEqual(changed, ["source export", "public viewer copy"])
        self.assertEqual(source_output.read_bytes(), self.public_output.read_bytes())
        self.assertEqual(sync_public_viewer(self.vault_root, self.public_output), [])
        self.assertEqual(
            sync_public_viewer(self.vault_root, self.public_output, check=True), []
        )

    def test_check_distinguishes_stale_source_export(self) -> None:
        sync_public_viewer(self.vault_root, self.public_output)
        source_output = self.vault_root / "pages" / "vault-data.json"
        source_output.write_text("{}", encoding="utf-8")

        with self.assertRaisesRegex(SyncError, "source export is stale") as raised:
            sync_public_viewer(self.vault_root, self.public_output, check=True)

        self.assertNotIn("public viewer copy", str(raised.exception))

    def test_check_distinguishes_stale_public_copy(self) -> None:
        sync_public_viewer(self.vault_root, self.public_output)
        self.public_output.write_text("{}", encoding="utf-8")

        with self.assertRaisesRegex(SyncError, "public viewer copy is stale") as raised:
            sync_public_viewer(self.vault_root, self.public_output, check=True)

        self.assertNotIn("source export", str(raised.exception))

    def test_check_cli_exits_nonzero_and_names_invalid_utf8_public_copy(self) -> None:
        sync_public_viewer(self.vault_root, self.public_output)
        self.public_output.write_bytes(b"\xff")

        result = subprocess.run(
            [
                sys.executable,
                str(SYNC_SCRIPT),
                "--check",
                "--vault-root",
                str(self.vault_root),
                "--public-output",
                str(self.public_output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("public viewer copy is stale", result.stderr)
        self.assertEqual(self.public_output.read_bytes(), b"\xff", "check mode must not write")

    def test_missing_public_viewer_refuses_before_writing_source(self) -> None:
        missing_output = self.public_output.parent.parent / "missing" / "vault-data.json"

        with self.assertRaisesRegex(SyncError, "viewer directory is missing"):
            sync_public_viewer(self.vault_root, missing_output)

        self.assertFalse((self.vault_root / "pages" / "vault-data.json").exists())
        self.assertFalse(missing_output.exists())

    def test_missing_vault_refuses_without_replacing_public_copy(self) -> None:
        self.public_output.write_text("preserve me", encoding="utf-8")
        missing_vault = self.vault_root.parent / "missing-vault"

        with self.assertRaisesRegex(SyncError, "vault root is missing"):
            sync_public_viewer(missing_vault, self.public_output)

        self.assertEqual(self.public_output.read_text(encoding="utf-8"), "preserve me")

    def test_empty_vault_refuses_without_replacing_public_copy(self) -> None:
        self.public_output.write_text("preserve me", encoding="utf-8")
        empty_vault = self.vault_root.parent / "empty-vault"
        empty_vault.mkdir()

        with self.assertRaisesRegex(SyncError, "no exportable notes or canvases"):
            sync_public_viewer(empty_vault, self.public_output)

        self.assertEqual(self.public_output.read_text(encoding="utf-8"), "preserve me")

    def test_git_status_reports_both_repositories_without_writing(self) -> None:
        source_root, public_root = self.initialize_repositories()
        (self.vault_root / "Index.md").write_text("# Changed\n", encoding="utf-8")
        sync_public_viewer(self.vault_root, self.public_output)
        source_before = self.git(source_root, "status", "--short").stdout
        public_before = self.git(public_root, "status", "--short").stdout

        result = self.run_sync_cli("--git-status")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Source repository ({source_root}):", result.stdout)
        self.assertIn(" M Index.md", result.stdout)
        self.assertIn(" M pages/vault-data.json", result.stdout)
        self.assertIn(f"Public repository ({public_root}):", result.stdout)
        self.assertIn(" M pages/seeking-biblical-truth/vault-data.json", result.stdout)
        self.assertEqual(self.git(source_root, "status", "--short").stdout, source_before)
        self.assertEqual(self.git(public_root, "status", "--short").stdout, public_before)

    def test_commit_staged_refuses_all_commits_when_work_is_unstaged(self) -> None:
        source_root, public_root = self.initialize_repositories()
        (self.vault_root / "Index.md").write_text("# Changed\n", encoding="utf-8")
        sync_public_viewer(self.vault_root, self.public_output)
        self.git(source_root, "add", "Index.md", "pages/vault-data.json")
        self.git(public_root, "add", "pages/seeking-biblical-truth/vault-data.json")
        (public_root / "forgotten.txt").write_text("not staged\n", encoding="utf-8")

        result = self.run_sync_cli("--commit-staged")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Public repository has unstaged or untracked changes", result.stderr)
        self.assertEqual(self.git(source_root, "rev-list", "--count", "HEAD").stdout, "1\n")
        self.assertEqual(self.git(public_root, "rev-list", "--count", "HEAD").stdout, "1\n")

    def test_commit_staged_requires_the_repository_dataset_in_the_index(self) -> None:
        source_root, public_root = self.initialize_repositories()
        (source_root / "README.md").write_text("staged but unrelated\n", encoding="utf-8")
        self.git(source_root, "add", "README.md")

        result = self.run_sync_cli("--commit-staged")

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Source repository has staged changes but not its dataset",
            result.stderr,
        )
        self.assertEqual(self.git(source_root, "rev-list", "--count", "HEAD").stdout, "1\n")
        self.assertEqual(self.git(public_root, "rev-list", "--count", "HEAD").stdout, "1\n")

    def test_commit_staged_creates_separate_commits_without_pushing(self) -> None:
        source_root, public_root = self.initialize_repositories()
        (self.vault_root / "Index.md").write_text("# Changed\n", encoding="utf-8")
        sync_public_viewer(self.vault_root, self.public_output)
        self.git(source_root, "add", "Index.md", "pages/vault-data.json")
        self.git(public_root, "add", "pages/seeking-biblical-truth/vault-data.json")

        result = self.run_sync_cli(
            "--commit-staged", "--commit-message", "Sync fixture data"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Committed Source repository", result.stdout)
        self.assertIn("Committed Public repository", result.stdout)
        self.assertIn("No pushes were performed", result.stdout)
        self.assertEqual(
            self.git(source_root, "log", "-1", "--format=%s").stdout,
            "Sync fixture data\n",
        )
        self.assertEqual(
            self.git(public_root, "log", "-1", "--format=%s").stdout,
            "Sync fixture data\n",
        )
        self.assertEqual(self.git(source_root, "status", "--short").stdout, "")
        self.assertEqual(self.git(public_root, "status", "--short").stdout, "")


if __name__ == "__main__":
    unittest.main()
