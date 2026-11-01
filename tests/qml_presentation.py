"""Compact presentation at native logical pixels and caller-selected Qt scaling."""
import argparse
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qt'))
from PyQt6.QtCore import QObject, QMetaObject, Qt, QPointF, qInstallMessageHandler
from PyQt6.QtGui import QPalette, QColor, QIcon
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtTest import QTest
from PyQt6 import QtQuick, sip
from controller import Controller
from test_backend import FakeDriver
from test_presentation import GIMP, XML, presentation

parser = argparse.ArgumentParser()
parser.add_argument('--dark', action='store_true')
parser.add_argument('--large-font', action='store_true')
parser.add_argument('--output', default='test-artifacts/dev5-presentation')
args = parser.parse_args()
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)
errors=[]
def message(kind, context, text):
    print(text, file=sys.stderr)
    if 'file:' in text or 'Error:' in text or 'binding loop' in text.lower(): errors.append(text)
qInstallMessageHandler(message)
app = QApplication([])
QIcon.setThemeName('breeze')
if args.large_font:
    font=app.font(); font.setPointSizeF(font.pointSizeF()*1.4); app.setFont(font)
palette = QPalette()
for role, light, dark in ((QPalette.ColorRole.Window,'#ffffff','#242a33'), (QPalette.ColorRole.WindowText,'#20252d','#f1f4f8'), (QPalette.ColorRole.Text,'#20252d','#f1f4f8'), (QPalette.ColorRole.ButtonText,'#20252d','#f1f4f8'), (QPalette.ColorRole.Base,'#f7f8fa','#2d3440'), (QPalette.ColorRole.Button,'#f7f8fa','#2d3440')):
    palette.setColor(role,QColor(dark if args.dark else light))
app.setPalette(palette)
def wait(predicate):
    end=time.monotonic()+4
    while not predicate() and time.monotonic()<end: app.processEvents(); time.sleep(.005)
    assert predicate()
def find(w,n):
    obj=w.findChild(QObject,n); assert obj is not None,n; return obj
def click(w,n):
    obj=find(w,n); assert obj.property('visible') and obj.property('enabled'),n
    QMetaObject.invokeMethod(obj,'clicked')
def capture(w,n):
    QTest.qWait(120)
    assert w.grabWindow().save(str(output/(n+'.png')))
    for name in ('installButton','closeButton','openButton','removeButton'):
        item=find(w,name)
        if item.property('visible'):
            p=item.mapToScene(QPointF(0,0))
            assert p.x()>=0 and p.y()>=0,(name,p)
            assert p.x()+item.width()<=w.width()+.5,(name,w.width())
            assert p.y()+item.height()<=w.height()+.5,(name,w.height())

with tempfile.TemporaryDirectory() as folder:
    for appid,raw in [('gimp',GIMP.raw),('scribe',GIMP.raw.replace(b'org.gimp.GIMP',b'io.github.gnacho.Scribe'))]:
        class Driver(FakeDriver):
            def __init__(self): super().__init__(existing=True)
            def presentation(self,ref):
                if appid=='gimp': return presentation()
                return {'name':'Scribe','description':'Markdown editor with live rendering'}
        c=Controller(driver_factory=Driver)
        path=Path(folder)/'app.flatpakref'; path.write_bytes(raw)
        c.loadFile(str(path))
        engine=QQmlApplicationEngine(); engine.rootContext().setContextProperty('backend',c)
        engine.load(str(Path(__file__).resolve().parents[1]/'qt/Main.qml'))
        assert engine.rootObjects()
        w=engine.rootObjects()[0]
        wait(lambda:not c.view['busy'])
        QTest.qWait(100)
        expected='GIMP' if appid=='gimp' else 'Scribe'
        assert find(w,'installationTitle').property('text')==expected
        assert find(w,'applicationDescription').property('text')==c.view['description']
        assert find(w,'applicationDescription').property('visible')
        assert not find(w,'installationMessage').property('visible')
        assert not find(w,'detailsPanel').property('visible')
        assert not find(w,'installationSource').property('visible')
        assert w.width()<=520.5
        assert w.height()<400 or args.large_font
        capture(w,appid+'-compact')
        # Keyboard changes destination, then opens details with Space.
        find(w,'userDestination').forceActiveFocus()
        QTest.keyClick(w,Qt.Key.Key_Tab); QTest.keyClick(w,Qt.Key.Key_Space)
        wait(lambda:not c.view['busy'])
        assert c.view['scope']=='system'
        toggle=find(w,'detailsToggle'); toggle.forceActiveFocus(); QTest.qWait(80)
        scroll=find(w,'bodyScroll')
        pos=toggle.mapToItem(scroll, QPointF(0,0))
        assert pos.y()>=-.5 and pos.y()+toggle.height()<=scroll.height()+.5
        QTest.keyClick(w,Qt.Key.Key_Space)
        QTest.qWait(100)
        assert find(w,'detailsPanel').property('visible')
        source=find(w,'installationSource')
        assert source.property('visible')
        assert c.view['source'] in source.property('text')
        assert 'Será adicionada se necessária ao instalar' in source.property('text')
        capture(w,appid+'-details')
        click(w,'detailsToggle')
        QTest.qWait(100)
        with_description=w.height()
        c.update(description='')
        QTest.qWait(100)
        assert not find(w,'applicationDescription').property('visible')
        assert w.height()<=with_description
        capture(w,appid+'-no-description')
        c.update(description='Descrição longa para verificar quebra de linha e rolagem. '*50)
        QTest.qWait(100)
        body=find(w,'bodyScroll')
        assert body.property('contentHeight')>body.property('height')
        capture(w,appid+'-long-description')
        c.update(description='Resumo curto',installed={'scope':'system','ref':'app/'+c.reference.app_id+'/x86_64/stable'},phase='success',message='Já instalado')
        capture(w,appid+'-installed')
        w.resize(640,480)
        QTest.qWait(100)
        capture(w,appid+'-640x480')
        w.close(); sip.delete(engine)
assert not errors,errors
print('QML PRESENTATION OK:',args.output,'large-font=',args.large_font)
