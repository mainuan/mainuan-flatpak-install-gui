"""Operation-local installation authorization and validated origins."""
import threading
from metadata import https_url


class Cancelled(Exception):
    pass


class OriginConflict(ValueError):
    pass


class Decisions:
    def __init__(self):
        self.condition = threading.Condition()
        self.cancelled = False
        self.sequence = 0
        self.pending = None
        self.answer_value = None

    def ask(self, emit, kind, payload):
        with self.condition:
            self.check()
            self.sequence += 1
            token = self.sequence
            self.pending, self.answer_value = token, None
            emit({'event': kind, 'token': token, **payload})
            self.condition.wait_for(lambda: self.answer_value is not None or self.cancelled)
            answer = self.answer_value
            self.pending = None
            if self.cancelled or answer is False:
                raise Cancelled()
            return answer

    def answer(self, token, value):
        with self.condition:
            if token != self.pending or self.answer_value is not None or self.cancelled:
                return False
            self.answer_value = value
            self.condition.notify_all()
            return True

    def cancel(self):
        with self.condition:
            self.cancelled = True
            self.condition.notify_all()

    def check(self):
        if self.cancelled:
            raise Cancelled()


class Installer:
    def __init__(self, driver, decisions, emit):
        self.driver, self.decisions, self.emit = driver, decisions, emit
        self.operation_errors = []
        self.callback_error = None
        self.reference = None
        self.main_remote = None
        self.authorized_remotes = set()
        self.selected_remotes = {}
        self.allowed_specs = {}

    def ask(self, kind, **payload):
        return self.decisions.ask(self.emit, kind, payload)

    def remote_consent(self, specs):
        identity = lambda s: (s.url, s.key, s.collection, s.default_branch)
        pending = list({identity(s): s for s in specs if identity(s) not in self.authorized_remotes}.values())
        if not pending:
            return
        self.decisions.check()
        for spec in pending:
            https_url(spec.url)
            if not spec.key:
                raise OriginConflict('A origem necessária não fornece chave GPG. A instalação foi interrompida.')
        self.authorized_remotes.update(identity(s) for s in pending)

    def choose(self, ref, names, descriptions):
        if len(names) == 1:
            return names[0]
        if not names:
            raise OriginConflict('Nenhuma origem compatível está disponível.')
        cache_key = (ref, tuple(zip(names, descriptions)))
        if cache_key in self.selected_remotes:
            return self.selected_remotes[cache_key]
        choice = self.ask('chooseRemote', notice='Há mais de uma origem compatível. Escolha qual deseja usar.',
                          choices=descriptions, details=ref)
        if not 0 <= int(choice) < len(names):
            raise ValueError('Origem selecionada inválida.')
        name = names[int(choice)]
        self.selected_remotes[cache_key] = name
        return name

    def find_remote(self, spec):
        names = self.driver.remote_candidates(spec)
        return self.choose(spec.url, names, [self.driver.remote_description(n) for n in names]) if names else None

    def guarded(self, fallback, callback, *args):
        try:
            return callback(*args)
        except Exception as exc:
            self.callback_error = exc
            self.driver.cancel()
            return fallback

    def ready(self, transaction, pre_auth=False):
        self.decisions.check()
        # Revalidate identity/configuration at the actual libflatpak veto points.
        for spec in self.allowed_specs.values():
            if not self.driver.remote_candidates(spec):
                raise OriginConflict('A origem autorizada desapareceu durante a instalação.')
        ops = self.driver.operations(transaction)
        self.driver.validate_operations(ops, self.reference, self.main_remote)
        self.emit({'event': 'operations', 'operations': ops})
        self.decisions.check()
        if not pre_auth:
            self.emit({'event': 'installing', 'message': 'Instalando…'})
        return True

    def new_remote(self, reason, app_id, name, url):
        # Accept only dependency proposals bound to this request and a validated
        # descriptor. Unknown URLs cannot inherit the user's install authorization.
        https_url(url)
        if reason not in (0, 1) or not self.reference or app_id != self.reference.app_id:
            raise OriginConflict('Proposta de origem não vinculada ao aplicativo solicitado.')
        if url not in self.allowed_specs:
            raise OriginConflict('Origem de dependência sem descritor validado: ' + url)
        self.remote_consent([self.allowed_specs[url]])
        return True

    def choose_remote(self, ref, names):
        # Called only for dependency providers. Never substitute the app's origin.
        candidates = self.driver.dependency_candidates(names)
        selected = self.choose(ref, candidates, [self.driver.remote_description(n) for n in candidates])
        return list(names).index(selected)

    def progress(self, ref, status, percent):
        self.emit({'event': 'progress', 'operation': ref, 'message': status, 'percent': percent})

    def operation_error(self, ref, message):
        self.operation_errors.append(f'{ref}: {message}')
        return False

    def run(self, reference, scope):
        self.reference = reference
        try:
            self.decisions.check()
            self.driver.prepare(reference, scope)
            self.emit({'event': 'inventory', 'message': self.driver.inventory(reference)})
            locations = self.driver.installed_locations(reference)
            self.decisions.check()
            if self.driver.is_installed(reference):
                installed = self.driver.verify(reference)
                self.decisions.check()
                self.emit({'event': 'success', 'message': 'O aplicativo já está instalado neste destino.',
                           'installed': installed})
                return
            if locations:
                self.ask('confirmDuplicate', notice='Este aplicativo já está instalado. '
                         'Deseja instalar outra cópia no destino selecionado?',
                         details='\n'.join(f'{r["scope"]}: {r["ref"]}' for r in locations))
            # The Install click covers declared app/runtime origins. Resolve and
            # validate their descriptors before making any configuration changes.
            specs = [reference.remote]
            if reference.runtime_repo:
                specs.append(self.driver.fetch_runtime(reference.runtime_repo))
            combined = {}
            for spec in specs:
                combined[spec.url] = (self.driver.merge_descriptors(combined[spec.url], spec)
                                      if spec.url in combined else spec)
            self.allowed_specs = combined
            names = {url: self.find_remote(spec) for url, spec in combined.items()}
            self.remote_consent([combined[url] for url, name in names.items() if name is None])
            for url, name in names.items():
                self.decisions.check()
                spec = combined[url]
                if name is None:
                    existing = self.find_remote(spec)  # Recheck after waiting for the user.
                    name = existing or self.driver.add_remote(spec)
                    if not existing:
                        self.emit({'event': 'remoteAdded', 'message': f'Origem adicionada: {name} — {url}'})
                names[url] = name
            self.main_remote = names[reference.remote.url]
            self.decisions.check()
            tx = self.driver.transaction(reference, self.main_remote, self)
            self.driver.run(tx)
            if self.callback_error:
                raise self.callback_error
            if self.operation_errors:
                raise RuntimeError('\n'.join(self.operation_errors))
            self.decisions.check()
            installed = self.driver.verify(reference)
            self.decisions.check()
            self.emit({'event': 'success', 'message': 'Instalação concluída.', 'installed': installed})
        except Exception as exc:
            cause = self.callback_error or exc
            if isinstance(cause, Cancelled) or self.decisions.cancelled or self.driver.is_cancelled(cause):
                self.emit({'event': 'cancelled', 'message': 'Instalação cancelada. Alterações já concluídas podem permanecer.',
                           'details': str(exc)})
            else:
                self.emit({'event': 'error', 'message': self.driver.error_message(cause),
                           'details': str(cause) + ('\n' + '\n'.join(self.operation_errors) if self.operation_errors else '')})
