"""Verify the static archive contains the files required by the game."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


spec = importlib.util.spec_from_file_location("web_build", Path(__file__).with_name("build.py"))
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class WebBuildTests(unittest.TestCase):
    def test_archive_contains_runtime_without_local_or_generated_data(self):
        with tempfile.TemporaryDirectory() as directory:
            original = build.DIST
            build.DIST = Path(directory)
            try:
                build.build()
            finally:
                build.DIST = original
            output = Path(directory)
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "boot.py").is_file())
            with zipfile.ZipFile(output / "game.zip") as archive:
                names = set(archive.namelist())
                self.assertTrue({"matrix.py", "card_layout.py", "card_art.py", "digital/app.py",
                                 "digital/game.py", "digital/table.py", "digital/card_faces.py",
                                 "digital/assets/LiberationSans-Regular.ttf",
                                 "digital/assets/LICENSE_LIBERATION",
                                 "expansion_split/generated/deck.json"} <= names)
                self.assertFalse(any(name.startswith("digital/saves/") or name.endswith(".pdf")
                                     or "__pycache__" in name for name in names))
                self.assertEqual(archive.read("expansion_split/generated/deck.json"),
                                 (build.ROOT / "expansion_split/generated/deck.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
