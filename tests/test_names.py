"""Presentation regressions. Operations remain keyed by the immutable reference."""
import gzip
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from metadata import parse_reference, friendly_name, appstream_name, installed_appstream_name
from controller import Worker, Controller
import test_controller as helpers
from test_backend import FakeDriver
from test_flatpak_api import FlatpakDriver

SCRIBE = b'[Flatpak Ref]\nName=io.github.gnacho.Scribe\nBranch=stable\nTitle=io.github.gnacho.Scribe from flathub\nUrl=https://dl.flathub.org/repo/\n'
XML = b'<components><component><id>io.github.gnacho.Scribe</id><name>Scribe Studio Pro</name><bundle type="flatpak">app/io.github.gnacho.Scribe/x86_64/stable</bundle></component></components>'


class NameTests(unittest.TestCase):
    def test_exact_observed_title_and_missing_title(self):
        ref = parse_reference(SCRIBE)
        self.assertEqual(ref.display_name, 'Scribe')
        self.assertEqual(ref.title, 'io.github.gnacho.Scribe from flathub')
        self.assertEqual(ref.app_id, 'io.github.gnacho.Scribe')
        self.assertEqual(ref.info['name'], 'Scribe')
        self.assertEqual(friendly_name(ref.app_id), 'Scribe')

    def test_friendly_titles_and_legitimate_from_are_preserved(self):
        for title in ('Scribe', 'Letters from Home', 'Scribe from flathub',
                      'io.github.gnacho.Scribe from the Heart', '<b>Scribe & Co.</b>'):
            self.assertEqual(friendly_name('io.github.gnacho.Scribe', title), title)
        self.assertEqual(friendly_name('org.example.MixedCASE', 'org.example.MixedCASE from source'), 'MixedCASE')

    def test_appstream_overrides_title_and_preserves_case_spaces(self):
        self.assertEqual(friendly_name('io.github.gnacho.Scribe', 'Other title', 'Scribe Studio Pro'), 'Scribe Studio Pro')
        ref = parse_reference(SCRIBE)
        self.assertEqual(installed_appstream_name(gzip.compress(XML), ref, 'x86_64'), 'Scribe Studio Pro')
        self.assertEqual(installed_appstream_name(gzip.compress(XML.replace(b'gnacho.Scribe', b'other.App')), ref, 'x86_64'), '')
        self.assertEqual(installed_appstream_name(b'corrupt', ref, 'x86_64'), '')

    def test_catalog_larger_than_old_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            with gzip.open(Path(folder) / 'appstream.xml.gz', 'wb') as stream:
                stream.write(b'<components>')
                padding = b'<component><id>org.other.App</id><description>' + b'x' * 32768 + b'</description></component>'
                for _ in range(1050): stream.write(padding)
                stream.write(XML.removeprefix(b'<components>').removesuffix(b'</components>'))
                stream.write(b'</components>')
            self.assertEqual(appstream_name(folder, parse_reference(SCRIBE), 'x86_64'), 'Scribe Studio Pro')

    def test_bad_external_metadata_and_offline_do_not_change_fallback(self):
        d = FakeDriver()
        d.presentation_name = Mock(side_effect=OSError('offline'))
        worker = Worker(reference=parse_reference(SCRIBE), inspect=True, driver_factory=lambda: d)
        events = []
        worker.event.connect(events.append)
        worker.run()
        self.assertEqual(events[-1]['event'], 'inspected')
        self.assertEqual(events[-1]['name'], 'Scribe')
        self.assertFalse(any(x.startswith('MUTATE') for x in d.log))
        self.assertEqual(worker.reference.raw, SCRIBE)

    @unittest.skipIf(FlatpakDriver is None, 'GI Flatpak unavailable')
    def test_installed_compressed_metadata_before_remote_cache(self):
        d = FlatpakDriver()
        ref = parse_reference(SCRIBE)
        d.full_ref = 'app/io.github.gnacho.Scribe/x86_64/stable'
        d.arch = 'x86_64'
        inst, installed = Mock(), Mock()
        d.installations = [('user', inst)]
        inst.list_installed_refs.return_value = [installed]
        installed.format_ref.return_value = d.full_ref
        installed.get_appdata_name.return_value = ''
        installed.load_appdata.return_value.get_data.return_value = gzip.compress(XML)
        self.assertEqual(d.presentation_name(ref), 'Scribe Studio Pro')
        inst.list_remotes.assert_not_called()
        installed.get_appdata_name.return_value = 'sCRIBE Local Edition'
        installed.load_appdata.side_effect = OSError('local XML unavailable')
        inst.list_remotes.return_value = []
        self.assertEqual(d.presentation_name(ref), 'sCRIBE Local Edition')


class NameLifecycleTests(unittest.TestCase):
    setUpClass = classmethod(helpers.ControllerTests.setUpClass.__func__)
    wait_for = helpers.ControllerTests.wait_for

    def test_name_before_after_install_and_reopen_identity_unchanged(self):
        shared = {'installed': False, 'identity': []}
        ref = parse_reference(SCRIBE)
        full_ref = 'app/io.github.gnacho.Scribe/x86_64/stable'
        class Driver(FakeDriver):
            def __init__(self): super().__init__(existing=True)
            def installed_locations(self, reference):
                return [self.verify(reference)] if shared['installed'] else []
            def presentation_name(self, reference):
                return 'Scribe Studio Pro' if shared['installed'] else reference.display_name
            def verify(self, reference):
                shared['identity'].append((reference.app_id, reference.branch, self.scope))
                return {'scope': self.scope, 'name': reference.app_id, 'branch': reference.branch, 'arch': 'x86_64', 'ref': full_ref, 'selected': True}
            def run(self, tx):
                super().run(tx)
                shared['installed'] = True
            def launch(self, installed): shared['identity'].append(installed['ref'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Scribe.flatpakref'
            path.write_bytes(SCRIBE)
            c = Controller(driver_factory=Driver)
            c.loadFile(str(path))
            self.assertEqual(c.view['name'], 'Scribe')
            self.wait_for(lambda: not c.view['busy'])
            c.install()
            self.wait_for(lambda: not c.view['busy'])
            self.assertEqual(c.view['phase'], 'success')
            self.assertEqual(c.view['name'], 'Scribe Studio Pro')
            self.assertEqual(c.view['installed']['ref'], full_ref)
            c.launch()
            self.wait_for(lambda: not c.view['busy'])
            self.assertEqual(shared['identity'][-1], full_ref)
            c.requestRemove()
            self.assertIn('Scribe Studio Pro', c.view['notice'])
            reopened = Controller(driver_factory=Driver)
            reopened.loadFile(str(path))
            self.wait_for(lambda: not reopened.view['busy'])
            self.assertEqual(reopened.view['name'], 'Scribe Studio Pro')
            self.assertEqual(reopened.reference.raw, SCRIBE)
            self.assertEqual(reopened.view['installed']['ref'], full_ref)
            self.assertIn((ref.app_id, 'stable', 'user'), shared['identity'])
