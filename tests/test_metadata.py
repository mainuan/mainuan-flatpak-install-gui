import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qt"))
from metadata import read_reference

class ReferenceTests(unittest.TestCase):
    def read(self, content):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "app.flatpakref"
            path.write_text(content)
            return read_reference(path)

    def test_valid(self):
        result = self.read("[Flatpak Ref]\nName=org.example.App\nUrl=https://example.org/repo\nTitle=Exemplo 100%\n")
        self.assertEqual(result["name"], "Exemplo 100%")

    def test_rejects_invalid_inputs(self):
        for text in ["", "[Flatpak Ref]\nName=bad\nUrl=https://example.org",
                     "[Flatpak Ref]\nName=org.example.App\nUrl=http://example.org",
                     "[Flatpak Ref]\nName=org.example.App\nUrl=https://user:pass@example.org",
                     "[Flatpak Ref]\nName=org.example.App\nUrl=https://example.org\nIsRuntime=true",
                     "x" * 65537]:
            with self.subTest(text=text[:100]), self.assertRaises(ValueError):
                self.read(text)

if __name__ == "__main__":
    unittest.main()
