from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "report_stub_near_misses.py"


def write_note(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {Path(relative).stem}\n", encoding="utf-8")


def write_decisions(path: Path, rows: list[tuple[str, str, str]]) -> None:
    lines = [
        "Prose above the table is not a stub, even if it mentions Faith.",
        "",
        "| Kind | Source | Stub | Lines | Status |",
        "|---|---|---|---|---|",
    ]
    for kind, source, stub in rows:
        lines.append(f"| {kind} | {source} | {stub} | 1 | pending owner |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_report(root: Path, decisions: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--decisions",
            str(decisions),
        ],
        check=False,
        capture_output=True,
        cwd=root,
        text=True,
        encoding="utf-8",
    )


def vault_snapshot(root: Path) -> tuple[tuple[str, ...], tuple[tuple[str, bytes], ...]]:
    paths: list[str] = []
    files: list[tuple[str, bytes]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        paths.append(f"{relative}/" if path.is_dir() else relative)
        if path.is_file():
            files.append((relative, path.read_bytes()))
    return tuple(paths), tuple(files)


class StubNearMissTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_bare_title_is_near_miss_not_exact(self) -> None:
        tmp_path = self.root
        write_note(tmp_path, "notes/Faith.md")
        decisions = tmp_path / "tools" / "stub-decisions.md"
        write_decisions(decisions, [("topical", "topics/Source.md", "Faith")])

        result = run_report(tmp_path, decisions)

        assert result.returncode == 0, result.stderr
        assert result.stdout == (
            "EXACT\n"
            "\n"
            "NEAR MISS\n"
            "Faith\ttopics/Source.md\tnotes/Faith.md\n"
        )


    def test_full_path_is_exact_and_not_a_suggestion(self) -> None:
        tmp_path = self.root
        write_note(tmp_path, "notes/Faith.md")
        decisions = tmp_path / "tools" / "stub-decisions.md"
        write_decisions(decisions, [("topical", "topics/Source.md", "notes/Faith.md")])

        result = run_report(tmp_path, decisions)

        assert result.returncode == 0, result.stderr
        assert result.stdout == (
            "EXACT\n"
            "notes/Faith.md\ttopics/Source.md\tnotes/Faith.md\n"
            "\n"
            "NEAR MISS\n"
        )
        assert "NEAR MISS\nnotes/Faith.md" not in result.stdout


    def test_case_only_stem_difference_is_near_miss(self) -> None:
        tmp_path = self.root
        write_note(tmp_path, "notes/Belief.md")
        decisions = tmp_path / "tools" / "stub-decisions.md"
        write_decisions(decisions, [("topical", "topics/Source.md", "belief")])

        result = run_report(tmp_path, decisions)

        assert result.returncode == 0, result.stderr
        assert result.stdout == (
            "EXACT\n"
            "\n"
            "NEAR MISS\n"
            "belief\ttopics/Source.md\tnotes/Belief.md\n"
        )


    def test_unmatched_stub_is_omitted(self) -> None:
        tmp_path = self.root
        write_note(tmp_path, "notes/Other.md")
        decisions = tmp_path / "tools" / "stub-decisions.md"
        write_decisions(decisions, [("scripture", "topics/Source.md", "Num 14")])

        result = run_report(tmp_path, decisions)

        assert result.returncode == 0, result.stderr
        assert "Num 14" not in result.stdout
        assert result.stdout == "EXACT\n\nNEAR MISS\n"


    def test_report_does_not_create_or_modify_vault_files(self) -> None:
        tmp_path = self.root
        write_note(tmp_path, "notes/Faith.md")
        write_note(tmp_path, "notes/Belief.md")
        (tmp_path / "keep.txt").write_text("leave me\n", encoding="utf-8")
        decisions = tmp_path / "tools" / "stub-decisions.md"
        write_decisions(
            decisions,
            [
                ("topical", "topics/Source.md", "Faith"),
                ("topical", "topics/Source.md", "notes/Belief.md"),
                ("scripture", "topics/Source.md", "Num 14"),
            ],
        )
        before = vault_snapshot(tmp_path)

        result = run_report(tmp_path, decisions)

        assert result.returncode == 0, result.stderr
        assert "NEAR MISS\nFaith\t" in result.stdout
        assert "EXACT\nnotes/Belief.md\t" in result.stdout
        assert vault_snapshot(tmp_path) == before


    def test_pending_filter_excludes_resolved_rows_without_writing(self) -> None:
        write_note(self.root, "notes/Faith.md")
        write_note(self.root, "notes/Belief.md")
        decisions = self.root / "tools" / "stub-decisions.md"
        write_decisions(decisions, [
            ("topical", "Source.md", "Faith"),
            ("topical", "Source.md", "Belief"),
        ])
        decisions.write_text(decisions.read_text().replace("Belief | 1 | pending owner", "Belief | 1 | resolved"))
        before = vault_snapshot(self.root)
        result = subprocess.run([
            sys.executable, str(SCRIPT), "--root", str(self.root),
            "--decisions", str(decisions), "--pending-only",
        ], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Pending owner decisions: 1", result.stdout)
        self.assertIn("Faith\t", result.stdout)
        self.assertNotIn("Belief\t", result.stdout)
        self.assertEqual(vault_snapshot(self.root), before)
