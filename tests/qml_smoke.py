"""Execute separately, on Wayland or offscreen. Never imports the real backend.
Captures states, palettes, and 640x480 layout; QT_SCALE_FACTOR is supplied by caller.
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from PyQt6.QtCore import QObject, QTimer, qInstallMessageHandler
from PyQt6.QtGui import QGuiApplication, QColor, QPalette, QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6 import QtQuick, sip
from controller import Controller
from demo import STATES

parser = argparse.ArgumentParser()
parser.add_argument('--output', default='test-artifacts')
parser.add_argument('--dark', action='store_true')
args = parser.parse_args()
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)
errors = []
def message(kind, context, text):
    print(text, file=sys.stderr)
    if 'file:' in text or 'Error:' in text or 'binding loop' in text.lower():
        errors.append(text)
qInstallMessageHandler(message)
app = QGuiApplication([])
app.setApplicationName('mainuan-flatpak-install-gui')
QIcon.setThemeName('breeze')
# Deterministic light/dark palette for the harness, without changing desktop settings.
palette = QPalette()
for role, light, dark in ((QPalette.ColorRole.Window, '#ffffff', '#242a33'),
                          (QPalette.ColorRole.WindowText, '#20252d', '#f1f4f8'),
                          (QPalette.ColorRole.Base, '#f7f8fa', '#2d3440'),
                          (QPalette.ColorRole.Text, '#20252d', '#f1f4f8'),
                          (QPalette.ColorRole.Button, '#f7f8fa', '#2d3440'),
                          (QPalette.ColorRole.ButtonText, '#20252d', '#f1f4f8'),
                          (QPalette.ColorRole.Highlight, '#3daee9', '#3daee9')):
    palette.setColor(role, QColor(dark if args.dark else light))
app.setPalette(palette)
controller = Controller('ready')
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty('backend', controller)
engine.load(str(Path(__file__).resolve().parents[1] / 'qt/Main.qml'))
if not engine.rootObjects():
    sys.exit(1)
window = engine.rootObjects()[0]
window.resize(640, 480)
phases = iter(STATES)
def capture():
    filename = output / (controller.view['phase'] + '.png')
    if not window.grabWindow().save(str(filename)):
        errors.append('Falha na captura de ' + str(filename))
    column = window.findChild(QObject, 'bodyColumn')
    if column.property('width') > 592.5:
        errors.append('Conteúdo maior que a largura disponível')
    advance()
def advance():
    try:
        controller.simulate(next(phases))
        QTimer.singleShot(250, capture)
    except StopIteration:
        app.quit()
QTimer.singleShot(300, advance)
app.exec()
sip.delete(engine)
assert 'flatpak_backend' not in sys.modules, 'Demonstração importou backend real'
if errors:
    raise SystemExit('\n'.join(errors))
print('QML OK: seis estados, 640×480; backend real ausente.')
