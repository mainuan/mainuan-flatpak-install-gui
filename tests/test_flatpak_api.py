from dataclasses import replace
"""Installed ABI checks and signal adapters, using only a temporary installation.
No transaction.run(), downloads, host remote changes or app installations.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
try:
    from flatpak_backend import FlatpakDriver, Flatpak, Gio, GLib, OSTree, HttpsOnly
except (ImportError, ValueError):
    FlatpakDriver = None
from test_backend import REFERENCE as UNSIGNED_REFERENCE
REFERENCE = replace(UNSIGNED_REFERENCE, remote=replace(UNSIGNED_REFERENCE.remote, key=Path("/usr/share/keyrings/ubuntu-archive-keyring.gpg").read_bytes()))
from backend import Installer, Decisions, OriginConflict


@unittest.skipIf(FlatpakDriver is None, 'Introspecção Flatpak indisponível')
class FlatpakApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.driver = FlatpakDriver()
        self.driver.scope = 'user'
        self.driver.arch = Flatpak.get_default_arch()
        self.driver.full_ref = f'app/org.example.App/{self.driver.arch}/master'
        self.driver.installation = Flatpak.Installation.new_for_path(Gio.File.new_for_path(self.tmp.name), True, None)
        self.driver.expected_remote = None

    def test_real_remote_api_in_disposable_repository(self):
        name = self.driver.add_remote(REFERENCE.remote)
        self.assertEqual(self.driver.remote_candidates(REFERENCE.remote), [name])
        self.assertFalse(self.driver.is_installed(REFERENCE))
        with self.assertRaises(OriginConflict):
            self.driver.add_remote(REFERENCE.remote)
        self.assertTrue(self.driver.installation.get_remote_by_name(name, None).get_gpg_verify())

    def test_real_signals_abort_before_execution(self):
        name = self.driver.add_remote(REFERENCE.remote)
        decisions = Decisions()
        def emit(event):
            if 'token' in event: decisions.answer(event['token'], False)
        policy = Installer(self.driver, decisions, emit)
        tx = self.driver.transaction(REFERENCE, name, policy)
        decisions.cancel()
        self.assertFalse(tx.emit('ready-pre-auth'))
        self.assertIsNotNone(policy.callback_error)
        self.assertTrue(self.driver.cancellable.is_cancelled())

    def test_progress_signature_and_estimation(self):
        op = Mock()
        op.get_ref.return_value = 'app/org.example.App/x86_64/master'
        p = Mock()
        p.get_is_estimating.return_value = True
        p.get_status.return_value = 'Receiving'
        policy = Mock()
        policy.guarded.side_effect = lambda fallback, callback, *args: callback(*args)
        self.driver.new_operation(op, p, policy)
        self.assertEqual(policy.progress.call_args.args[-1], -1)
        p.get_is_estimating.return_value = False
        p.get_progress.return_value = 17
        callback = p.connect.call_args.args[1]
        callback(p)
        self.assertEqual(policy.progress.call_args.args[-1], 17)

    def test_https_redirect_cannot_downgrade(self):
        with self.assertRaises(ValueError):
            HttpsOnly().redirect_request(None, None, 302, '', {}, 'http://example.org/repo')

    def test_auth_and_busy_errors_are_short_and_specific(self):
        cases = [(Flatpak.error_quark(), Flatpak.Error.NOT_AUTHORIZED, 'autorização'),
                 (Flatpak.error_quark(), Flatpak.Error.PERMISSION_DENIED, 'Permissão'),
                 (Gio.io_error_quark(), Gio.IOErrorEnum.BUSY, 'Outra instalação')]
        for domain, code, expected in cases:
            e = GLib.Error.new_literal(domain, 'technical error', code)
            self.assertIn(expected, self.driver.error_message(e))

    def test_launch_uses_verified_identity_and_scope_without_shell(self):
        for scope in ('user', 'system'):
            installed = {'scope': scope, 'name': 'org.example.App', 'arch': 'x86_64', 'branch': 'stable'}
            ref = Mock()
            ref.get_name.return_value = installed['name']
            ref.get_arch.return_value = installed['arch']
            ref.get_branch.return_value = installed['branch']
            inst = Mock()
            inst.get_installed_ref.return_value = ref
            with patch.object(Flatpak.Installation, 'new_user', return_value=inst) as user, \
                 patch.object(Flatpak.Installation, 'new_system', return_value=inst) as system:
                self.driver.launch(installed)
                self.assertEqual(user.call_count, int(scope == 'user'))
                self.assertEqual(system.call_count, int(scope == 'system'))
                inst.get_installed_ref.assert_called_once_with(Flatpak.RefKind.APP, installed['name'], 'x86_64', 'stable', self.driver.cancellable)
                inst.launch.assert_called_once_with(installed['name'], 'x86_64', 'stable', None, self.driver.cancellable)

    def test_same_name_different_url_never_matches(self):
        self.driver.add_remote(REFERENCE.remote)
        self.assertEqual(self.driver.remote_candidates(replace(REFERENCE.remote, url='https://other.example.org/repo')), [])

    def test_same_url_two_origins_reports_ambiguity(self):
        one = self.driver.add_remote(REFERENCE.remote)
        two = self.driver.add_remote(replace(REFERENCE.remote, suggested='alias'))
        remote = self.driver.installation.get_remote_by_name(two, None)
        remote.set_noenumerate(True)
        self.driver.installation.modify_remote(remote, None)
        self.driver.pinned_remotes.clear()  # Existing differences before a new operation.
        self.assertEqual(set(self.driver.remote_candidates(REFERENCE.remote)), {one, two})

    def test_disabled_or_filtered_origin_not_silently_reused(self):
        for option in ('disabled', 'filter'):
            with self.subTest(option=option):
                name = self.driver.add_remote(replace(REFERENCE.remote, url='https://' + option + '.example.org', suggested=option))
                remote = self.driver.installation.get_remote_by_name(name, None)
                if option == 'disabled': remote.set_disabled(True)
                else:
                    path = Path(self.tmp.name) / 'filter'
                    path.write_text('deny *\n')
                    remote.set_filter(str(path))
                self.driver.installation.modify_remote(remote, None)
                with self.assertRaises(OriginConflict):
                    self.driver.remote_candidates(replace(REFERENCE.remote, url=remote.get_url()))

    def test_gpg_identity_checked_with_real_ostree(self):
        keyfile = Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg')
        if not keyfile.exists(): self.skipTest('public Ubuntu test keyring unavailable')
        spec = replace(REFERENCE.remote, key=keyfile.read_bytes())
        name = self.driver.add_remote(spec)
        self.assertEqual(self.driver.remote_candidates(spec), [name])
        self.assertTrue(self.driver.key_fingerprints(spec.key))
        remote = self.driver.installation.get_remote_by_name(name, None)
        remote.set_gpg_verify(False)
        self.driver.installation.modify_remote(remote, None)
        with self.assertRaises(OriginConflict): self.driver.remote_candidates(spec)

    def test_ready_vetoes_unrequested_app_or_uninstall(self):
        self.driver.add_remote(REFERENCE.remote)
        ops = [{'type': 'install', 'ref': self.driver.full_ref, 'remote': REFERENCE.remote.suggested}]
        self.driver.validate_operations(ops, REFERENCE, REFERENCE.remote.suggested)
        for ref, kind in [('app/org.other.App/x86_64/master', 'install'), (self.driver.full_ref, 'uninstall')]:
            with self.assertRaises(OriginConflict):
                self.driver.validate_operations([{**ops[0], 'ref': ref, 'type': kind}], REFERENCE, ops[0]['remote'])

    def test_configuration_change_between_ready_signals_is_rejected(self):
        name = self.driver.add_remote(REFERENCE.remote)
        remote = self.driver.installation.get_remote_by_name(name, None)
        remote.set_url('https://elsewhere.example.org')
        self.driver.installation.modify_remote(remote, None)
        with self.assertRaises(OriginConflict):
            self.driver.validate_operations([], REFERENCE, name)

    def test_identical_origin_aliases_are_unambiguous(self):
        one = self.driver.add_remote(REFERENCE.remote)
        self.driver.add_remote(replace(REFERENCE.remote, suggested='alias'))
        self.assertEqual(self.driver.remote_candidates(REFERENCE.remote), [one])
