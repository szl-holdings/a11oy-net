"""Offline JavaScript regression checks, collected by the existing Python CI."""
from pathlib import Path
import shutil
import subprocess
import unittest


class AtelierJavascriptTests(unittest.TestCase):
    def test_script_and_model_base_examples(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required to validate the shipped JavaScript")
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [node, "--test", str(root / "tests" / "atelier-script.test.cjs")],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Atelier JavaScript regression failed:\n{result.stdout}\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
