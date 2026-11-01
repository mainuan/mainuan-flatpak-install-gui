#!/usr/bin/python3
"""Mainuan Instalador Flatpak — Qt 6 / Kirigami entry point."""
import argparse
import os
from pathlib import Path
import sys


def arguments(argv=None):
    parser = argparse.ArgumentParser(description='Mainuan Instalador Flatpak — arquivo .flatpakref local')
    parser.add_argument('reference', nargs='?', help='um arquivo .flatpakref local')
    parser.add_argument('--demo', nargs='?', const='ready', choices=['ready', 'remote', 'progress', 'success', 'error', 'cancelled'],
                        help='demonstração visual, incapaz de instalar')
    parser.add_argument('--override-appname', help='nome de apresentação em texto simples; não altera a identidade')
    parser.add_argument('--remove', action='store_true', help='remover a referência exata, com confirmação gráfica')
    parser.add_argument('--scope', help='user, system ou system:ID; obrigatório para --remove')
    parser.add_argument('--fetch-dependencies', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--do-install', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.fetch_dependencies or args.do_install:
        parser.error('--fetch-dependencies e --do-install foram descontinuados: eram auxiliares internos do Bash. '
                     'Abra um arquivo .flatpakref e use Instalar. Nenhuma operação foi executada.')
    if args.scope and args.scope not in ('user', 'system'):
        import re
        if not re.fullmatch(r'system:[A-Za-z0-9_.-]+', args.scope):
            parser.error('Destino inválido: use user, system ou system:ID.')
    if args.scope == 'system:default':
        args.scope = 'system'
    if args.remove and (not args.reference or not args.scope):
        parser.error('--remove exige arquivo .flatpakref e --scope user|system|system:ID; a identidade vem do arquivo.')
    if args.reference and Path(args.reference).suffix.lower() != '.flatpakref':
        parser.error('Forneça um arquivo .flatpakref local. IDs ou URLs avulsos do instalador antigo não são aceitos.')
    if args.demo and (args.reference or args.remove or args.override_appname is not None or args.scope):
        parser.error('--demo é isolado: não aceita arquivo, destino, remoção ou nome sobrescrito.')
    return args


def main():
    args = arguments()
    if os.geteuid() == 0:
        print('Execute a interface como usuário normal. O Flatpak/Polkit solicitará autorização quando necessária.', file=sys.stderr)
        return 1
    os.umask(0o022)
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtQml import QQmlApplicationEngine
        from PyQt6 import QtQuick  # Register QQuickWindow wrappers before QML loads.
        from controller import Controller
    except ImportError as exc:
        print(f'Dependência Qt indisponível: {exc}. Consulte README.md.', file=sys.stderr)
        return 1
    app = QApplication(sys.argv[:1])  # Enables the Plasma native file dialog helper.
    app.setApplicationName('mainuan-flatpak-install-gui')
    app.setApplicationDisplayName('Mainuan Instalador Flatpak')
    app.setDesktopFileName('mainuan-flatpak-install-gui')
    app.setWindowIcon(QIcon.fromTheme('system-software-install'))
    controller = Controller(args.demo)
    controller.override_name = args.override_appname
    if args.scope:
        controller.update(scope=args.scope)
    if args.reference:
        controller.pending_remove = args.remove
        controller.loadFile(args.reference)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', controller)
    try:
        engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))))
        if not engine.rootObjects():
            return 1
        return app.exec()
    finally:
        # Handles app.quit/session termination as well as a normal window close.
        controller.shutdown()
        from PyQt6 import sip
        sip.delete(engine)  # Context and worker stay alive until QML is destroyed.



if __name__ == '__main__':
    sys.exit(main())
