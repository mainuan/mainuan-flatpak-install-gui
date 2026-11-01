"""Release-candidate review: cancellation boundaries, lifetime and public CLI."""
import contextlib
import io
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from backend import Decisions, Installer, OriginConflict
from controller import Controller, Worker
from main import arguments
from test_backend import FakeDriver, REFERENCE, OPS
import test_controller as helpers


class FinalBoundaryTests(unittest.TestCase):
    def test_install_cancelled_after_successful_driver_return_is_not_success(self):
        for stage in ('run', 'verify'):
            d, decisions, events = FakeDriver(existing=True), Decisions(), []
            original = getattr(d, stage)
            def cancel_after(*args):
                result = original(*args)
                decisions.cancel()
                return result
            setattr(d, stage, cancel_after)
            Installer(d, decisions, events.append).run(REFERENCE, 'system')
            self.assertEqual(events[-1]['event'], 'cancelled')
            self.assertFalse(any(e['event'] == 'success' for e in events))

    def test_callback_conflict_is_error_even_if_driver_aborts_with_cancellation(self):
        d, events = FakeDriver(existing=True), []
        policy = Installer(d, Decisions(), events.append)
        class TransactionCancelled(Exception): pass
        def abort(tx):
            policy.callback_error = OriginConflict('Chave alterada')
            raise TransactionCancelled()
        d.run = abort
        d.is_cancelled = lambda error: isinstance(error, TransactionCancelled)
        policy.run(REFERENCE, 'user')
        self.assertEqual(events[-1]['event'], 'error')
        self.assertIn('Chave alterada', events[-1]['details'])

    def test_worker_late_cancel_does_not_emit_removed_or_launched(self):
        for remove in (False, True):
            d, events = FakeDriver(), []
            worker = Worker(installed={'scope': 'user', 'ref': OPS[0]['ref']}, remove=remove,
                            driver_factory=lambda: d)
            def completed_but_cancelled(installed): worker.decisions.cancel()
            if remove: d.remove = completed_but_cancelled
            else: d.launch = completed_but_cancelled
            worker.event.connect(events.append)
            worker.run()
            self.assertEqual(events[-1]['event'], 'cancelled')
            self.assertFalse(any(e['event'] in ('removed', 'launched', 'success') for e in events))

    def test_inspection_cancel_during_optional_metadata_does_not_emit_ready(self):
        d, events = FakeDriver(), []
        worker = Worker(reference=REFERENCE, inspect=True, driver_factory=lambda: d)
        def metadata(ref):
            worker.decisions.cancel()
            return {'name': 'Example', 'description': ''}
        d.presentation = metadata
        worker.event.connect(events.append)
        worker.run()
        self.assertEqual(events[-1]['event'], 'cancelled')
        self.assertFalse(any(e['event'] == 'inspected' for e in events))

    def test_cli_explicit_scope_and_plaintext_override(self):
        for scope in ('user', 'system', 'system:extra'):
            for override in ('<b>Nome</b> & $(touch /never)', 'Nome com espaços'):
                args = arguments(['--override-appname='+override, '--remove', '--scope', scope, '/um caminho/app.flatpakref'])
                self.assertEqual(args.override_appname, override)
                self.assertEqual(args.scope, scope)
                self.assertEqual(args.reference, '/um caminho/app.flatpakref')

    def test_default_system_alias_uses_the_same_detection_scope(self):
        self.assertEqual(arguments(['--scope', 'system:default', 'a.flatpakref']).scope, 'system')

    def test_internal_options_have_accurate_retirement_error(self):
        for flag in ('--fetch-dependencies', '--do-install'):
            output = io.StringIO()
            with contextlib.redirect_stderr(output), self.assertRaises(SystemExit) as result:
                arguments([flag, 'a.flatpakref'])
            self.assertEqual(result.exception.code, 2)
            self.assertIn('descontinuados', output.getvalue())
            self.assertNotIn('--remove, --override-appname', output.getvalue())

    def test_bare_legacy_id_requires_migration_to_a_local_reference(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
            arguments(['--override-appname=Exemplo', 'org.example.App'])
        self.assertIn('arquivo .flatpakref local', output.getvalue())

    def test_demo_rejects_scope_and_even_empty_name_override(self):
        for options in (['--scope','system'], ['--override-appname=']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                arguments(['--demo','ready',*options])


class LifetimeTests(unittest.TestCase):
    setUpClass = classmethod(helpers.ControllerTests.setUpClass.__func__)
    wait_for = helpers.ControllerTests.wait_for

    def test_shutdown_cancels_pending_decision_and_joins_worker(self):
        c = Controller(driver_factory=lambda: FakeDriver(candidates=['one','two']))
        c.reference = REFERENCE
        c.install()
        self.wait_for(lambda: c.view['phase'] == 'chooseRemote')
        c.shutdown()
        self.assertFalse(c.worker.isRunning())
        self.app.processEvents()
        self.assertEqual(c.view['phase'], 'cancelled')

    def test_demo_destination_and_all_actions_cannot_create_worker(self):
        forbidden = Mock(side_effect=AssertionError('demo started a real worker'))
        c = Controller('success', driver_factory=forbidden)
        c.reference = REFERENCE
        c.selectDestination('system')
        c.install()
        c.launch()
        c.requestRemove()
        c.confirmRemove()
        c.respond(True, 0)
        self.assertIsNone(c.worker)
        forbidden.assert_not_called()

    def test_initial_system_scope_is_used_by_inspection(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'app.flatpakref'
            path.write_bytes(REFERENCE.raw)
            d = FakeDriver()
            c = Controller(driver_factory=lambda: d)
            c.update(scope='system')
            c.loadFile(str(path))
            self.wait_for(lambda: not c.view['busy'])
            self.assertEqual(d.scope, 'system')
            self.assertEqual(c.view['scope'], 'system')
