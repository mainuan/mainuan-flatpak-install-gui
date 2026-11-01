"""Names and summaries must remain separate from the operation identity."""
import gzip
import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from metadata import parse_reference, appstream_stream_presentation, installed_appstream_presentation, desktop_presentation
from controller import Worker
from test_backend import FakeDriver
from test_flatpak_api import FlatpakDriver

GIMP = parse_reference(b'[Flatpak Ref]\nName=org.gimp.GIMP\nBranch=stable\nTitle=org.gimp.GIMP from flathub\nUrl=https://dl.flathub.org/repo/\n')
XML = '''<component><id>org.gimp.GIMP</id><name>GNU Image Manipulation Program</name><name xml:lang="pt-BR">Programa de manipulação de imagem do GNU</name><summary>Create and edit images</summary><summary xml:lang="pt-BR">Crie e edite imagens</summary><bundle type="flatpak">app/org.gimp.GIMP/x86_64/stable</bundle></component>'''.encode()

def presentation(xml=XML, ref=GIMP):
    return appstream_stream_presentation(io.BytesIO(xml), ref, 'x86_64')

class PresentationTests(unittest.TestCase):
    def test_localized_gimp_name_and_summary(self):
        with patch('locale.getlocale', return_value=('pt_BR', 'UTF-8')):
            self.assertEqual(presentation(), {'name': 'GIMP', 'description': 'Crie e edite imagens'})
        self.assertEqual(GIMP.app_id, 'org.gimp.GIMP')
        self.assertEqual(GIMP.branch, 'stable')

    def test_expanded_english_name_as_description_if_summary_absent(self):
        xml = XML[:XML.index(b'<summary>')] + b'</component>'
        self.assertEqual(presentation(xml), {'name': 'GIMP', 'description': 'GNU Image Manipulation Program'})

    def test_acronym_match_is_generic_and_restricted(self):
        ref = parse_reference(GIMP.raw.replace(b'org.gimp.GIMP', b'org.example.RTE'))
        xml = XML.replace(b'org.gimp.GIMP', b'org.example.RTE').replace(b'GNU Image Manipulation Program', b'Rapid Text Editor')
        self.assertEqual(presentation(xml, ref)['name'], 'RTE')
        ref = parse_reference(GIMP.raw.replace(b'org.gimp.GIMP', b'org.example.ABC'))
        xml = b'<component><id>org.example.ABC</id><name>Really Nice App</name></component>'
        self.assertEqual(presentation(xml, ref)['name'], 'Really Nice App')

    def test_scribe_name_and_summary(self):
        ref = parse_reference(GIMP.raw.replace(b'org.gimp.GIMP', b'io.github.gnacho.Scribe'))
        xml = b'<component><id>io.github.gnacho.Scribe</id><name>Scribe</name><summary>Markdown editor with live rendering</summary></component>'
        self.assertEqual(presentation(xml, ref), {'name': 'Scribe', 'description': 'Markdown editor with live rendering'})
        self.assertEqual(presentation(xml.replace(b'<summary>Markdown editor with live rendering</summary>', b''), ref)['description'], '')

    def test_desktop_name_is_separate_from_generic_name_and_comment(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'app.desktop'
            p.write_text('[Desktop Entry]\nName=GIMP\nGenericName=Image Editor\nComment=Edit photos\nExec=never-executed\n')
            self.assertEqual(desktop_presentation(p), {'name': 'GIMP', 'description': 'Edit photos'})

    def test_worker_transmits_both_fields_without_mutation(self):
        d = FakeDriver()
        d.presentation = lambda ref: presentation()
        events = []
        w = Worker(reference=GIMP, inspect=True, driver_factory=lambda: d)
        w.event.connect(events.append)
        w.run()
        self.assertEqual(events[-1]['name'], 'GIMP')
        self.assertTrue(events[-1]['description'])
        self.assertEqual(w.reference.raw, GIMP.raw)
        self.assertFalse(any(x.startswith('MUTATE') for x in d.log))

    def test_installed_desktop_expansion_does_not_override_short_name(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'app.desktop'
            p.write_text('[Desktop Entry]\nName=GNU Image Manipulation Program\nName[pt_BR]=Programa de manipulação de imagem do GNU\nComment=Edit photos\n')
            with patch('locale.getlocale', return_value=('pt_BR', 'UTF-8')):
                self.assertEqual(desktop_presentation(p, GIMP.app_id)['name'], 'GIMP')

    @unittest.skipIf(FlatpakDriver is None, 'GI Flatpak unavailable')
    def test_installed_gimp_xml_and_desktop_keep_title_and_summary_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            deploy = Path(folder)
            desktop = deploy / 'files/share/applications/org.gimp.GIMP.desktop'
            desktop.parent.mkdir(parents=True)
            desktop.write_text('[Desktop Entry]\nName=GNU Image Manipulation Program\nName[pt_BR]=Programa de manipulação de imagem do GNU\nComment=Edit photos\n')
            d = FlatpakDriver()
            d.full_ref = 'app/org.gimp.GIMP/x86_64/stable'
            d.arch = 'x86_64'
            inst, ref = Mock(), Mock()
            ref.format_ref.return_value = d.full_ref
            ref.get_appdata_name.return_value = 'Programa de manipulação de imagem do GNU'
            ref.get_appdata_summary.return_value = 'Crie e edite imagens'
            ref.load_appdata.return_value.get_data.return_value = gzip.compress(XML)
            ref.get_deploy_dir.return_value = str(deploy)
            inst.list_installed_refs.return_value = [ref]
            d.installations = [('user', inst)]
            with patch('locale.getlocale', return_value=('pt_BR', 'UTF-8')):
                self.assertEqual(d.presentation(GIMP), {'name': 'GIMP', 'description': 'Crie e edite imagens'})
            self.assertEqual(GIMP.app_id, 'org.gimp.GIMP')
