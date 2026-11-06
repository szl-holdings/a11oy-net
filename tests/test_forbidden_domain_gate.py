"""Executable contract for the forbidden-domain gate.

The gate once called ripgrep, which ubuntu-latest does not install, and its
`|| true` turned "rg: command not found" into a clean result. These tests run
the workflow's own `run:` block against synthetic trees, so a scanner that is
missing or broken fails the gate instead of passing it.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "forbidden-domain.yml"
STEP_NAME = "      - name: Scan for forbidden domain references"
RUN_INDENT = " " * 10
# Assembled at runtime so this test file never matches the rule itself.
FORBIDDEN = "a11oy" + ".com"


def gate_script() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = lines.index(STEP_NAME)
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body = []
    for line in lines[run_at + 1:]:
        if line.strip() and not line.startswith(RUN_INDENT):
            break
        body.append(line[len(RUN_INDENT):])
    return "\n".join(body) + "\n"


def gnu_grep_with_pcre() -> bool:
    grep = shutil.which("grep")
    if grep is None:
        return False
    probe = subprocess.run(
        [grep, "-P", "(?<!-)x"], input="x\n", capture_output=True, text=True, check=False
    )
    return probe.returncode == 0


BASH = shutil.which("bash")


@unittest.skipUnless(
    BASH and gnu_grep_with_pcre(),
    "the gate runs bash with GNU grep -P on ubuntu-latest; this host lacks one of them",
)
class ForbiddenDomainGateTests(unittest.TestCase):
    def run_gate(self, files: dict[str, str], *, path: str | None = None) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(prefix="forbidden-domain-") as tmp:
            tree = pathlib.Path(tmp)
            for name, text in files.items():
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            script = tree.parent / f"{tree.name}-gate.sh"
            script.write_text(gate_script(), encoding="utf-8")
            try:
                env = {"PATH": path if path is not None else "/usr/bin:/bin"}
                return subprocess.run(
                    [BASH, "--noprofile", "--norc", "-eo", "pipefail", str(script)],
                    cwd=tree,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
            finally:
                script.unlink()

    def test_unguarded_reference_fails_and_is_printed(self) -> None:
        result = self.run_gate({"page.html": f"<a href=\"https://{FORBIDDEN}/\">shop</a>\n"})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Forbidden domain references found", result.stdout)
        self.assertIn("./page.html:1:", result.stdout)

    def test_guarded_hyphenated_and_git_references_pass(self) -> None:
        result = self.run_gate(
            {
                "notes.md": f"Never link {FORBIDDEN}; the product is a-11-oy.com.\n",
                "record.json": f'{{"never": ["{FORBIDDEN}"]}}\n',
                ".git/config": f"url = https://{FORBIDDEN}\n",
            }
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2 matching line(s), all in guard contexts", result.stdout)

    def test_empty_tree_passes_only_after_the_scanner_self_test(self) -> None:
        result = self.run_gate({"index.html": "<p>proof origin</p>\n"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 matching line(s)", result.stdout)

    def test_missing_scanner_fails_closed(self) -> None:
        result = self.run_gate(
            {"page.html": f"https://{FORBIDDEN}/\n"},
            path="/nonexistent",
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("scanner self-test failed", result.stdout)
        self.assertNotIn("OK:", result.stdout)


class ForbiddenDomainWorkflowContractTests(unittest.TestCase):
    def test_gate_does_not_depend_on_ripgrep_or_mask_exit_status(self) -> None:
        commands = "\n".join(
            line for line in gate_script().splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotRegex(commands, r"(^|[\s|($])rg\s")
        self.assertNotIn("|| true", commands)
        self.assertIn("set -euo pipefail", commands)
        self.assertIn("pattern='(?<!-)a11oy\\.com'", commands)


if __name__ == "__main__":
    unittest.main()
