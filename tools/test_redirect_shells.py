from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_VIEWER = "https://alphaeusng.github.io/pages/seeking-biblical-truth/"
SHELLS = (ROOT / "index.html", ROOT / "pages" / "index.html")


class RedirectShellTests(unittest.TestCase):
    def test_legacy_pages_redirect_to_the_canonical_viewer(self) -> None:
        for shell in SHELLS:
            source = shell.read_text(encoding="utf-8")
            with self.subTest(shell=shell.relative_to(ROOT)):
                self.assertIn(
                    f'<meta http-equiv="refresh" content="0; url={CANONICAL_VIEWER}">',
                    source,
                )
                self.assertIn(f'<link rel="canonical" href="{CANONICAL_VIEWER}">', source)
                self.assertIn('<meta name="robots" content="noindex, follow">', source)
                self.assertIn(f'href="{CANONICAL_VIEWER}"', source)

    def test_legacy_shells_are_identical_and_inert(self) -> None:
        root_source = SHELLS[0].read_text(encoding="utf-8")
        self.assertEqual(root_source, SHELLS[1].read_text(encoding="utf-8"))
        self.assertNotIn("<script", root_source.lower())
        self.assertNotIn("vault-data.json", root_source)
        self.assertNotIn("cdn", root_source.lower())


if __name__ == "__main__":
    unittest.main()
