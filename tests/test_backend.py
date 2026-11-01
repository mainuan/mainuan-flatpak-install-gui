import sys
import threading
import unittest
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from backend import Installer, Decisions, OriginConflict
from metadata import parse_reference, RemoteSpec

REFERENCE = parse_reference(b'[Flatpak Ref]\nName=org.example.App\nUrl=https://example.org/repo\nGPGKey=a2V5\n')
OPS = [{'type': 'install', 'ref': 'app/org.example.App/x86_64/master',
        'remote': 'example', 'url': 'https://example.org/repo', 'commit': '123', 'download': 7, 'installedSize': 9}]


class FakeDriver:
    def __init__(self, installed=False, existing=False, fail=None, changed=False, candidates=None, locations=None):
        self.installed, self.existing, self.fail, self.changed = installed, existing, fail, changed
        self.candidates = candidates
        self.locations = locations or []
        self.log, self.scope = [], None
        self.cancelled, self.ops = False, OPS
        self.added = {}

    def prepare(self, reference, scope): self.scope = scope; self.log.append('prepare:' + scope)
    def inventory(self, reference): return 'user e system'
    def installed_locations(self, reference): return self.locations
    def is_installed(self, reference): return self.installed
    def remote_candidates(self, spec):
        if self.fail == 'conflict': raise OriginConflict('Chave incompatível')
        if spec.url in self.added: return [self.added[spec.url]]
        return self.candidates if self.candidates is not None else ['example'] if self.existing else []
    def remote_description(self, name): return name + ' — https://example.org/repo'
    def dependency_candidates(self, names): return list(names)
    def merge_descriptors(self, first, second): return first
    def add_remote(self, spec):
        self.log.append('MUTATE:remote:' + spec.url)
        name = spec.suggested
        self.added[spec.url] = name
        return name
    def fetch_runtime(self, url):
        self.log.append('fetch:runtime')
        return RemoteSpec('https://runtime.example.org', 'runtime', 'Runtime', b'key')
    def transaction(self, reference, remote, policy): self.policy = policy; return self
    def operations(self, tx): return self.ops
    def validate_operations(self, ops, reference, remote):
        self.log.append('validate')
        if self.fail == 'changed-origin': raise OriginConflict('Origem alterada')
    def run(self, tx):
        self.log.append('resolve')
        if self.fail == 'network': raise OSError('offline')
        if not self.policy.guarded(False, self.policy.ready, self, True): raise RuntimeError('aborted')
        if self.changed: self.ops = [{**OPS[0], 'commit': 'changed'}]
        if not self.policy.guarded(False, self.policy.ready, self): raise RuntimeError('aborted')
        self.log.append('MUTATE:install')
        self.policy.progress(OPS[0]['ref'], 'Baixando', 42)
        if self.fail == 'operation':
            self.policy.operation_error(OPS[0]['ref'], 'authentication denied')
            raise RuntimeError('operation failed')
        if self.fail == 'cancel':
            self.policy.decisions.cancel()
            raise RuntimeError('cancelled')
        self.log.append('run:success')
    def verify(self, reference):
        self.log.append('verify:' + self.scope)
        if self.fail == 'verify': raise RuntimeError('not installed')
        return {'scope': self.scope, 'ref': OPS[0]['ref'], 'origin': 'example', 'name': reference.app_id, 'arch': 'x86_64', 'branch': reference.branch}
    def launch(self, installed): self.log.append('launch:' + installed['scope'] + ':' + installed['ref'])
    def remove(self, installed):
        self.log.append('remove:' + installed['scope'] + ':' + installed['ref'])
        if self.fail == 'remove': raise RuntimeError('denied')
        self.locations = [r for r in self.locations if r != installed]
    def cancel(self): self.cancelled = True
    def is_cancelled(self, exc): return False
    def error_message(self, exc): return str(exc) if isinstance(exc, OriginConflict) else 'Falhou'


class BackendTests(unittest.TestCase):
    def exercise(self, driver=None, answers=None, reference=REFERENCE, scope='user'):
        driver = driver or FakeDriver()
        decisions, events = Decisions(), []
        answers = iter(answers if answers is not None else [True] * 10)
        def emit(event):
            events.append(event)
            driver.log.append('event:' + event['event'])
            if 'token' in event:
                value = next(answers)
                driver.log.append('consent:' + event['event'] + ':' + str(value))
                self.assertTrue(decisions.answer(event['token'], value))
                self.assertFalse(decisions.answer(event['token'], value))
        Installer(driver, decisions, emit).run(reference, scope)
        return driver, events

    def test_one_click_existing_origin_has_no_intermediate_confirmation(self):
        for scope in ('user', 'system'):
            d, events = self.exercise(FakeDriver(existing=True), scope=scope, answers=[])
            self.assertFalse(any('token' in e for e in events))
            self.assertEqual(events[-1]['event'], 'success')
            self.assertEqual(events[-1]['installed']['scope'], scope)
            self.assertEqual(d.log.count('MUTATE:install'), 1)
            self.assertEqual(d.log.count('validate'), 2)
            self.assertLess(d.log.index('run:success'), d.log.index('verify:' + scope))
            self.assertEqual([e['percent'] for e in events if e['event'] == 'progress'], [42])

    def test_new_origin_covered_by_install_click(self):
        d, events = self.exercise(answers=[])
        self.assertFalse(any('token' in e for e in events))
        self.assertIn('MUTATE:remote:https://example.org/repo', d.log)
        self.assertTrue(any(e['event'] == 'remoteAdded' for e in events))
        self.assertEqual(events[-1]['event'], 'success')

    def test_unsigned_origin_blocked(self):
        ref = replace(REFERENCE, remote=replace(REFERENCE.remote, key=b''))
        d, events = self.exercise(reference=ref)
        self.assertEqual(events[-1]['event'], 'error')
        self.assertFalse(any(x.startswith('MUTATE') for x in d.log))

    def test_known_runtime_origins_authorized_by_click(self):
        ref = replace(REFERENCE, runtime_repo='https://runtime.example.org/repo.flatpakrepo')
        d, events = self.exercise(reference=ref, answers=[])
        self.assertFalse(any('token' in e for e in events))
        self.assertEqual(len([x for x in d.log if x.startswith('MUTATE:remote')]), 2)
        self.assertLess(d.log.index('fetch:runtime'), d.log.index('MUTATE:remote:https://example.org/repo'))

    def test_same_origin_from_two_descriptors_added_once(self):
        d = FakeDriver()
        d.fetch_runtime = lambda url: replace(REFERENCE.remote, title='Runtime', descriptor=url)
        d, events = self.exercise(d, reference=replace(REFERENCE, runtime_repo='https://example.org/runtime'))
        self.assertEqual(len([x for x in d.log if x.startswith('MUTATE:remote')]), 1)

    def test_late_origin_bound_to_request(self):
        p = Installer(FakeDriver(), Decisions(), lambda e: None)
        p.reference = REFERENCE
        p.allowed_specs = {REFERENCE.remote.url: REFERENCE.remote}
        self.assertTrue(p.new_remote(1, REFERENCE.app_id, 'example', REFERENCE.remote.url))
        for app, url in [('org.other.App', REFERENCE.remote.url), (REFERENCE.app_id, 'https://extra.example.org')]:
            with self.assertRaises(OriginConflict):
                p.new_remote(1, app, 'extra', url)

    def test_conflicting_origin_fails_without_mutations(self):
        d, events = self.exercise(FakeDriver(fail='conflict'))
        self.assertEqual(events[-1]['event'], 'error')
        self.assertIn('incompatível', events[-1]['message'])
        self.assertFalse(any(x.startswith('MUTATE') for x in d.log))

    def test_ambiguous_origins_require_explicit_selection(self):
        d, events = self.exercise(FakeDriver(candidates=['one', 'two']), answers=[1])
        self.assertEqual([e['event'] for e in events if 'token' in e], ['chooseRemote'])
        self.assertEqual(events[-1]['event'], 'success')
        d, events = self.exercise(FakeDriver(candidates=['one', 'two']), answers=[False])
        self.assertEqual(events[-1]['event'], 'cancelled')
        self.assertNotIn('MUTATE:install', d.log)

    def test_single_dependency_origin_does_not_ask(self):
        p = Installer(FakeDriver(), Decisions(), lambda e: self.fail('unnecessary prompt'))
        self.assertEqual(p.choose_remote('runtime/id/x86_64/stable', ['one']), 0)

    def test_changed_dependency_commits_revalidated_without_second_confirmation(self):
        d, events = self.exercise(FakeDriver(existing=True, changed=True), answers=[])
        self.assertEqual(d.log.count('validate'), 2)
        self.assertEqual(events[-1]['event'], 'success')
        self.assertFalse(any('token' in e for e in events))

    def test_origin_change_at_ready_is_vetoed(self):
        d, events = self.exercise(FakeDriver(existing=True, fail='changed-origin'))
        self.assertEqual(events[-1]['event'], 'error')
        self.assertNotIn('MUTATE:install', d.log)

    def test_failures_and_no_false_success(self):
        for failure in ('network', 'operation', 'verify'):
            d, events = self.exercise(FakeDriver(existing=True, fail=failure))
            self.assertEqual(events[-1]['event'], 'error')
            self.assertFalse(any(e['event'] == 'success' for e in events))

    def test_cancel_and_existing_app(self):
        d, events = self.exercise(FakeDriver(existing=True, fail='cancel'))
        self.assertEqual(events[-1]['event'], 'cancelled')
        d, events = self.exercise(FakeDriver(installed=True))
        self.assertFalse(any(x.startswith('MUTATE') for x in d.log))
        self.assertEqual(events[-1]['event'], 'success')

    def test_other_destination_does_not_create_duplicate_automatically(self):
        d = FakeDriver(existing=True, locations=[{'scope': 'system', 'ref': OPS[0]['ref']}])
        d, events = self.exercise(d, answers=[False])
        self.assertEqual([e['event'] for e in events if 'token' in e], ['confirmDuplicate'])
        self.assertEqual(events[-1]['event'], 'cancelled')
        self.assertNotIn('MUTATE:install', d.log)

    def test_cancel_wakes_waiting_decision(self):
        decisions, entered, events = Decisions(), threading.Event(), []
        d = FakeDriver(candidates=['one', 'two'])
        def emit(e):
            events.append(e)
            if 'token' in e: entered.set()
        worker = threading.Thread(target=Installer(d, decisions, emit).run, args=(REFERENCE, 'user'))
        worker.start()
        self.assertTrue(entered.wait(2))
        decisions.cancel()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(events[-1]['event'], 'cancelled')
        self.assertFalse(any(x.startswith('MUTATE') for x in d.log))
        self.assertFalse(decisions.answer(999, True))
