"""Qt/QML workflow tests with simulated transactions; never imports libflatpak."""
import argparse
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from PyQt6.QtCore import QObject, QMetaObject, Qt, QUrl, QPointF, qInstallMessageHandler
from PyQt6.QtGui import QPalette, QColor, QIcon
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine, QQmlExpression, QQmlEngine
from PyQt6.QtTest import QTest
from PyQt6 import QtQuick, sip
from controller import Controller
from test_backend import FakeDriver, REFERENCE

parser = argparse.ArgumentParser()
parser.add_argument('--dark', action='store_true')
parser.add_argument('--output', default='test-artifacts/flow')
args = parser.parse_args()
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)
errors = []
def message(kind, context, text):
    print(text, file=sys.stderr)
    if 'file:' in text or 'Error:' in text or 'binding loop' in text.lower(): errors.append(text)
qInstallMessageHandler(message)
app = QApplication([])
app.setApplicationName('mainuan-flatpak-install-gui')
QIcon.setThemeName('breeze')
palette = QPalette()
for role, light, dark in ((QPalette.ColorRole.Window, '#ffffff', '#242a33'),
                          (QPalette.ColorRole.WindowText, '#20252d', '#f1f4f8'),
                          (QPalette.ColorRole.Text, '#20252d', '#f1f4f8'),
                          (QPalette.ColorRole.ButtonText, '#20252d', '#f1f4f8'),
                          (QPalette.ColorRole.Base, '#f7f8fa', '#2d3440'),
                          (QPalette.ColorRole.Button, '#f7f8fa', '#2d3440'),
                          (QPalette.ColorRole.Highlight, '#3daee9', '#3daee9')):
    palette.setColor(role, QColor(dark if args.dark else light))
app.setPalette(palette)

def wait_for(predicate):
    deadline = time.monotonic() + 3
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.005)
    assert predicate()

def create(path=None, existing=True, candidates=None, fail=None, override=None):
    drivers = []
    def factory():
        driver = FakeDriver(existing=existing, candidates=candidates, fail=fail)
        drivers.append(driver)
        return driver
    controller = Controller(driver_factory=factory)
    controller.override_name = override
    if path is not None: controller.loadFile(str(path))  # Same entry path used by main.py.
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', controller)
    engine.load(str(Path(__file__).resolve().parents[1] / 'qt/Main.qml'))
    assert engine.rootObjects()
    window = engine.rootObjects()[0]
    window.resize(640, 480)
    wait_for(lambda: not controller.view['busy'])
    return controller, engine, window, drivers

def find(window, name):
    obj = window.findChild(QObject, name)
    assert obj is not None, name
    return obj

def click(window, name):
    button = find(window, name)
    assert button.property('visible') and button.property('enabled'), name
    QMetaObject.invokeMethod(button, 'clicked')

def capture(window, name):
    QTest.qWait(150)
    assert window.grabWindow().save(str(output / (name + '.png')))
    for object_name in ('installButton', 'closeButton', 'confirmButton', 'openButton', 'removeButton', 'confirmRemoveButton'):
        item = find(window, object_name)
        if item.property('visible'):
            pos = item.mapToScene(QPointF(0, 0))
            assert pos.x() >= 0 and pos.y() >= 0
            assert pos.x() + item.width() <= 640.5
            assert pos.y() + item.height() <= 480.5

def destroy(controller, engine, window):
    window.close()
    if controller.view['busy']:
        wait_for(lambda: not controller.view['busy'])
    sip.delete(engine)

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'aplicativo # com espaços.flatpakref'
    path.write_bytes(REFERENCE.raw.replace(b'Name=', b'Title=<b>Exemplo & 100%</b>\nName='))
    c, e, w, drivers = create(path)
    assert not find(w, 'chooseFileButton').property('visible')
    assert not find(w, 'filePicker').property('visible')
    assert find(w, 'userDestination').property('text') == 'Apenas seu usuário'
    assert find(w, 'systemDestination').property('text') == 'Todo o sistema'
    assert find(w, 'userDestination').property('visible') and find(w, 'systemDestination').property('visible')
    assert find(w, 'userDestination').property('checked')
    assert not find(w, 'detailsPanel').property('visible')
    assert find(w, 'closeButton').property('text') == 'Fechar'
    title = find(w, 'installationTitle')
    assert title.property('text') == '<b>Exemplo & 100%</b>'
    expr = QQmlExpression(QQmlEngine.contextForObject(title), title, 'textFormat === 0')
    assert expr.evaluate()[0]
    capture(w, 'ready')
    # Select both destinations with the keyboard and keep focus on that option.
    user = find(w, 'userDestination')
    user.forceActiveFocus()
    QTest.keyClick(w, Qt.Key.Key_Tab)
    assert find(w, 'systemDestination').property('activeFocus')
    QTest.keyClick(w, Qt.Key.Key_Space)
    assert c.view['scope'] == 'system'
    wait_for(lambda: not c.view['busy'])
    find(w, 'systemDestination').forceActiveFocus()
    QTest.keyClick(w, Qt.Key.Key_Backtab)
    QTest.keyClick(w, Qt.Key.Key_Space)
    assert c.view['scope'] == 'user'
    wait_for(lambda: not c.view['busy'])
    find(w, 'installButton').forceActiveFocus()
    QTest.keyClick(w, Qt.Key.Key_Space)
    c.install()  # A second click cannot start a duplicate transaction.
    wait_for(lambda: c.view['phase'] == 'success' and not c.view['busy'])
    assert not find(w, 'confirmButton').property('visible')
    assert sum(d.log.count('MUTATE:install') for d in drivers) == 1
    assert c.view['installed']['scope'] == 'user'
    assert c.view['operations']
    assert find(w, 'openButton').property('visible')
    assert find(w, 'closeButton').property('text') == 'Fechar'
    capture(w, 'success')
    destroy(c, e, w)

    c, e, w, drivers = create()
    assert find(w, 'chooseFileButton').property('visible')
    click(w, 'chooseFileButton')
    picker = find(w, 'filePicker')
    wait_for(lambda: picker.property('visible'))
    picker.setProperty('selectedFile', QUrl.fromLocalFile(str(path)))
    QMetaObject.invokeMethod(picker, 'accepted')
    QMetaObject.invokeMethod(picker, 'close')
    wait_for(lambda: c.view['phase'] == 'ready' and not c.view['busy'])
    assert not find(w, 'chooseFileButton').property('visible')
    destroy(c, e, w)

    c, e, w, drivers = create(Path(directory) / 'invalid.flatpakref')
    assert c.view['phase'] == 'error'
    assert not find(w, 'chooseFileButton').property('visible')
    assert not find(w, 'installButton').property('visible')
    assert find(w, 'closeButton').property('text') == 'Fechar'
    capture(w, 'invalid')
    destroy(c, e, w)

    c, e, w, drivers = create(path, existing=False)
    click(w, 'installButton')
    wait_for(lambda: c.view['phase'] == 'success' and not c.view['busy'])
    assert not find(w, 'confirmButton').property('visible')
    assert any(x.startswith('MUTATE:remote') for d in drivers for x in d.log)
    capture(w, 'new-origin')
    click(w, 'removeButton')
    assert c.view['phase'] == 'confirmRemove'
    capture(w, 'confirm-remove')
    click(w, 'confirmRemoveButton')
    wait_for(lambda: c.view['phase'] == 'ready' and not c.view['busy'])
    assert find(w, 'installButton').property('visible')
    capture(w, 'removed')
    destroy(c, e, w)

    c, e, w, drivers = create(path, candidates=['one', 'two'])
    click(w, 'installButton')
    wait_for(lambda: c.view['phase'] == 'chooseRemote')
    assert w.property('selectedOrigin') == -1
    assert 'Selecione' in find(w, 'ambiguousOriginChoice').property('displayText')
    assert not find(w, 'confirmButton').property('enabled')
    capture(w, 'ambiguous')
    find(w, 'ambiguousOriginChoice').forceActiveFocus()
    QTest.keyClick(w, Qt.Key.Key_End)
    assert w.property('selectedOrigin') == 1
    click(w, 'confirmButton')
    wait_for(lambda: c.view['phase'] == 'success' and not c.view['busy'])
    destroy(c, e, w)

    c, e, w, drivers = create(path, fail='network')
    click(w, 'installButton')
    wait_for(lambda: c.view['phase'] == 'error' and not c.view['busy'])
    capture(w, 'error')
    destroy(c, e, w)
    # Exact VM regression, offline fallback and a single presentation name in QML.
    path = Path(directory) / 'Scribe.flatpakref'
    path.write_bytes(b'[Flatpak Ref]\nName=io.github.gnacho.Scribe\nBranch=stable\nTitle=io.github.gnacho.Scribe from flathub\nUrl=https://dl.flathub.org/repo/\n')
    c, e, w, drivers = create(path)
    assert find(w, 'installationTitle').property('text') == 'Scribe'
    assert c.reference.app_id == 'io.github.gnacho.Scribe'
    assert c.reference.branch == 'stable'
    assert 'dl.flathub.org' in find(w, 'installationSource').property('text')
    capture(w, 'scribe-ready')
    c.on_event({'event': 'progress', 'message': 'Baixando', 'operation': 'app/io.github.gnacho.Scribe/x86_64/stable', 'percent': 42})
    assert find(w, 'installationTitle').property('text') == 'Instalando Scribe'
    capture(w, 'scribe-progress')
    c.install()
    wait_for(lambda: c.view['phase'] == 'success' and not c.view['busy'])
    assert find(w, 'installationTitle').property('text') == 'Scribe'
    capture(w, 'scribe-success')
    click(w, 'removeButton')
    assert c.view['phase'] == 'confirmRemove'
    assert c.view['notice'].startswith('Desinstalar Scribe (')
    assert find(w, 'installationTitle').property('text') == 'Scribe'
    capture(w, 'scribe-remove')
    destroy(c, e, w)

    override = '<b>Nome & literal</b> $(sem execução)'
    c, e, w, drivers = create(path, override=override)
    assert find(w, 'installationTitle').property('text') == override
    title = find(w, 'installationTitle')
    assert QQmlExpression(QQmlEngine.contextForObject(title), title, 'textFormat === 0').evaluate()[0]
    assert c.reference.app_id == 'io.github.gnacho.Scribe'
    assert c.reference.branch == 'stable'
    click(w, 'installButton')
    wait_for(lambda: c.view['phase'] == 'success' and not c.view['busy'])
    assert c.view['name'] == override
    assert c.view['installed']['name'] == 'io.github.gnacho.Scribe'
    click(w, 'removeButton')
    assert c.view['notice'].startswith('Desinstalar ' + override)
    notice = find(w, 'originNotice')
    assert QQmlExpression(QQmlEngine.contextForObject(notice), notice, 'textFormat === 0').evaluate()[0]
    capture(w, 'override-plaintext')
    destroy(c, e, w)

assert 'flatpak_backend' not in sys.modules
assert not errors, errors
print('QML FLOW OK: seleção; destinos/teclado; instalação sem confirmação extra; origens ambíguas; remoção confirmada; erro; 640×480.')
