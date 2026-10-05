"""Offline JavaScript regression checks, collected by the existing Python CI."""
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import unittest


class AtelierJavascriptTests(unittest.TestCase):
    def test_module_reference_tracks_exact_script_bytes(self):
        class ModuleScripts(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sources = []

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == "script" and attributes.get("type") == "module":
                    self.sources.append(attributes.get("src"))

        root = Path(__file__).resolve().parents[1]
        script_hash = hashlib.sha256((root / "atelier/app.js").read_bytes()).hexdigest()
        page = ModuleScripts()
        page.feed((root / "atelier/index.html").read_text(encoding="utf-8"))
        page.close()
        self.assertEqual(
            page.sources,
            [f"./app.js?v={script_hash}"],
            "Refresh the Atelier module URL fingerprint whenever app.js changes",
        )

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
