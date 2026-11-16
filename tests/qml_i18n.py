"""Load Main.qml as main.py does (same translators) and print visible texts as JSON.

Run by tests/test_i18n.py in a subprocess per language, offscreen; never imports
the real backend. The language comes only from the environment (LANGUAGE etc.).
"""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6 import QtQuick, sip  # noqa: F401
from controller import Controller
from i18n import _, install_qt_translators

if 'QML_I18N_QT_TRANSLATIONS' in os.environ:
    # Simulates a missing qtbase_<lang>.qm (e.g. Urdu, or qt6-translations-l10n absent).
    from unittest import mock
    from PyQt6.QtCore import QLibraryInfo
    mock.patch.object(QLibraryInfo, 'path', return_value=os.environ['QML_I18N_QT_TRANSLATIONS']).start()

app = QApplication(sys.argv[:1])
app.setApplicationName('mainuan-flatpak-install-gui')
translators = install_qt_translators(app)
app.setApplicationDisplayName(_('Mainuan Flatpak Installer'))
controller = Controller('ready')
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty('backend', controller)
engine.load(str(Path(__file__).resolve().parents[1] / 'qt/Main.qml'))
if not engine.rootObjects():
    sys.exit(1)
window = engine.rootObjects()[0]
result = {}


def collect():
    result['title'] = window.property('title')
    result['displayName'] = app.applicationDisplayName()
    result['layoutDirection'] = app.layoutDirection().name
    result['mirrored'] = window.findChild(QObject, 'installButton').property('mirrored')
    for name in ('installButton', 'closeButton', 'userDestination', 'systemDestination',
                 'detailsToggle', 'installationMessage', 'installationTitle', 'installationSource'):
        result[name] = window.findChild(QObject, name).property('text')
    controller.simulate('progress')
    QTimer.singleShot(50, finish)


def finish():
    result['progressMessage'] = window.findChild(QObject, 'installationMessage').property('text')
    app.quit()


QTimer.singleShot(100, collect)
app.exec()
sip.delete(engine)
assert 'flatpak_backend' not in sys.modules
print(json.dumps(result, ensure_ascii=False))
