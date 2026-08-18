from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.generate_vault_data import (
    build_dataset,
    format_dataset_summary,
    format_link_diagnostics,
    is_content_file,
    serialize_dataset,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "pages" / "vault-data.json"
GENERATOR = ROOT / "tools" / "generate_vault_data.py"


class VaultDatasetTests(unittest.TestCase):
    def test_excludes_hidden_configuration_markdown_from_discovery(self) -> None:
        self.assertFalse(is_content_file(Path(".obsidian") / "workspace.md"))
        self.assertFalse(is_content_file(Path(".github") / "ISSUE_TEMPLATE.md"))
        self.assertFalse(is_content_file(Path(".hidden.md")))
        self.assertTrue(is_content_file(Path("Word of God") / "Grace.md"))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            public = root / "Word of God" / "Grace.md"
            public.parent.mkdir()
            public.write_text("# Grace\n", encoding="utf-8")
            hidden = root / ".obsidian" / "Note.md"
            hidden.parent.mkdir()
            hidden.write_text("# Editor only\n", encoding="utf-8")

            dataset = build_dataset(root)
            paths = {note["path"] for note in dataset["nodes"] if note.get("path")}
            self.assertEqual(paths, {"Word of God/Grace.md"})

    def test_formats_link_diagnostics_by_source_with_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for folder in ("A", "B"):
                note = root / folder / "Grace.md"
                note.parent.mkdir()
                note.write_text(f"# {folder} Grace\n", encoding="utf-8")
            (root / "Index.md").write_text(
                "[[Missing Note]]\n[[Grace]]\n", encoding="utf-8"
            )

            report = format_link_diagnostics(build_dataset(root))

            self.assertEqual(
                report,
                "Link diagnostics: 1 unresolved, 1 ambiguous\n"
                "\n"
                "Index.md\n"
                "  - unresolved wikilink (line 1): Missing Note\n"
                "  - ambiguous wikilink (line 2): Grace\n"
                "    candidates: A/Grace.md, B/Grace.md",
            )

    def test_dataset_summary_names_counts_without_rewriting_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Index.md").write_text("# No links\n", encoding="utf-8")
            summary = format_dataset_summary(build_dataset(root))
            self.assertIn("Vault snapshot: 1 notes, 0 canvas, 1 links, 1 folders.", summary)
            self.assertIn("Link health: 0 unresolved, 0 ambiguous.", summary)

    def test_formats_an_explicit_empty_link_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Index.md").write_text("# No links\n", encoding="utf-8")

            self.assertEqual(
                format_link_diagnostics(build_dataset(root)),
                "Link diagnostics: 0 unresolved, 0 ambiguous\n\n"
                "No unresolved or ambiguous note links.",
            )

    def test_link_report_cli_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Index.md").write_text("[[Missing]]\n", encoding="utf-8")
            output = root / "generated.json"
            output.write_text("preserve me", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--report-links",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Vault snapshot:", result.stdout)
            self.assertIn("Link health:", result.stdout)
            self.assertIn("Link diagnostics: 1 unresolved, 0 ambiguous", result.stdout)
            self.assertIn("  - unresolved wikilink (line 1): Missing", result.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")

    def test_check_cli_is_read_only_and_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Index.md").write_text("# No links\n", encoding="utf-8")
            output = root / "pages" / "vault-data.json"
            output.parent.mkdir()
            fresh = serialize_dataset(build_dataset(root))
            output.write_text(fresh, encoding="utf-8")
            marker = "preserve me"

            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Vault snapshot:", result.stdout)
            self.assertIn("Committed dataset matches vault sources.", result.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), fresh)

            output.write_text(marker, encoding="utf-8")
            stale = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(stale.returncode, 1)
            self.assertIn("stale", stale.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), marker)

    def test_reports_deduplicated_missing_and_ambiguous_wikilinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for folder in ("A", "B"):
                note = root / folder / "Grace.md"
                note.parent.mkdir()
                note.write_text(f"# {folder} Grace\n", encoding="utf-8")
            (root / "Index.md").write_text(
                "[[Missing Note]]\n"
                "[[Missing%20Note|same missing note]]\n"
                "[[Grace]]\n",
                encoding="utf-8",
            )

            data = build_dataset(root)

            self.assertEqual(data["counts"]["unresolvedLinks"], 1)
            self.assertEqual(data["counts"]["ambiguousLinks"], 1)
            self.assertEqual(
                data["linkDiagnostics"],
                {
                    "unresolved": [
                        {
                            "source": "Index.md",
                            "reference": "Missing Note",
                            "type": "wikilink",
                            "lines": [1, 2],
                        }
                    ],
                    "ambiguous": [
                        {
                            "source": "Index.md",
                            "reference": "Grace",
                            "type": "wikilink",
                            "lines": [3],
                            "candidates": ["A/Grace.md", "B/Grace.md"],
                        }
                    ],
                },
            )

    def test_resolves_vault_root_wikilink_paths_with_optional_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            topic = root / "Word of God" / "Grace.md"
            topic.parent.mkdir()
            topic.write_text("# Grace\n", encoding="utf-8")
            (root / "Index.md").write_text(
                "[[Word of God/Grace]]\n"
                "[[Word of God/Grace.md|Grace again]]\n"
                "[[Word%20of%20God/Grace]]\n"
                "[[./Word of God/Grace]]\n",
                encoding="utf-8",
            )

            links = build_dataset(root)["links"]
            wikilinks = [link for link in links if link["type"] == "wikilink"]

            self.assertEqual(
                wikilinks,
                [
                    {
                        "source": "Index.md",
                        "target": "Word of God/Grace.md",
                        "type": "wikilink",
                    }
                ],
            )

    def test_ambiguous_bare_title_does_not_create_the_wrong_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for folder in ("A", "B"):
                note = root / folder / "Grace.md"
                note.parent.mkdir()
                note.write_text(f"# {folder} Grace\n", encoding="utf-8")
            (root / "Index.md").write_text(
                "[[Grace]]\n[[B/Grace]]\n", encoding="utf-8"
            )

            links = build_dataset(root)["links"]
            wikilinks = [link for link in links if link["type"] == "wikilink"]

            self.assertEqual(
                wikilinks,
                [
                    {
                        "source": "Index.md",
                        "target": "B/Grace.md",
                        "type": "wikilink",
                    }
                ],
            )

    def test_resolves_relative_and_vault_root_markdown_note_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            word = root / "Word of God"
            topics = root / "Topics"
            word.mkdir()
            topics.mkdir()
            for name in ("Relative", "Root Target"):
                (word / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
            (topics / "Index.md").write_text(
                "[Relative](../Word%20of%20God/Relative.md#Hope)\n"
                "[Root](/Word%20of%20God/Root%20Target.md)\n"
                "[Case duplicate](/word%20OF%20god/root%20target.MD \"Read\")\n"
                "[External](https://example.test/remote.md)\n",
                encoding="utf-8",
            )

            markdown_links = [
                link
                for link in build_dataset(root)["links"]
                if link["type"] == "markdown"
            ]

            self.assertEqual(
                markdown_links,
                [
                    {
                        "source": "Topics/Index.md",
                        "target": "Word of God/Relative.md",
                        "type": "markdown",
                    },
                    {
                        "source": "Topics/Index.md",
                        "target": "Word of God/Root Target.md",
                        "type": "markdown",
                    },
                ],
            )

    def test_reports_missing_markdown_notes_but_ignores_external_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Index.md").write_text(
                "[Missing](Missing%20Note.md#Section)\n"
                "[Same missing](./Missing Note.md)\n"
                "[Outside](../../Outside.md)\n"
                "[External](https://example.test/remote.md)\n",
                encoding="utf-8",
            )

            data = build_dataset(root)

            self.assertEqual(data["counts"]["unresolvedLinks"], 2)
            self.assertEqual(
                data["linkDiagnostics"]["unresolved"],
                [
                    {
                        "source": "Index.md",
                        "reference": "Missing Note.md",
                        "type": "markdown",
                        "lines": [1, 2],
                    },
                    {
                        "source": "Index.md",
                        "reference": "../../Outside.md",
                        "type": "markdown",
                        "lines": [3],
                    },
                ],
            )

    def test_excludes_repository_metadata_from_public_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in ("AGENTS.md", "PROGRESS.md", "README.md"):
                (root / name).write_text(f"# {name}\n", encoding="utf-8")
            (root / "My Search for Truth.md").write_text(
                "# Public root note\n", encoding="utf-8"
            )
            topic = root / "Word of God" / "Topic.md"
            topic.parent.mkdir()
            topic.write_text("# Public nested note\n", encoding="utf-8")

            data = build_dataset(root)
            note_ids = {
                node["id"] for node in data["nodes"] if node["type"] == "note"
            }

            self.assertEqual(
                note_ids, {"My Search for Truth.md", "Word of God/Topic.md"}
            )

    def test_preserves_complete_note_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = "# Long note\n\n" + ("complete content " * 600)
            (root / "Long note.md").write_text(source, encoding="utf-8")

            data = build_dataset(root)
            note = next(node for node in data["nodes"] if node["type"] == "note")

            self.assertGreater(len(source), 7000)
            self.assertEqual(note["content"], source)

    def test_preserves_source_newline_sequences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = b"# Windows note\r\n\r\nComplete line\r\n"
            (root / "Windows.md").write_bytes(source)

            note = next(
                node
                for node in build_dataset(root)["nodes"]
                if node["type"] == "note"
            )

            self.assertEqual(note["content"], source.decode("utf-8"))

    def test_invalid_utf8_note_fails_with_its_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Broken.md").write_bytes(b"# Broken\ntruth \xff omitted\n")

            with self.assertRaisesRegex(
                ValueError,
                r"Invalid UTF-8 in note: Broken\.md",
            ) as raised:
                build_dataset(root)
            self.assertIsInstance(raised.exception.__cause__, UnicodeDecodeError)

    def test_invalid_utf8_canvas_fails_with_its_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Broken.canvas").write_bytes(
                b'{"nodes": [], "edges": []}\xff'
            )

            with self.assertRaisesRegex(
                ValueError,
                r"Invalid UTF-8 in canvas: Broken\.canvas",
            ):
                build_dataset(root)

    def test_note_symlink_outside_vault_fails_with_its_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            projects = Path(temp_dir)
            root = projects / "vault"
            root.mkdir()
            private_note = projects / "private.md"
            private_note.write_text("# Private\nexternal secret\n", encoding="utf-8")
            (root / "Leaked.md").symlink_to(private_note)

            with self.assertRaisesRegex(
                ValueError,
                r"Note source resolves outside vault: Leaked\.md",
            ):
                build_dataset(root)

    def test_canvas_symlink_outside_vault_fails_with_its_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            projects = Path(temp_dir)
            root = projects / "vault"
            root.mkdir()
            private_canvas = projects / "private.canvas"
            private_canvas.write_text(
                '{"nodes": [], "edges": []}', encoding="utf-8"
            )
            (root / "Leaked.canvas").symlink_to(private_canvas)

            with self.assertRaisesRegex(
                ValueError,
                r"Canvas source resolves outside vault: Leaked\.canvas",
            ):
                build_dataset(root)

    def test_note_symlink_inside_vault_preserves_its_lexical_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "Target.md"
            target.write_text("# Target\n", encoding="utf-8")
            (root / "Alias.md").symlink_to(target)

            note_ids = {
                node["id"]
                for node in build_dataset(root)["nodes"]
                if node["type"] == "note"
            }

            self.assertEqual(note_ids, {"Alias.md", "Target.md"})

    def test_broken_note_symlink_fails_with_its_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Broken.md").symlink_to(root / "missing.md")

            with self.assertRaisesRegex(
                ValueError,
                r"Cannot resolve note source: Broken\.md",
            ):
                build_dataset(root)

    def test_case_folded_note_path_collision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for folder in ("Topics", "topics"):
                note = root / folder / "Grace.md"
                note.parent.mkdir()
                note.write_text(f"# {folder} Grace\n", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                r"Canonical note path collision: Topics/Grace\.md and topics/Grace\.md",
            ):
                build_dataset(root)

    def test_percent_decoded_note_path_collision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Note A.md").write_text("# Spaced\n", encoding="utf-8")
            (root / "Note%20A.md").write_text("# Encoded\n", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                r"Canonical note path collision: Note A\.md and Note%20A\.md",
            ):
                build_dataset(root)

    def test_invalid_canvas_fails_instead_of_disappearing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Broken.canvas").write_text('{"nodes": [', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Broken.canvas"):
                build_dataset(root)

    def test_committed_dataset_matches_vault_sources(self) -> None:
        committed = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if committed != build_dataset(ROOT):
            self.fail("pages/vault-data.json is stale; run the generator")

    def test_counts_and_links_are_internally_consistent(self) -> None:
        data = build_dataset(ROOT)
        ids = [node["id"] for node in data["nodes"]]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(data["counts"]["nodes"], len(data["nodes"]))
        self.assertEqual(data["counts"]["links"], len(data["links"]))
        self.assertEqual(
            data["counts"]["unresolvedLinks"],
            len(data["linkDiagnostics"]["unresolved"]),
        )
        self.assertEqual(
            data["counts"]["ambiguousLinks"],
            len(data["linkDiagnostics"]["ambiguous"]),
        )
        for link in data["links"]:
            self.assertIn(link["source"], ids)
            self.assertIn(link["target"], ids)
        for diagnostic in (
            data["linkDiagnostics"]["unresolved"]
            + data["linkDiagnostics"]["ambiguous"]
        ):
            self.assertIn(diagnostic["source"], ids)
            self.assertTrue(diagnostic["lines"])
            self.assertEqual(diagnostic["lines"], sorted(set(diagnostic["lines"])))
            self.assertTrue(all(line > 0 for line in diagnostic["lines"]))


if __name__ == "__main__":
    unittest.main()
