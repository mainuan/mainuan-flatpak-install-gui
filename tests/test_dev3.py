"""Regression tests: no real app installs/removals or host association writes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from dataclasses import replace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from metadata import parse_reference, appstream_name
from test_backend import REFERENCE, FakeDriver, OPS
import test_controller as controller_tests
from test_flatpak_api import FlatpakDriver, Flatpak, Gio, GLib
from controller import Controller, Worker
ROOT = Path(__file__).resolve().parents[1]


class PresentationTests(unittest.TestCase):
    def test_title_not_description_and_defaults(self):
        ref = parse_reference(REFERENCE.raw + b'Title=Friendly\nComment=Technical\nDescription=Long description\n')
        self.assertEqual(ref.title, 'Friendly')
        self.assertEqual(ref.app_id, REFERENCE.app_id)
        self.assertEqual(ref.branch, 'master')
        self.assertEqual(REFERENCE.title, REFERENCE.app_id)

    def test_appstream_requires_corresponding_component_and_branch(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'appstream.xml'
            text = '<components><component><id>org.example.App</id><name>Friendly</name><summary>Technical</summary><bundle type="flatpak">app/org.example.App/x86_64/master</bundle></component></components>'
            path.write_text(text)
            self.assertEqual(appstream_name(folder, REFERENCE, 'x86_64'), 'Friendly')
            self.assertEqual(appstream_name(folder, replace(REFERENCE, branch='stable'), 'x86_64'), '')
            path.write_text(text.replace('org.example.App', 'org.other.App'))
            self.assertEqual(appstream_name(folder, REFERENCE, 'x86_64'), '')
            path.write_text('invalid xml')
            self.assertEqual(appstream_name(folder, REFERENCE, 'x86_64'), '')


class DetectionTests(unittest.TestCase):
    setUpClass = classmethod(controller_tests.ControllerTests.setUpClass.__func__)
    wait_for = controller_tests.ControllerTests.wait_for
    controller = controller_tests.ControllerTests.controller
    stop = controller_tests.ControllerTests.stop

    def test_user_system_both_and_other_branch(self):
        for scopes in [('user',), ('system',), ('user', 'system')]:
            rows = [{'scope': scope, 'ref': OPS[0]['ref'], 'selected': True} for scope in scopes]
            c = self.controller(locations=rows)
            c.update(hasFile=True)
            for scope in ('user', 'system'):
                c.selectDestination(scope)
                self.wait_for(lambda: not c.view['busy'])
                self.assertEqual(bool(c.view['installed']), scope in scopes)
                self.assertEqual(c.view['phase'], 'success' if scope in scopes else 'ready')
                self.assertIn(scopes[0], c.view['existingNotice'])
        c = self.controller(locations=[{'scope': 'user', 'ref': 'app/org.example.App/x86_64/beta', 'selected': False}])
        c.update(hasFile=True)
        c.selectDestination('user')
        self.wait_for(lambda: not c.view['busy'])
        self.assertEqual(c.view['phase'], 'ready')
        self.assertIn('beta', c.view['existingNotice'])
        self.assertFalse(c.view['installed'])

    def test_query_failure_is_not_absence(self):
        def factory():
            d = FakeDriver()
            d.installed_locations = Mock(side_effect=OSError('query failed'))
            return d
        c = Controller(driver_factory=factory)
        c.reference = REFERENCE
        c.update(hasFile=True)
        c.selectDestination('system')
        self.wait_for(lambda: not c.view['busy'])
        self.assertEqual(c.view['phase'], 'error')
        self.assertIn('query failed', c.view['details'])

    def test_confirmed_remove_and_exact_open(self):
        c = self.controller()
        selected = {'scope': 'system', 'name': REFERENCE.app_id, 'arch': 'x86_64', 'branch': 'master', 'ref': OPS[0]['ref']}
        c.update(installed=selected, phase='success', name='Friendly', scope='system')
        c.launch()
        self.wait_for(lambda: not c.view['busy'])
        self.assertIn('launch:system:' + selected['ref'], self.drivers[-1].log)
        c.requestRemove()
        self.assertEqual(c.view['phase'], 'confirmRemove')
        self.assertIn('Friendly', c.view['notice'])
        self.assertIn('system', c.view['notice'])
        self.assertFalse(any('remove:' in x for d in self.drivers for x in d.log))
        c.confirmRemove()
        self.wait_for(lambda: not c.view['busy'])
        self.assertIn('remove:system:' + selected['ref'], self.drivers[-1].log)
        self.assertEqual(c.view['phase'], 'ready')
        self.assertFalse(c.view['installed'])
        self.assertIn('preservados', c.view['message'])

    def test_override_is_only_presentation(self):
        c = self.controller()
        c.override_name = '<Friendly>'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'x.flatpakref'
            path.write_bytes(REFERENCE.raw)
            c.loadFile(str(path))
            self.wait_for(lambda: not c.view['busy'])
            self.assertEqual(c.view['name'], '<Friendly>')
            self.assertEqual(c.reference.app_id, REFERENCE.app_id)
            self.assertFalse(any(x.startswith('MUTATE') for x in self.drivers[0].log))

    def test_reopen_after_installation(self):
        installed = {'scope': 'user', 'ref': OPS[0]['ref'], 'selected': True}
        c = self.controller(locations=[installed])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'installed.flatpakref'
            path.write_bytes(REFERENCE.raw)
            c.loadFile(str(path))
            self.wait_for(lambda: not c.view['busy'])
            self.assertEqual(c.view['message'], 'Já instalado')
            self.assertEqual(c.view['installed']['ref'], installed['ref'])


@unittest.skipIf(FlatpakDriver is None, 'Flatpak GI required')
class ScopedApiTests(unittest.TestCase):
    def test_prepare_never_falls_back(self):
        driver = FlatpakDriver()
        user, system = Mock(), Mock()
        with patch.object(Flatpak.Installation, 'new_user', return_value=user) as u, patch.object(Flatpak.Installation, 'new_system', return_value=system) as s:
            driver.prepare(REFERENCE, 'user')
            self.assertIs(driver.installation, user)
            driver.prepare(REFERENCE, 'system')
            self.assertIs(driver.installation, system)
            s.side_effect = RuntimeError('no system')
            with self.assertRaises(RuntimeError): driver.prepare(REFERENCE, 'system')
            self.assertEqual(u.call_count, 1)

    def test_inventory_exact_identity_and_caches(self):
        d = FlatpakDriver()
        d.full_ref = OPS[0]['ref']
        ref = Mock()
        ref.get_kind.return_value = Flatpak.RefKind.APP
        ref.get_name.return_value = REFERENCE.app_id
        ref.get_arch.return_value = 'x86_64'
        ref.get_branch.return_value = 'master'
        ref.format_ref.return_value = OPS[0]['ref']
        user, system = Mock(), Mock()
        system.get_id.return_value = 'default'
        for inst in (user, system): inst.list_installed_refs.return_value = [ref]
        with patch.object(Flatpak.Installation, 'new_user', return_value=user), patch.object(Flatpak, 'get_system_installations', return_value=[system]):
            rows = d.installed_locations(REFERENCE)
            self.assertEqual({r['scope'] for r in rows}, {'user', 'system'})
            self.assertTrue(all(r['selected'] for r in rows))
            for inst in (user, system): inst.drop_caches.assert_called_once()
            system.list_installed_refs.side_effect = OSError('denied')
            with self.assertRaises(OSError): d.installed_locations(REFERENCE)

    def test_remove_success_error_cancel_denied_and_still_present(self):
        selected = {'scope': 'system', 'name': REFERENCE.app_id, 'arch': 'x86_64', 'branch': 'master', 'ref': OPS[0]['ref']}
        absent = GLib.Error.new_literal(Flatpak.error_quark(), 'absent', Flatpak.Error.NOT_INSTALLED)
        denied = GLib.Error.new_literal(Flatpak.error_quark(), 'denied', Flatpak.Error.NOT_AUTHORIZED)
        cancelled = GLib.Error.new_literal(Gio.io_error_quark(), 'cancelled', Gio.IOErrorEnum.CANCELLED)
        for outcome in (None, denied, cancelled, RuntimeError('failure'), 'still present'):
            d, inst, tx, ref = FlatpakDriver(), Mock(), Mock(), Mock()
            ref.format_ref.return_value = selected['ref']
            inst.get_installed_ref.side_effect = [ref, ref if outcome == 'still present' else absent]
            d.action_installation = Mock(return_value=inst)
            tx.run.return_value = True
            if isinstance(outcome, Exception): tx.run.side_effect = outcome
            with patch.object(Flatpak.Transaction, 'new_for_installation', return_value=tx):
                if outcome is None: d.remove(selected)
                else:
                    with self.assertRaises(Exception): d.remove(selected)
            tx.add_uninstall.assert_called_once_with(selected['ref'])
            tx.set_disable_related.assert_called_once_with(True)
            tx.set_disable_dependencies.assert_called_once_with(True)
            tx.set_disable_prune.assert_called_once_with(True)
            tx.run.assert_called_once_with(d.cancellable)
            self.assertNotIn('delete_data', [call[0] for call in tx.method_calls])

    def test_remove_ready_rejects_other_references_and_preserves_data(self):
        d, inst, tx, ref = FlatpakDriver(), Mock(), Mock(), Mock()
        selected = {'scope': 'user', 'name': REFERENCE.app_id, 'arch': 'x86_64', 'branch': 'master', 'ref': OPS[0]['ref']}
        ref.format_ref.return_value = selected['ref']
        absent = GLib.Error.new_literal(Flatpak.error_quark(), 'absent', Flatpak.Error.NOT_INSTALLED)
        inst.get_installed_ref.side_effect = [ref, absent]
        d.action_installation = Mock(return_value=inst)
        tx.run.return_value = True
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'personal-data'
            data.write_text('keep me')
            with patch.object(Flatpak.Transaction, 'new_for_installation', return_value=tx):
                d.remove(selected)
            self.assertEqual(data.read_text(), 'keep me')
        ready = next(call.args[1] for call in tx.connect.call_args_list if call.args[0] == 'ready')
        operation = Mock()
        operation.get_ref.return_value = 'app/org.example.App/x86_64/beta'
        operation.get_operation_type.return_value = Flatpak.TransactionOperationType.UNINSTALL
        tx.get_operations.return_value = [operation]
        self.assertFalse(ready(tx))
        operation.get_ref.return_value = selected['ref']
        self.assertTrue(ready(tx))

    def test_worker_removal_error_and_cancel_are_not_success(self):
        selected = {'scope': 'user', 'ref': OPS[0]['ref']}
        for cancel in (False, True):
            d = FakeDriver(fail='remove')
            worker = Worker(installed=selected, remove=True, driver_factory=lambda: d)
            events = []
            worker.event.connect(events.append)
            if cancel: worker.cancel()
            worker.run()
            self.assertEqual(events[-1]['event'], 'cancelled' if cancel else 'error')
            self.assertFalse(any(e['event'] in ('success', 'removed') for e in events))


class DesktopTests(unittest.TestCase):
    def test_registration_default_precedence_and_spaces(self):
        with tempfile.TemporaryDirectory(prefix='mainuan-desktop-') as folder:
            root = Path(folder)
            apps = root / 'data/applications'
            apps.mkdir(parents=True)
            config, distro, binaries = root / 'config', root / 'distro', root / 'bin'
            for directory in (config, distro, binaries): directory.mkdir()
            stub = binaries / 'mainuan-flatpak-install-gui'
            log = root / 'arguments'
            stub.write_text('#!/usr/bin/python3\nimport os, sys\nfrom pathlib import Path\nPath(os.environ["ARGUMENT_LOG"]).write_text(repr(sys.argv[1:]))\n')
            stub.chmod(0o755)
            desktop = apps / 'mainuan-flatpak-install-gui.desktop'
            desktop.write_bytes((ROOT / 'launcher').read_bytes())
            other = apps / 'other.desktop'
            other.write_text('[Desktop Entry]\nType=Application\nName=Personal preference\nExec=/usr/bin/true %f\nMimeType=application/vnd.flatpak.ref;\n')
            env = {**os.environ, 'HOME': str(root), 'XDG_CONFIG_HOME': str(config), 'XDG_CONFIG_DIRS': str(distro), 'XDG_DATA_HOME': str(root/'data'), 'XDG_DATA_DIRS': '/usr/local/share:/usr/share', 'XDG_CURRENT_DESKTOP': 'X-Generic', 'KDE_FULL_SESSION': '', 'GNOME_DESKTOP_SESSION_ID': '', 'DESKTOP_SESSION': '', 'DE': 'generic', 'PATH': str(binaries) + ':' + os.environ['PATH'], 'ARGUMENT_LOG': str(log)}
            subprocess.run(['desktop-file-validate', str(desktop)], check=True, env=env)
            subprocess.run(['update-desktop-database', str(apps)], check=True, env=env)
            self.assertIn('mainuan-flatpak-install-gui.desktop', (apps/'mimeinfo.cache').read_text())
            (distro/'mimeapps.list').write_bytes((ROOT/'packaging/mainuan-mimeapps.list').read_bytes())
            query = ['xdg-mime', 'query', 'default', 'application/vnd.flatpak.ref']
            self.assertEqual(subprocess.check_output(query, env=env, text=True).strip(), desktop.name)
            (config/'mimeapps.list').write_text('[Default Applications]\napplication/vnd.flatpak.ref=other.desktop;\n')
            self.assertEqual(subprocess.check_output(query, env=env, text=True).strip(), 'other.desktop')
            subprocess.run(['xdg-mime', 'default', desktop.name, 'application/vnd.flatpak.ref'], env=env, check=True)
            self.assertEqual(subprocess.check_output(query, env=env, text=True).strip(), desktop.name)
            file = root / 'my app # spaces.flatpakref'
            file.write_bytes(REFERENCE.raw)
            self.assertEqual(subprocess.check_output(['xdg-mime', 'query', 'filetype', str(file)], env=env, text=True).strip(), 'application/vnd.flatpak.ref')
            subprocess.run(['gio', 'launch', str(desktop), str(file)], env=env, check=True, stdout=subprocess.DEVNULL)
            deadline = time.monotonic() + 3
            while not log.exists() and time.monotonic() < deadline: time.sleep(.01)
            self.assertEqual(log.read_text(), repr([str(file)]))
