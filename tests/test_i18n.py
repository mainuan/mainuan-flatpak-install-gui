"""i18n: English source strings, pt_BR from po/pt_BR.po, language only from the session.

Compiles the real catalog into a temporary directory and exercises the real
code (Python, argparse and QML through the gettext QTranslator).
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'qt'))
import i18n  # noqa: E402
from i18n import DOMAIN  # noqa: E402

PORTUGUESE = {'LANGUAGE': 'pt_BR', 'LC_ALL': '', 'LC_MESSAGES': '', 'LANG': 'pt_BR.UTF-8'}
ENGLISH = {'LANGUAGE': 'en', 'LC_ALL': '', 'LC_MESSAGES': '', 'LANG': 'en_US.UTF-8'}
POSIX = {'LANGUAGE': '', 'LC_ALL': 'C', 'LC_MESSAGES': '', 'LANG': 'C'}


@unittest.skipIf(shutil.which('msgfmt') is None, 'msgfmt (gettext) unavailable')
class I18nTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        target = Path(cls.tmp.name) / 'pt_BR' / 'LC_MESSAGES'
        target.mkdir(parents=True)
        subprocess.run(['msgfmt', '--check', '-o', str(target / f'{DOMAIN}.mo'),
                        str(ROOT / 'po' / 'pt_BR.po')], check=True)
        cls.locale = {'MAINUAN_FLATPAK_INSTALL_GUI_LOCALEDIR': cls.tmp.name}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def env(self, language):
        return patch.dict(os.environ, {**language, **self.locale})

    def test_python_strings_follow_the_session_language(self):
        from demo import demo_state
        from metadata import parse_reference
        with self.env(PORTUGUESE):
            self.assertEqual(i18n._('Welcome'), 'Boas-vindas')
            self.assertEqual(i18n.pgettext('transaction operation', 'Install'), 'Instalar')
            self.assertEqual(demo_state('error')['message'], 'Erro simulado: não foi possível acessar a origem.')
            with self.assertRaisesRegex(ValueError, 'Referência Flatpak inválida.'):
                parse_reference(b'not a reference')
        for language in (ENGLISH, POSIX):
            with self.subTest(language=language), self.env(language):
                self.assertEqual(i18n._('Welcome'), 'Welcome')
                self.assertEqual(demo_state('error')['message'], 'Simulated error: could not access the source.')
                with self.assertRaisesRegex(ValueError, 'Invalid Flatpak reference.'):
                    parse_reference(b'not a reference')

    def test_placeholders_are_filled_after_translation(self):
        with self.env(PORTUGUESE):
            text = i18n._('Uninstall {name} ({scope})? Personal data will be preserved.').format(name='Scribe', scope='user')
            self.assertEqual(text, 'Desinstalar Scribe (user)? Os dados pessoais serão preservados.')

    def test_command_line_messages(self):
        from main import arguments
        for language, expected in ((PORTUGUESE, 'Destino inválido: use user, system ou system:ID.'),
                                   (ENGLISH, 'Invalid destination: use user, system or system:ID.')):
            with self.subTest(language=language['LANGUAGE']), self.env(language):
                error = io.StringIO()
                with contextlib.redirect_stderr(error), self.assertRaises(SystemExit):
                    arguments(['--scope', 'bad', 'a.flatpakref'])
                self.assertIn(expected, error.getvalue())

    def test_flatpak_error_messages(self):
        try:
            from flatpak_backend import FlatpakDriver, Flatpak, GLib
        except (ImportError, ValueError):
            self.skipTest('GI Flatpak unavailable')
        error = GLib.Error.new_literal(Flatpak.error_quark(), 'raw flatpak text', Flatpak.Error.OUT_OF_SPACE)
        with self.env(PORTUGUESE):
            self.assertEqual(FlatpakDriver.error_message(error), 'Não há espaço suficiente para instalar.')
        with self.env(ENGLISH):
            self.assertEqual(FlatpakDriver.error_message(error), 'There is not enough space to install.')

    def test_desktop_entry_is_translated_at_build_time(self):
        output = Path(self.tmp.name) / 'launcher.desktop'
        subprocess.run(['msgfmt', '--desktop', f'--template={ROOT / "launcher"}', '-d', str(ROOT / 'po'),
                        '-o', str(output)], check=True)
        text = output.read_text(encoding='utf-8')
        self.assertIn('\nName=Mainuan Flatpak Installer\n', text)
        self.assertIn('\nName[pt_BR]=Mainuan Instalador Flatpak\n', text)
        self.assertIn('\nComment[pt_BR]=Instale aplicativos a partir de arquivos de referência Flatpak\n', text)

    def test_qml_uses_the_same_catalog(self):
        try:
            import PyQt6.QtQml  # noqa: F401
        except ImportError:
            self.skipTest('PyQt6 unavailable')
        def run(language):
            env = {**os.environ, **language, **self.locale, 'QT_QPA_PLATFORM': 'offscreen'}
            out = subprocess.run([sys.executable, str(ROOT / 'tests' / 'qml_i18n.py')], env=env,
                                 capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 0, out.stderr)
            return json.loads(out.stdout.strip().splitlines()[-1])
        pt = run(PORTUGUESE)
        self.assertEqual(pt['title'], 'Mainuan Instalador Flatpak')
        self.assertEqual(pt['displayName'], 'Mainuan Instalador Flatpak')
        self.assertEqual(pt['installButton'], 'Instalar')
        self.assertEqual(pt['closeButton'], 'Fechar')
        self.assertEqual(pt['userDestination'], 'Apenas seu usuário')
        self.assertEqual(pt['systemDestination'], 'Todo o sistema')
        self.assertEqual(pt['detailsToggle'], 'Ver detalhes')
        self.assertEqual(pt['installationMessage'], 'Demonstração sem instalações.')
        self.assertEqual(pt['installationTitle'], 'Aplicativo de exemplo')
        self.assertIn('Origem: https://example.org/repo\nSerá adicionada se necessária ao instalar.', pt['installationSource'])
        self.assertEqual(pt['progressMessage'], 'Baixando a operação atual (simulação)…')
        for language in (ENGLISH, POSIX):
            with self.subTest(language=language):
                en = run(language)
                self.assertEqual(en['title'], 'Mainuan Flatpak Installer')
                self.assertEqual(en['installButton'], 'Install')
                self.assertEqual(en['closeButton'], 'Close')
                self.assertEqual(en['userDestination'], 'Only your user')
                self.assertEqual(en['detailsToggle'], 'Show Details')
                self.assertEqual(en['installationMessage'], 'Demonstration without installations.')
                self.assertIn('Source: https://example.org/repo\nIt will be added if needed when installing.', en['installationSource'])

    def test_right_to_left_catalog_mirrors_qml_without_qtbase(self):
        try:
            import PyQt6.QtQml  # noqa: F401
        except ImportError:
            self.skipTest('PyQt6 unavailable')
        target = Path(self.tmp.name) / 'ar' / 'LC_MESSAGES'
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run(['msgfmt', '--check', '-o', str(target / f'{DOMAIN}.mo'),
                        str(ROOT / 'po' / 'ar.po')], check=True)

        def run(language):
            with tempfile.TemporaryDirectory() as empty:
                # Empty Qt translations directory: no qtbase_<lang>.qm can mirror the layout.
                env = {**os.environ, 'LANGUAGE': language, 'LC_ALL': '', 'LC_MESSAGES': '', 'LANG': 'en_US.UTF-8',
                       **self.locale, 'QT_QPA_PLATFORM': 'offscreen', 'QML_I18N_QT_TRANSLATIONS': empty}
                out = subprocess.run([sys.executable, str(ROOT / 'tests' / 'qml_i18n.py')], env=env,
                                     capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 0, out.stderr)
            return json.loads(out.stdout.strip().splitlines()[-1])
        # The application's Arabic catalog is used: the QML window is mirrored.
        ar = run('ar')
        self.assertEqual(ar['layoutDirection'], 'RightToLeft')
        self.assertTrue(ar['mirrored'])
        # Urdu is right-to-left but has no application catalog: English, left to right.
        ur = run('ur')
        self.assertEqual(ur['installButton'], 'Install')
        self.assertEqual(ur['layoutDirection'], 'LeftToRight')
        self.assertFalse(ur['mirrored'])


class CatalogLookupTests(unittest.TestCase):
    def test_installed_layout_is_the_default(self):
        with patch.dict(os.environ, {'MAINUAN_FLATPAK_INSTALL_GUI_LOCALEDIR': ''}), \
                patch('i18n.Path.is_dir', return_value=False):
            self.assertIsNone(i18n.localedir())  # gettext default: /usr/share/locale

    def test_no_forced_language(self):
        for path in ('qt/main.py', 'qt/i18n.py', 'qt/controller.py', 'mainuan-flatpak-install-gui',
                     'packaging/mainuan-flatpak-install-gui', 'flatpak-install-gui'):
            text = (ROOT / path).read_text()
            self.assertNotIn('setDefault', text)
            self.assertNotIn('LANG=', text)


if __name__ == '__main__':
    unittest.main()
