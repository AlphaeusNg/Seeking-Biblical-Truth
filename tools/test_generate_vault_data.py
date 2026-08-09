from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.generate_vault_data import build_dataset


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "pages" / "vault-data.json"


class VaultDatasetTests(unittest.TestCase):
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
        for link in data["links"]:
            self.assertIn(link["source"], ids)
            self.assertIn(link["target"], ids)


if __name__ == "__main__":
    unittest.main()
