import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from metadata import LIMIT, read_reference, parse_reference, parse_runtime_repo

VALID = b'[Flatpak Ref]\nName=org.example.App\nUrl=https://example.org/repo\nTitle=Exemplo 100% <b>& $(touch /tmp/no)\n'


class ReferenceTests(unittest.TestCase):
    def test_valid_and_pinned_bytes_and_spaces(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'um app.flatpakref'
            path.write_bytes(VALID)
            result = read_reference(path)
            path.write_text('substituido')
            self.assertEqual(result.raw, VALID)
            self.assertEqual(result.title, 'Exemplo 100% <b>& $(touch /tmp/no)')
            self.assertEqual(result.branch, 'master')
            with self.assertRaises(Exception):
                result.raw = b''

    def test_rejects_invalid_inputs(self):
        for raw in (b'', b'[Flatpak Ref]\nName=bad\nUrl=https://example.org',
                    VALID.replace(b'Url=', b'Other='), VALID.replace(b'Name=', b'Other='),
                    VALID.replace(b'https:', b'http:'), VALID.replace(b'example.org', b'user:pass@example.org'),
                    VALID + b'IsRuntime=true\n', VALID + b'GPGKey=not base64\n',
                    VALID + b'Name=org.evil.App\n', VALID + b'RuntimeRepo=http://example.org/r\n',
                    VALID + b'Branch=../bad\n', VALID + b'IsRuntime=garbage\n',
                    VALID.replace(b'/repo', b'/repo\\s'), VALID + b'\x00',
                    b'\xff', b'x' * (LIMIT + 1), VALID + b'[DEFAULT]\nUrl=https://evil.org\n'):
            with self.subTest(raw=raw[:120]), self.assertRaises(ValueError):
                parse_reference(raw)

    def test_runtime_repo_security(self):
        raw = b'[Flatpak Repo]\nUrl=https://runtime.example.org/repo\nTitle=Runtime\nGPGKey=a2V5\n'
        spec = parse_runtime_repo(raw, 'https://example.org/runtime.flatpakrepo')
        self.assertEqual(spec.key, b'key')
        self.assertIn('não garante', spec.notice())
        for suffix in (b'Filter=foo\n', b'AuthenticatorName=example\n', b'Url=https://evil.org\n'):
            with self.assertRaises(ValueError):
                parse_runtime_repo(raw + suffix, 'https://example.org')

    def test_non_regular_and_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                read_reference(directory)
            path = Path(directory) / 'folder.flatpakref'
            path.mkdir()
            with self.assertRaises((ValueError, OSError)):
                read_reference(path)
