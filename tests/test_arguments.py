import contextlib
import io
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from main import arguments


class ArgumentTests(unittest.TestCase):
    def test_normal_and_demo_are_distinct(self):
        self.assertIsNone(arguments([]).demo)
        self.assertEqual(arguments(['--demo']).demo, 'ready')
        self.assertEqual(arguments(['--demo', 'error']).demo, 'error')
        self.assertEqual(arguments(['/tmp/um app.flatpakref']).reference, '/tmp/um app.flatpakref')

    def test_unsupported_legacy_and_multiple_files_fail_explicitly(self):
        cases = [['--remove', 'org.example.App'],
                 ['--do-install', 'a.flatpakref'], ['--fetch-dependencies', 'a.flatpakref'],
                 ['a.flatpakref', 'b.flatpakref'], ['--demo', 'ready', 'a.flatpakref']]
        for case in cases:
            with self.subTest(case=case):
                error = io.StringIO()
                with contextlib.redirect_stderr(error), self.assertRaises(SystemExit) as raised:
                    arguments(case)
                self.assertEqual(raised.exception.code, 2)
                self.assertTrue(error.getvalue())

    def test_remove_requires_explicit_scope_and_file(self):
        args = arguments(['--remove', '--scope', 'system', '/tmp/um app.flatpakref'])
        self.assertTrue(args.remove)
        self.assertEqual(args.scope, 'system')
        self.assertEqual(arguments(['--override-appname=Nome', 'a.flatpakref']).override_appname, 'Nome')
