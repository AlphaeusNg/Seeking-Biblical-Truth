from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


class WorkflowPolicyTests(unittest.TestCase):
    def test_ci_policy_and_complete_gate(self) -> None:
        self.assertRegex(WORKFLOW, r"(?m)^name:\s*ci\s*$")
        self.assertRegex(WORKFLOW, r"push:\s*\n\s+branches:\s*\[main\]")
        self.assertRegex(WORKFLOW, r"(?m)^\s{2}pull_request:\s*$")
        self.assertRegex(WORKFLOW, r"permissions:\s*\n\s+contents:\s*read")
        self.assertRegex(
            WORKFLOW,
            r"concurrency:[\s\S]*group:\s*ci-.*github\.workflow.*github\.ref",
        )
        self.assertRegex(WORKFLOW, r"cancel-in-progress:\s*true")
        self.assertRegex(WORKFLOW, r"timeout-minutes:\s*10")
        self.assertRegex(WORKFLOW, r"uses:\s*actions/checkout@v7\b")
        self.assertRegex(WORKFLOW, r"uses:\s*actions/setup-python@v7\b")
        self.assertRegex(WORKFLOW, r"python-version:\s*[\"']3\.12[\"']")
        self.assertIn("python3 -m unittest discover -s tools -p 'test_*.py'", WORKFLOW)
        self.assertIn(
            "python3 tools/generate_vault_data.py --output /tmp/vault-data.json",
            WORKFLOW,
        )
        self.assertIn("cmp pages/vault-data.json /tmp/vault-data.json", WORKFLOW)
        self.assertIn("python3 -m compileall -q tools", WORKFLOW)
        self.assertNotIn("actions/checkout@v4", WORKFLOW)
        self.assertNotIn("actions/setup-python@v6", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
