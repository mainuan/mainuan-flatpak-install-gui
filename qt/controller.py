"""Qt state, one-click install intent and worker lifetime management."""
from PyQt6.QtCore import QObject, QThread, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from backend import Cancelled, Decisions, Installer
from metadata import read_reference, friendly_name


class Worker(QThread):
    event = pyqtSignal(dict)

    def __init__(self, reference=None, scope=None, installed=None, driver_factory=None, inspect=False, remove=False):
        super().__init__()
        self.reference, self.scope, self.installed = reference, scope, installed
        self.inspect = inspect
        self.remove = remove
        self.decisions = Decisions()
        self.driver = None
        self.driver_factory = driver_factory

    def cancel(self):
        self.decisions.cancel()
        if self.driver:
            self.driver.cancel()

    def presentation(self):
        try:
            if hasattr(self.driver, 'presentation'):
                result = self.driver.presentation(self.reference)
            else:
                result = {'name': self.driver.presentation_name(self.reference), 'description': ''}
            return {'name': friendly_name(self.reference.app_id, self.reference.title, result.get('name', '')),
                    'description': result.get('description', '')}
        except Exception:
            return {'name': self.reference.display_name, 'description': ''}

    def refresh_locations(self):
        if not self.reference:
            return
        self.driver.prepare(self.reference, self.scope)
        self.event.emit({'event': 'refreshed', 'locations': self.driver.installed_locations(self.reference),
                         **self.presentation()})

    def run(self):
        try:
            if self.driver_factory is None:
                from flatpak_backend import FlatpakDriver
                factory = FlatpakDriver
            else:
                factory = self.driver_factory
            self.driver = factory()
            self.decisions.check()
            if self.inspect:
                self.driver.prepare(self.reference, self.scope or 'user')
                locations = self.driver.installed_locations(self.reference)
                presentation = self.presentation()
                self.decisions.check()
                self.event.emit({'event': 'inspected', 'locations': locations,
                                 **presentation,
                                 'systems': self.driver.system_scopes() if hasattr(self.driver, 'system_scopes') else []})
            elif self.remove:
                self.driver.remove(self.installed)
                self.decisions.check()
                self.event.emit({'event': 'removed'})
                self.refresh_locations()
            elif self.installed:
                self.driver.launch(self.installed)
                self.decisions.check()
                self.event.emit({'event': 'launched'})
            else:
                Installer(self.driver, self.decisions, self.event.emit).run(self.reference, self.scope)
                if not self.decisions.cancelled:
                    self.refresh_locations()
        except Exception as exc:
            cancelled = (isinstance(exc, Cancelled) or self.decisions.cancelled
                         or self.driver is not None and self.driver.is_cancelled(exc))
            self.event.emit({'event': 'cancelled' if cancelled else 'error',
                             'message': 'Operação cancelada.' if cancelled else
                             self.driver.error_message(exc) if self.driver else 'Não foi possível consultar a instalação.', 'details': str(exc)})


class Controller(QObject):
    changed = pyqtSignal()
    safeToClose = pyqtSignal()

    def __init__(self, demo=None, driver_factory=None):
        super().__init__()
        self.reference = None
        self.worker = None
        self.driver_factory = driver_factory
        self.closing = False
        self.locations = []
        self.pending_remove = False
        self.override_name = None
        self._view = {'phase': 'empty', 'busy': False, 'started': False, 'hasFile': False,
                      'description': '', 'demo': bool(demo), 'name': 'Boas-vindas', 'iconName': 'system-software-install',
                      'id': '', 'source': '', 'runtimeRepo': '', 'scope': 'user', 'details': '',
                      'message': 'Escolha um arquivo .flatpakref para instalar.', 'inventory': '',
                      'operations': '', 'notice': '', 'choices': [], 'token': 0, 'existingNotice': '',
                      'percent': -1, 'operation': '', 'operationStatus': '', 'installed': {}, 'systemScopes': []}
        if demo:
            from demo import demo_state
            self._view.update(demo_state(demo))

    @pyqtProperty('QVariantMap', notify=changed)
    def view(self):
        return self._view.copy()

    def update(self, **values):
        self._view.update(values)
        self.changed.emit()

    def start_worker(self, **kwargs):
        self.worker = Worker(driver_factory=self.driver_factory, **kwargs)
        self.worker.event.connect(self.on_event)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    @pyqtSlot(QUrl)
    def loadUrl(self, url):
        if url.isLocalFile():
            self.loadFile(url.toLocalFile())

    @pyqtSlot(str)
    def loadFile(self, path):
        if self._view['busy'] or self._view['demo'] or self._view['hasFile']:
            return
        self.update(hasFile=True)
        try:
            reference = read_reference(path)
            self.reference = reference
            icon = 'system-software-install'
            from PyQt6.QtGui import QGuiApplication, QIcon
            if isinstance(QGuiApplication.instance(), QGuiApplication):
                for name in (reference.icon_name, reference.app_id):
                    if name and QIcon.hasThemeIcon(name):
                        icon = name
                        break
            self.update(phase='checking', **{**reference.info, 'name': self.override_name or reference.display_name}, iconName=icon, scope=self._view['scope'], busy=True,
                        message='Verificando instalação…', details='', operations='', installed={}, token=0)
            self.start_worker(reference=reference, scope=self._view['scope'], inspect=True)
        except (OSError, ValueError) as exc:
            self.reference = None
            self.update(phase='error', name='Arquivo inválido', id='', source='', runtimeRepo='',
                        message='Não foi possível abrir este arquivo .flatpakref.', details=str(exc), installed={})

    @pyqtSlot(str)
    def selectDestination(self, scope):
        if self._view['demo'] or self.closing:
            return
        if (scope in ('user', 'system') or scope.startswith('system:')) and not self._view['busy']:
            self.update(scope=scope, started=False)
            if self.reference and self._view['hasFile']:
                self.update(busy=True, phase='checking', installed={}, message='Verificando instalação…')
                self.start_worker(reference=self.reference, scope=scope, inspect=True)

    @pyqtSlot()
    def install(self):
        if self._view['busy'] or self._view['demo'] or not self.reference:
            return
        scope = self._view['scope']
        if scope not in ('user', 'system') and not scope.startswith('system:'):
            return
        self.update(busy=True, started=True, phase='resolving', message='Preparando instalação…',
                    details='', operations='', notice='', percent=-1, installed={}, token=0)
        self.start_worker(reference=self.reference, scope=scope)

    def on_event(self, event):
        kind = event['event']
        if kind == 'refreshed':
            self.locations = event['locations']
            self.update(name=self.override_name or event.get('name', self._view['name']),
                        description=event.get('description', self._view['description']),
                        existingNotice='; '.join(f"{r['scope']}: {r['ref']}" for r in self.locations))
        elif kind == 'inspected':
            self.update(systemScopes=event.get('systems', []))
            self.locations = event['locations']
            matches = [r for r in self.locations if r['scope'] == self._view['scope'] and r.get('selected', True)]
            notice = '; '.join(f"{r['scope']}: {r['ref']}" for r in self.locations)
            if len(matches) > 1:
                self.update(phase='error', message='Há referências ambíguas no destino. Selecione uma referência exata.', installed={})
            else:
                self.update(phase='success' if matches else 'ready', started=False,
                            installed=matches[0] if matches else {},
                            name=self.override_name or event.get('name', self.reference.display_name),
                            description=event.get('description', ''),
                            existingNotice=('Instalações encontradas: ' + notice if notice else ''),
                            message='Já instalado' if matches else '',
                            details=notice)
        elif kind == 'remoteAdded':
            self.update(details=self._view['details'] + '\n' + event['message'])
        elif kind == 'removed':
            self.update(phase='ready', started=False, installed={}, message='Aplicativo desinstalado. Dados pessoais preservados.')
        elif kind == 'inventory':
            self.update(inventory=event['message'])
        elif kind in ('confirmRemote', 'chooseRemote', 'confirmDuplicate'):
            if self.closing:
                self.worker.cancel()
                return
            self.update(phase=kind, token=event['token'], notice=event.get('notice', ''),
                        choices=event.get('choices', []), message='',
                        details=self._view['details'] + '\n' + event.get('details', ''))
        elif kind == 'operations':
            labels = {'install': 'Instalar', 'update': 'Atualizar', 'uninstall': 'Remover'}
            self.update(operations='\n\n'.join(
                f'{labels.get(op["type"], op["type"])} {op["ref"]}\n'
                f'Origem: {op["remote"]} — {op["url"]}\n'
                f'Download: {op["download"]:,} bytes; espaço instalado: {op["installedSize"]:,} bytes'
                for op in event['operations']) or 'Nenhuma operação pendente.')
        elif kind == 'progress':
            self.update(phase='installing', message='Instalando…', operationStatus=event['message'],
                        operation=event['operation'], percent=event['percent'])
        elif kind in ('success', 'error', 'cancelled'):
            self.update(phase=kind, token=0, percent=-1, message=event['message'],
                        details=self._view['details'] + '\n' + event.get('details', ''),
                        installed=event.get('installed', {}) if kind == 'success' else self._view['installed'])
        elif kind == 'launched':
            self.update(phase='success', message='Aplicativo aberto.')
        else:
            self.update(phase=kind, message='Preparando instalação…' if kind == 'resolving'
                        else event.get('message', ''), token=0)

    def finished(self):
        if self._view['phase'] == 'checking':
            self.update(phase='ready', message='')
        self.update(busy=False, token=0)
        if self.closing:
            self.safeToClose.emit()
        elif self.pending_remove:
            self.pending_remove = False
            self.requestRemove()

    @pyqtSlot(bool, int)
    def respond(self, accepted, choice=0):
        if self._view['demo']:
            return
        token = self._view['token']
        if not self.worker or not token or not self._view['busy']:
            return
        value = choice if self._view['phase'] == 'chooseRemote' and accepted else accepted
        if self.worker.decisions.answer(token, value):
            self.update(token=0, phase='resolving', message='Preparando instalação…')

    @pyqtSlot()
    def cancel(self):
        if self.worker and self._view['busy']:
            self.worker.cancel()
            self.update(phase='cancelling', token=0, message='Cancelando… Aguarde a conclusão segura.')

    @pyqtSlot(result=bool)
    def requestClose(self):
        if self._view['busy']:
            self.closing = True
            self.cancel()
            return False
        return True

    def shutdown(self):
        """Final process exit must not destroy a still-running QThread."""
        self.closing = True
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()  # Cooperative cancellation, never terminate().

    @pyqtSlot()
    def requestRemove(self):
        if self._view['demo'] or self._view['busy'] or not self._view['installed']:
            return
        self.update(phase='confirmRemove', notice=f"Desinstalar {self._view['name']} ({self._view['scope']})? Os dados pessoais serão preservados.")

    @pyqtSlot()
    def confirmRemove(self):
        if self._view['phase'] != 'confirmRemove' or self._view['busy'] or self._view['demo']:
            return
        self.update(busy=True, phase='removing', message='Desinstalando…')
        self.start_worker(reference=self.reference, scope=self._view['scope'], installed=dict(self._view['installed']), remove=True)

    @pyqtSlot()
    def launch(self):
        if self._view['demo'] or self._view['busy'] or not self._view['installed']:
            return
        self.update(busy=True, phase='launching', message='Abrindo o aplicativo…')
        self.start_worker(installed=self._view['installed'])

    @pyqtSlot(str)
    def simulate(self, phase):
        if self._view['demo']:
            from demo import demo_state
            self.update(**demo_state(phase))
