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
    format_unresolved_link_checklist,
    is_content_file,
    serialize_dataset,
    unresolved_reference_kind,
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
            dataset = build_dataset(root)
            fresh = serialize_dataset(dataset)
            output.write_text(fresh, encoding="utf-8")
            checklist = root / "tools" / "unresolved-links.md"
            checklist.parent.mkdir()
            fresh_checklist = format_unresolved_link_checklist(dataset)
            checklist.write_text(fresh_checklist, encoding="utf-8")
            marker = "preserve me"

            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--checklist",
                    str(checklist),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Vault snapshot:", result.stdout)
            self.assertIn("Committed dataset matches vault sources.", result.stdout)
            self.assertIn(
                "Committed unresolved-link checklist matches vault sources.",
                result.stdout,
            )
            self.assertEqual(output.read_text(encoding="utf-8"), fresh)
            self.assertEqual(checklist.read_text(encoding="utf-8"), fresh_checklist)

            output.write_text(marker, encoding="utf-8")
            stale = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--checklist",
                    str(checklist),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(stale.returncode, 1)
            self.assertIn("stale", stale.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), marker)
            self.assertEqual(checklist.read_text(encoding="utf-8"), fresh_checklist)

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

    def test_invalid_canvas_structure_fails_with_its_relative_path(self) -> None:
        invalid_payloads = (
            "[]",
            json.dumps({"nodes": "not-an-array", "edges": []}),
            json.dumps({"nodes": ["not-an-object"], "edges": []}),
            json.dumps({"nodes": [{"type": "file", "file": []}], "edges": []}),
            json.dumps({"nodes": [{"type": "file"}], "edges": []}),
            json.dumps({"nodes": [], "edges": ["not-an-object"]}),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "Broken.canvas").write_text(payload, encoding="utf-8")

                with self.assertRaisesRegex(
                    ValueError,
                    "Invalid canvas structure: Broken.canvas",
                ):
                    build_dataset(root)

    def test_unresolved_checklist_groups_scripture_and_topical_by_source(self) -> None:
        self.assertEqual(unresolved_reference_kind("Num 14"), "scripture")
        self.assertEqual(unresolved_reference_kind("John 15:13"), "scripture")
        self.assertEqual(unresolved_reference_kind("1 Peter 3_20-21"), "scripture")
        self.assertEqual(unresolved_reference_kind("Deu 31_1-8"), "scripture")
        self.assertEqual(unresolved_reference_kind("Rom 4"), "scripture")
        self.assertEqual(unresolved_reference_kind("Belief"), "topical")
        self.assertEqual(unresolved_reference_kind("Kenneth Copeland"), "topical")
        self.assertEqual(unresolved_reference_kind("Women's Prayer"), "topical")
        self.assertEqual(unresolved_reference_kind("COC Theology"), "topical")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Index.md").write_text(
                "[[Num 14]]\n"
                "[[Belief]]\n"
                "[[1 Peter 3_20-21]]\n"
                "[[Faith]]\n"
                "[[John 15:13]]\n"
                "[[Kenneth Copeland]]\n"
                "[[Eph 5_25-27]]\n"
                "[[Eph 5_25-27]]\n",
                encoding="utf-8",
            )
            (root / "Notes.md").write_text(
                "[[Rom 4]]\n[[COC Theology]]\n",
                encoding="utf-8",
            )

            self.assertEqual(
                format_unresolved_link_checklist(build_dataset(root)),
                "# Unresolved link checklist\n"
                "\n"
                "Generated by tools/generate_vault_data.py. Do not hand-edit.\n"
                "\n"
                "9 unresolved note links remain as scripture or topical stubs, "
                "not path typos.\n"
                "0 ambiguous note links.\n"
                "\n"
                "## Scripture (5)\n"
                "\n"
                "### Index.md\n"
                "\n"
                "- [ ] wikilink `Num 14` (line 1)\n"
                "- [ ] wikilink `1 Peter 3_20-21` (line 3)\n"
                "- [ ] wikilink `John 15:13` (line 5)\n"
                "- [ ] wikilink `Eph 5_25-27` (lines 7, 8)\n"
                "\n"
                "### Notes.md\n"
                "\n"
                "- [ ] wikilink `Rom 4` (line 1)\n"
                "\n"
                "## Topical (4)\n"
                "\n"
                "### Index.md\n"
                "\n"
                "- [ ] wikilink `Belief` (line 2)\n"
                "- [ ] wikilink `Faith` (line 4)\n"
                "- [ ] wikilink `Kenneth Copeland` (line 6)\n"
                "\n"
                "### Notes.md\n"
                "\n"
                "- [ ] wikilink `COC Theology` (line 2)\n",
            )

            empty_root = root / "empty"
            empty_root.mkdir()
            (empty_root / "Index.md").write_text("# No links\n", encoding="utf-8")
            self.assertEqual(
                format_unresolved_link_checklist(build_dataset(empty_root)),
                "# Unresolved link checklist\n"
                "\n"
                "Generated by tools/generate_vault_data.py. Do not hand-edit.\n"
                "\n"
                "0 unresolved note links remain as scripture or topical stubs, "
                "not path typos.\n"
                "0 ambiguous note links.\n"
                "\n"
                "No unresolved scripture or topical stubs.\n",
            )

    def test_write_and_check_checklist_cli_without_writing_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Index.md").write_text(
                "[[Matt 28]]\n[[Musical Instrument]]\n",
                encoding="utf-8",
            )
            output = root / "pages" / "vault-data.json"
            output.parent.mkdir()
            output.write_text("preserve me", encoding="utf-8")
            checklist = root / "tools" / "unresolved-links.md"
            expected = format_unresolved_link_checklist(build_dataset(root))

            written = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--checklist",
                    str(checklist),
                    "--write-checklist",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertIn("Wrote 2 unresolved links", written.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")
            self.assertEqual(checklist.read_text(encoding="utf-8"), expected)

            rewritten = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--checklist",
                    str(checklist),
                    "--write-checklist",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(rewritten.returncode, 0, rewritten.stderr)
            self.assertEqual(checklist.read_text(encoding="utf-8"), expected)

            output.write_text(serialize_dataset(build_dataset(root)), encoding="utf-8")
            fresh = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--checklist",
                    str(checklist),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(fresh.returncode, 0, fresh.stderr)
            self.assertIn(
                "Committed unresolved-link checklist matches vault sources.",
                fresh.stdout,
            )

            checklist.write_text("# stale\n", encoding="utf-8")
            dataset_before = output.read_text(encoding="utf-8")
            stale = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--checklist",
                    str(checklist),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(stale.returncode, 1)
            self.assertIn("unresolved-link checklist is stale", stale.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), dataset_before)
            self.assertEqual(checklist.read_text(encoding="utf-8"), "# stale\n")

    def test_committed_dataset_matches_vault_sources(self) -> None:
        committed = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if committed != build_dataset(ROOT):
            self.fail("pages/vault-data.json is stale; run the generator")

    def test_committed_unresolved_checklist_matches_vault_sources(self) -> None:
        checklist_path = ROOT / "tools" / "unresolved-links.md"
        expected = format_unresolved_link_checklist(build_dataset(ROOT))
        try:
            committed = checklist_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            self.fail("tools/unresolved-links.md is missing; run --write-checklist")
        if committed != expected:
            self.fail("tools/unresolved-links.md is stale; run --write-checklist")

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

    def test_generated_bytes_match_committed_dataset(self) -> None:
        payload = serialize_dataset(build_dataset(ROOT))
        self.assertEqual(payload, DATA_PATH.read_text(encoding="utf-8"))

    def test_export_exclusion_hides_drafts_from_excerpts_and_canvas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Public.md").write_text(
                "[[Secret Note]]\n[[Listed Secret]]\n",
                encoding="utf-8",
            )
            (root / "Secret Note.md").write_text(
                "---\ndraft: true\n---\nFRONTMATTER_ONLY_SECRET\n",
                encoding="utf-8",
            )
            (root / "Quoted Secret.md").write_text(
                '---\ndraft: "true"\n---\nQUOTED_SECRET\n',
                encoding="utf-8",
            )
            ready = "---\ndraft: false\n---\nVISIBLE_READY\n"
            (root / "Ready.md").write_text(ready, encoding="utf-8")
            prose = "# Note\n\ndraft: true is only prose.\nVISIBLE_PROSE\n"
            (root / "Prose.md").write_text(prose, encoding="utf-8")
            closed = "---\ntitle: Public\n---\ndraft: true\nSTILL_PUBLIC\n"
            (root / "Closed.md").write_text(closed, encoding="utf-8")
            listed = "POLICY_ONLY_SECRET\n"
            (root / "Listed Secret.md").write_text(listed, encoding="utf-8")
            policy = root / "tools" / "export-exclusions.txt"
            policy.parent.mkdir()
            policy.write_text(
                "# comment\nListed Secret.md\nMissing.md\n",
                encoding="utf-8",
            )
            canvas = "\n".join(
                [
                    "{",
                    '  "nodes": [',
                    '    {"id": "secret", "type": "file", "file": "Secret Note.md"},',
                    '    {"id": "listed", "type": "file", "file": "Listed Secret.md"},',
                    '    {"id": "text", "type": "text", "text": "VISIBLE_CANVAS_TEXT"}',
                    "  ],",
                    '  "edges": [',
                    '    {"id": "edge", "fromNode": "secret", "toNode": "text"}',
                    "  ]",
                    "}",
                ]
            )
            (root / "Map.canvas").write_text(canvas, encoding="utf-8")

            data = build_dataset(root)
            note_ids = {
                node["id"] for node in data["nodes"] if node["type"] == "note"
            }
            self.assertEqual(
                note_ids,
                {"Public.md", "Ready.md", "Prose.md", "Closed.md"},
            )
            by_id = {node["id"]: node for node in data["nodes"]}
            self.assertEqual(by_id["Ready.md"]["content"], ready)
            self.assertEqual(by_id["Prose.md"]["content"], prose)
            self.assertEqual(by_id["Closed.md"]["content"], closed)
            for node in data["nodes"]:
                self.assertNotIn("FRONTMATTER_ONLY_SECRET", node["content"])
                self.assertNotIn("FRONTMATTER_ONLY_SECRET", node["excerpt"])
                self.assertNotIn("QUOTED_SECRET", node["content"])
                self.assertNotIn("POLICY_ONLY_SECRET", node["content"])
                self.assertNotIn("POLICY_ONLY_SECRET", node["excerpt"])
            canvas_node = by_id["Map.canvas"]
            self.assertIn("VISIBLE_CANVAS_TEXT", canvas_node["content"])
            self.assertNotIn("Secret Note.md", canvas_node["content"])
            self.assertNotIn("Listed Secret.md", canvas_node["content"])
            self.assertNotIn("secret", canvas_node["content"])
            targets = {link["target"] for link in data["links"]}
            self.assertNotIn("Secret Note.md", targets)
            self.assertNotIn("Listed Secret.md", targets)
            reasons = [
                diagnostic.get("reason", "")
                for diagnostic in data["linkDiagnostics"]["unresolved"]
            ]
            self.assertTrue(
                any(reason == "excluded from export (frontmatter)" for reason in reasons)
            )
            self.assertTrue(
                any(reason == "excluded from export (policy path)" for reason in reasons)
            )
            report = format_link_diagnostics(data)
            self.assertIn("excluded wikilink", report)
            self.assertIn("excluded canvas", report)
            self.assertIn("reason: excluded from export", report)

            output = root / "pages" / "vault-data.json"
            output.parent.mkdir()
            output.write_text("preserve me", encoding="utf-8")
            preview = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-exclusions",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertIn(
                "Export exclusion does not make files private in a public Git repository.",
                preview.stdout,
            )
            self.assertIn("Secret Note.md (frontmatter)", preview.stdout)
            self.assertIn("Listed Secret.md (policy path)", preview.stdout)
            self.assertIn("Missing.md", preview.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")
            self.assertEqual((root / "Secret Note.md").read_text(encoding="utf-8").count("FRONTMATTER_ONLY_SECRET"), 1)

    def test_rename_preview_lists_incoming_references_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Keep.md").write_text("# Keep\n", encoding="utf-8")
            (root / "From.md").write_text(
                "See [[Keep]]\n[also](Keep.md)\n",
                encoding="utf-8",
            )
            canvas = "\n".join(
                [
                    "{",
                    '  "nodes": [',
                    '    {"id": "n1", "type": "file", "file": "Keep.md"}',
                    "  ],",
                    '  "edges": []',
                    "}",
                ]
            )
            (root / "Map.canvas").write_text(canvas, encoding="utf-8")
            output = root / "pages" / "vault-data.json"
            output.parent.mkdir()
            output.write_text("preserve me", encoding="utf-8")
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }

            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-rename",
                    "Keep.md",
                    "Archive/Keep.md",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Note: Keep.md", result.stdout)
            self.assertIn("Destination: new path Archive/Keep.md", result.stdout)
            self.assertIn("From.md: wikilink `Keep` (line 1)", result.stdout)
            self.assertIn("From.md: markdown `Keep.md` (line 2)", result.stdout)
            self.assertIn(
                "Map.canvas: file `Keep.md` (line 3, node n1)",
                result.stdout,
            )
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

            missing = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-rename",
                    "Missing.md",
                    "Archive/Missing.md",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(missing.returncode, 1, missing.stdout)
            self.assertIn("Source: missing", missing.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")

    def test_rename_preview_states_ambiguous_destinations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for folder in ("A", "B", "Topics"):
                note = root / folder / "Grace.md"
                note.parent.mkdir()
                note.write_text(f"# {folder} Grace\n", encoding="utf-8")
            (root / "Index.md").write_text("[[A/Grace]]\n[[Grace]]\n", encoding="utf-8")
            output = root / "generated.json"
            output.write_text("preserve me", encoding="utf-8")

            ambiguous = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-rename",
                    "Index.md",
                    "Grace",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(ambiguous.returncode, 0, ambiguous.stderr)
            self.assertIn("Destination: ambiguous", ambiguous.stdout)
            self.assertIn("No destination was selected.", ambiguous.stdout)
            self.assertIn("A/Grace.md", ambiguous.stdout)
            self.assertIn("B/Grace.md", ambiguous.stdout)
            self.assertIn("Topics/Grace.md", ambiguous.stdout)
            self.assertNotIn("Destination: new path", ambiguous.stdout)
            self.assertNotIn("Destination: existing note", ambiguous.stdout)

            canonical = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-rename",
                    "Index.md",
                    "topics/Grace.md",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(canonical.returncode, 0, canonical.stderr)
            self.assertIn("Destination: ambiguous", canonical.stdout)
            self.assertIn("same canonical note identity", canonical.stdout)
            self.assertIn("Topics/Grace.md", canonical.stdout)
            self.assertIn("No destination was selected.", canonical.stdout)

            existing = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-rename",
                    "Index.md",
                    "A/Grace.md",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(existing.returncode, 0, existing.stderr)
            self.assertIn("Destination: existing note A/Grace.md", existing.stdout)
            self.assertNotIn("Destination: ambiguous", existing.stdout)

            source = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-rename",
                    "Grace",
                    "Archive/Grace.md",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(source.returncode, 0, source.stderr)
            self.assertIn("Source: ambiguous", source.stdout)
            self.assertIn("No source note was selected.", source.stdout)
            self.assertIn("Incoming references were not collected", source.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")

    def test_export_preview_reports_semantic_changes_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Alpha.md").write_text("Alpha\n[[Beta]]\n", encoding="utf-8")
            (root / "Beta.md").write_text("Beta\n", encoding="utf-8")
            (root / "Old.md").write_text("Old\n[[Alpha]]\n", encoding="utf-8")
            (root / "Map.canvas").write_text(
                '{"nodes": [{"id": "t", "type": "text", "text": "one"}], "edges": []}',
                encoding="utf-8",
            )
            output = root / "pages" / "vault-data.json"
            output.parent.mkdir()
            output.write_text(serialize_dataset(build_dataset(root)), encoding="utf-8")
            baseline = output.read_bytes()

            same = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-export",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(same.returncode, 0, same.stderr)
            for label in (
                "Added notes (0):",
                "Removed notes (0):",
                "Changed bodies (0):",
                "Resolved links (0):",
                "Broken links (0):",
                "Canvas changes (0):",
            ):
                self.assertIn(label, same.stdout)
            self.assertIn(
                "neither this repo's pages/vault-data.json nor the portfolio copy was written.",
                same.stdout,
            )
            self.assertEqual(output.read_bytes(), baseline)

            (root / "Alpha.md").write_text("Alpha changed\n", encoding="utf-8")
            (root / "Beta.md").unlink()
            (root / "Old.md").write_text("Old\n[[Gamma]]\n", encoding="utf-8")
            (root / "Gamma.md").write_text("Gamma\n", encoding="utf-8")
            (root / "Map.canvas").write_text(
                '{"nodes": [{"id": "t", "type": "text", "text": "two"}], "edges": []}',
                encoding="utf-8",
            )
            changed = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--preview-export",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertIn("Added notes (1):", changed.stdout)
            self.assertIn("- Gamma.md", changed.stdout)
            self.assertIn("Removed notes (1):", changed.stdout)
            self.assertIn("- Beta.md", changed.stdout)
            self.assertIn("Changed bodies (2):", changed.stdout)
            self.assertIn("- Alpha.md", changed.stdout)
            self.assertIn("- Old.md", changed.stdout)
            self.assertIn("Resolved links (1):", changed.stdout)
            self.assertIn("Old.md -> Gamma.md (wikilink)", changed.stdout)
            self.assertIn("Broken links (2):", changed.stdout)
            self.assertIn("Alpha.md -> Beta.md (wikilink)", changed.stdout)
            self.assertIn("Old.md -> Alpha.md (wikilink)", changed.stdout)
            self.assertIn("Canvas changes (1):", changed.stdout)
            self.assertIn("- content: Map.canvas", changed.stdout)
            self.assertNotIn("folder::", changed.stdout)
            self.assertEqual(output.read_bytes(), baseline)

            missing = root / "absent" / "vault-data.json"
            absent = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--output",
                    str(missing),
                    "--preview-export",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(absent.returncode, 1)
            self.assertIn("missing or unreadable", absent.stdout)
            self.assertIn("was written", absent.stdout)
            self.assertFalse(missing.exists())

    def test_real_vault_previews_do_not_write_either_dataset_copy(self) -> None:
        before = DATA_PATH.read_bytes()
        checklist = (ROOT / "tools" / "unresolved-links.md").read_bytes()
        portfolio = (
            ROOT.parent
            / "alphaeusng.github.io"
            / "pages"
            / "seeking-biblical-truth"
            / "vault-data.json"
        )
        portfolio_before = portfolio.read_bytes() if portfolio.is_file() else None

        export_preview = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--root",
                str(ROOT),
                "--output",
                str(DATA_PATH),
                "--preview-export",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(export_preview.returncode, 0, export_preview.stderr)
        self.assertIn("Added notes (0):", export_preview.stdout)
        self.assertIn("Changed bodies (0):", export_preview.stdout)
        self.assertIn("Resolved links (0):", export_preview.stdout)
        self.assertIn("Broken links (0):", export_preview.stdout)
        self.assertIn("Canvas changes (0):", export_preview.stdout)

        exclusion_preview = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--root",
                str(ROOT),
                "--output",
                str(DATA_PATH),
                "--preview-exclusions",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(exclusion_preview.returncode, 0, exclusion_preview.stderr)
        self.assertIn("Excluded notes (0):", exclusion_preview.stdout)
        self.assertIn("Unmatched policy paths (0):", exclusion_preview.stdout)
        self.assertIn(
            "Export exclusion does not make files private in a public Git repository.",
            exclusion_preview.stdout,
        )
        self.assertEqual(DATA_PATH.read_bytes(), before)
        self.assertEqual((ROOT / "tools" / "unresolved-links.md").read_bytes(), checklist)
        if portfolio_before is not None:
            self.assertEqual(portfolio.read_bytes(), portfolio_before)


if __name__ == "__main__":
    unittest.main()
