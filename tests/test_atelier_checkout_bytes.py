"""The content-addressed script must survive native checkout newline settings."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class AtelierCheckoutBytesTests(unittest.TestCase):
    def test_hashed_script_remains_byte_exact_under_checkout_settings(self):
        git = shutil.which("git")
        self.assertIsNotNone(git, "Git is required for the checkout-byte contract")
        root = Path(__file__).resolve().parents[1]
        attributes = (root / ".gitattributes").read_bytes()
        fixture = b'// Synthetic byte-preservation fixture, not production code.\nconst value = 1;\n'
        for setting in ("true", "input", "false"):
            with self.subTest(core_autocrlf=setting):
                with tempfile.TemporaryDirectory(prefix="atelier-checkout-contract-") as tmp:
                    temp = Path(tmp)
                    target = temp / "atelier" / "app.js"
                    target.parent.mkdir()
                    target.write_bytes(fixture)
                    (temp / ".gitattributes").write_bytes(attributes)

                    def run(*args):
                        return subprocess.run(
                            [git, "-C", str(temp), *args],
                            capture_output=True, check=True, timeout=15,
                        )

                    run("init", "--quiet")
                    run("config", "--local", "core.autocrlf", setting)
                    run("add", "--", ".gitattributes", "atelier/app.js")
                    target.unlink()  # Only this test's temporary synthetic fixture.
                    run("checkout-index", "--", "atelier/app.js")
                    self.assertEqual(target.read_bytes(), fixture)


if __name__ == "__main__":
    unittest.main()
