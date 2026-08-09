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


if __name__ == "__main__":
    unittest.main()
