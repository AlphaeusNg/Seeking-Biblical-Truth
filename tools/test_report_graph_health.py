from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.report_graph_health import graph_health
from tools.vault_dataset_assembly import build_dataset


SCRIPT = Path(__file__).resolve().with_name("report_graph_health.py")


def snapshot(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


class GraphHealthTests(unittest.TestCase):
    def test_directed_neighbors_components_exclusions_and_read_only_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in {
                "A.md": "[[B]]\n[B](B.md)\n[[B]]\n[[Missing Stub]]\n",
                "B.md": "[[C]]\n",
                "C.md": "# C\n",
                "D.md": "[[D]]\n",
                "Draft.md": "---\ndraft: true\n---\nSECRET_BODY [[D]]\n",
                "Policy Secret.md": "[[D]] SECRET_BODY\n",
                "tools/export-exclusions.txt": "Policy Secret.md\n",
                "docs/FEATURE_ROADMAP.md": "Maintenance only\n",
                ".obsidian/Secret.md": "SECRET_BODY\n",
            }.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            (root / "Map.canvas").write_text(json.dumps({"nodes": [
                {"id": "d", "type": "file", "file": "D.md"},
                {"id": "secret", "type": "file", "file": "Draft.md"},
            ], "edges": []}), encoding="utf-8")
            before = snapshot(root)
            command = [sys.executable, str(SCRIPT), "--root", str(root)]
            result = subprocess.run(command + ["--json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["schemaVersion"], 1)
            self.assertEqual(report["counts"], {"notes": 4, "noteLinks": 2, "isolated": 1, "components": 2})
            self.assertEqual(report["isolated"], ["D.md"])
            self.assertEqual(report["withoutIncoming"], ["A.md", "D.md"])
            self.assertEqual(report["withoutOutgoing"], ["C.md", "D.md"])
            self.assertEqual(report["components"], [["A.md", "B.md", "C.md"], ["D.md"]])
            self.assertEqual(report["notes"][0], {
                "path": "A.md", "incoming": [], "outgoing": ["B.md"], "canvasMentions": []})
            self.assertEqual(report["notes"][-1]["canvasMentions"], ["Map.canvas"])
            human = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(human.returncode, 0, human.stderr)
            self.assertIn("Isolated notes (1):\n- D.md", human.stdout)
            self.assertIn("Notes without outgoing links (2):\n- C.md\n- D.md", human.stdout)
            for output in (result.stdout, human.stdout):
                for omitted in ("SECRET_BODY", "Draft.md", "Policy Secret.md", "Missing Stub", "FEATURE_ROADMAP"):
                    self.assertNotIn(omitted, output)
            repeated = subprocess.run(command + ["--json"], capture_output=True, text=True)
            self.assertEqual(result.stdout, repeated.stdout)
            self.assertEqual(snapshot(root), before)
            data = build_dataset(root)
            reordered = dict(data, nodes=list(reversed(data["nodes"])), links=list(reversed(data["links"])))
            self.assertEqual(graph_health(data), graph_health(reordered))

    def test_empty_vault_is_valid_and_missing_or_invalid_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable, str(SCRIPT), "--root", str(root), "--json"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["counts"], {"notes": 0, "noteLinks": 0, "isolated": 0, "components": 0})
            self.assertEqual(report["components"], [])
            (root / "Broken.md").write_bytes(b"\xff")
            before = snapshot(root)
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("Invalid UTF-8 in note: Broken.md", result.stderr)
            self.assertEqual(snapshot(root), before)
            missing = subprocess.run(command[:-2] + [str(root / "absent"), "--json"], capture_output=True, text=True)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("Missing vault", missing.stderr)
