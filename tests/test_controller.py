import sys
import tempfile
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
try:
    from PyQt6.QtCore import QCoreApplication
    from controller import Controller
except ImportError:
    Controller = None
from test_backend import FakeDriver, REFERENCE, OPS


@unittest.skipIf(Controller is None, 'PyQt6 indisponível')
class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def wait_for(self, predicate):
        end = time.monotonic() + 3
        while not predicate() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(predicate())

    def controller(self, existing=True, locations=None, candidates=None):
        self.drivers = []
        def factory():
            d = FakeDriver(existing=existing, locations=locations, candidates=candidates)
            self.drivers.append(d)
            return d
        c = Controller(driver_factory=factory)
        c.reference = REFERENCE
        self.addCleanup(lambda: self.stop(c))
        return c

    def stop(self, c):
        if c.worker and c.worker.isRunning():
            c.worker.cancel()
            self.assertTrue(c.worker.wait(3000))
        self.app.processEvents()

    def test_repeated_clicks_do_not_duplicate_transaction(self):
        c = self.controller()
        c.selectDestination('system')
        c.install()
        c.selectDestination('user')
        c.install()
        self.wait_for(lambda: not c.view['busy'])
        self.assertEqual(c.view['phase'], 'success')
        self.assertEqual(len(self.drivers), 1)
        self.assertEqual(c.view['scope'], 'system')
        self.assertEqual(self.drivers[0].scope, 'system')
        self.assertEqual(self.drivers[0].log.count('MUTATE:install'), 1)
        self.assertTrue(c.view['operations'])

    def test_close_cancels_and_waits_for_worker(self):
        c = self.controller(existing=False, candidates=['one', 'two'])
        closed = []
        c.safeToClose.connect(lambda: closed.append(True))
        c.install()
        self.wait_for(lambda: c.view['phase'] == 'chooseRemote')
        self.assertFalse(c.requestClose())
        self.wait_for(lambda: bool(closed))
        self.assertFalse(c.worker.isRunning())
        self.assertEqual(c.view['phase'], 'cancelled')
        self.assertNotIn('MUTATE:install', self.drivers[0].log)
        self.assertTrue(c.requestClose())

    def test_reject_confirmation_is_cancellation_not_error(self):
        c = self.controller(existing=False, candidates=['one', 'two'])
        c.install()
        self.wait_for(lambda: c.view['phase'] == 'chooseRemote')
        c.respond(False, 0)
        self.wait_for(lambda: not c.view['busy'])
        self.assertEqual(c.view['phase'], 'cancelled')
        self.assertNotIn('MUTATE:install', self.drivers[0].log)

    def test_inspect_existing_destinations_before_install_without_mutation(self):
        c = self.controller(locations=[{'scope': 'system', 'ref': OPS[0]['ref']}])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'um app.flatpakref'
            path.write_bytes(REFERENCE.raw)
            c.loadFile(str(path))
            self.wait_for(lambda: not c.view['busy'])
            c.selectDestination('system')
            self.wait_for(lambda: not c.view['busy'])
            self.assertEqual(c.view['phase'], 'success')
            self.assertEqual(c.view['scope'], 'system')
            self.assertIn('system', c.view['existingNotice'])
            self.assertTrue(c.view['hasFile'])
            self.assertFalse(any(x.startswith('MUTATE') for x in self.drivers[0].log))

    def test_invalid_file_has_no_file_reselection(self):
        c = self.controller()
        c.loadFile('/missing.flatpakref')
        self.assertEqual(c.view['phase'], 'error')
        self.assertTrue(c.view['hasFile'])
        self.assertEqual(c.view['source'], '')
        c.loadFile('/another.flatpakref')
        self.assertEqual(c.view['phase'], 'error')

    def test_demo_cannot_create_driver_or_install_or_launch(self):
        def forbidden(): self.fail('demo criou backend')
        c = Controller('success', driver_factory=forbidden)
        c.reference = REFERENCE
        c.install()
        c.respond(True, 0)
        c.launch()
        c.loadFile('/nonexistent.flatpakref')
        self.assertIsNone(c.worker)
        self.assertTrue(c.view['demo'])

    def test_new_install_defaults_to_user(self):
        c = self.controller()
        self.assertEqual(c.view['scope'], 'user')
        c.selectDestination('invalid')
        self.assertEqual(c.view['scope'], 'user')
        c.install()
        self.wait_for(lambda: not c.view['busy'])
        self.assertEqual(self.drivers[0].scope, 'user')
