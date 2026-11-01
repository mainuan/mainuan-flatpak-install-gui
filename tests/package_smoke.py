"""Inspect/exercise an extracted package in a disposable mount namespace.
No apt install, host files modified, real app transactions, or development PYTHONPATH.
Missing Qt/GI dependencies may be supplied as an extracted /usr tree for testing.
"""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

parser=argparse.ArgumentParser()
parser.add_argument('package',type=Path)
parser.add_argument('--dependency-root',type=Path)
args=parser.parse_args()
package=args.package.resolve()
with tempfile.TemporaryDirectory(prefix='mainuan-package-rc1-') as folder:
    root=Path(folder)/'root'
    subprocess.run(['dpkg-deb','-x',str(package),str(root)],check=True)
    subprocess.run(['dpkg-deb','-e',str(package),str(root/'DEBIAN')],check=True)
    active=root/'usr/share/mainuan-flatpak-install-gui'
    assert (active/'qt/Main.qml').read_bytes()==Path('qt/Main.qml').read_bytes()
    for path in root.rglob('*'):
        assert path.stat().st_mode & 0o022 == 0, path
    for name in ('mainuan-flatpak-install-gui','flatpak-install-gui'):
        assert os.access(root/'usr/bin'/name,os.X_OK)
    launcher=(root/'usr/bin/mainuan-flatpak-install-gui').read_text()
    assert 'exec /usr/bin/python3 /usr/share/mainuan-flatpak-install-gui/qt/main.py "$@"' in launcher
    assert 'local_main' not in launcher
    for path in (active/'qt').glob('*'):
        if path.suffix in ('.py','.qml'):
            text=path.read_text()
            for forbidden in ('/home/daigo','/tmp/mainuan-qt6-deps','PYTHONPATH','tiger-shell-osd','tiger-osd.sh','yad --'):
                assert forbidden not in text,(path,forbidden)
    subprocess.run(['desktop-file-validate',str(root/'usr/share/applications/mainuan-flatpak-install-gui.desktop')],check=True)
    # A private /usr/bin and /usr/share supply the exact installed paths. All
    # remaining host files are read-only and the process cannot access the network.
    command=['bwrap','--die-with-parent','--unshare-net','--ro-bind','/','/',
             '--tmpfs','/usr/bin','--tmpfs','/usr/share','--proc','/proc','--dev-bind','/dev','/dev']
    interpreter = Path('/usr/bin/python3').resolve().name
    for executable in (interpreter,'dash','readlink','dirname'):
        command+=['--ro-bind','/usr/bin/'+executable,'/usr/bin/'+executable]
    command+=['--symlink',interpreter,'/usr/bin/python3','--symlink','dash','/usr/bin/sh']
    for path in Path('/usr/share').iterdir():
        if path.name!='mainuan-flatpak-install-gui':
            command+=['--ro-bind',str(path),str(path)]
    command+=['--ro-bind',str(active),'/usr/share/mainuan-flatpak-install-gui']
    for executable in ('mainuan-flatpak-install-gui','flatpak-install-gui'):
        command+=['--ro-bind',str(root/'usr/bin'/executable),'/usr/bin/'+executable]
    if args.dependency_root:
        # Overlay only missing module files at normal system locations.
        pyqt=Path('/usr/lib/python3/dist-packages/PyQt6')
        command+=['--tmpfs',str(pyqt)]
        files={p.name:p for p in pyqt.iterdir()}
        files.update({p.name:p for p in (args.dependency_root/'usr/lib/python3/dist-packages/PyQt6').iterdir()})
        for name,path in files.items(): command+=['--ro-bind',str(path.resolve()),str(pyqt/name)]
    command+=['--chdir','/']
    environment={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','GI_TYPELIB_PATH','QT_PLUGIN_PATH','QML_IMPORT_PATH','QML2_IMPORT_PATH')}
    environment.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_CONTROLS_STYLE='Basic')
    for executable in ('mainuan-flatpak-install-gui','flatpak-install-gui'):
        result=subprocess.run(command+['--','/usr/bin/'+executable,'--help'],env=environment,text=True,capture_output=True,check=True)
        assert 'Mainuan Instalador Flatpak' in result.stdout
        result=subprocess.run(command+['--','/usr/bin/'+executable,'--do-install','/never.flatpakref'],env=environment,text=True,capture_output=True)
        assert result.returncode==2 and 'descontinuados' in result.stderr
    # Drive the actual installed main/QML event loop, scheduling only test shutdown.
    harness='''
import sys, runpy
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication
original = QApplication.exec
errors=[]
def stop():
    windows=QGuiApplication.allWindows()
    if not any(w.title() == 'Mainuan Instalador Flatpak' for w in windows): errors.append('window title')
    if 'flatpak_backend' in sys.modules: errors.append('demo loaded backend')
    QApplication.quit()
def timed_exec():
    QTimer.singleShot(800, stop)
    return original()
QApplication.exec=staticmethod(timed_exec)
sys.path.insert(0, '/usr/share/mainuan-flatpak-install-gui/qt')
sys.argv=['mainuan-flatpak-install-gui','--demo','progress']
try:
    runpy.run_path('/usr/share/mainuan-flatpak-install-gui/qt/main.py',run_name='__main__')
except SystemExit as result:
    assert result.code==0, result.code
assert not errors,errors
print('Installed Qt demo: OK; no backend; no development paths')
'''
    subprocess.run(command+['--','/usr/bin/python3','-c',harness],env=environment,check=True)
    print('PACKAGE SMOKE OK:',package.name)
    print('SHA-256:',hashlib.sha256(package.read_bytes()).hexdigest())
