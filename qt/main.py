#!/usr/bin/python3
"""Mainuan Instalador Flatpak — Qt 6 / Kirigami entry point."""
import argparse
import os
from pathlib import Path
import sys
from i18n import _, install_qt_translators


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=_('Mainuan Flatpak Installer — local .flatpakref file'))
    parser.add_argument('reference', nargs='?', help=_('a local .flatpakref file'))
    parser.add_argument('--demo', nargs='?', const='ready', choices=['ready', 'remote', 'progress', 'success', 'error', 'cancelled'],
                        help=_('visual demonstration, unable to install'))
    parser.add_argument('--override-appname', help=_('plain-text display name; does not change the identity'))
    parser.add_argument('--remove', action='store_true', help=_('remove the exact reference, with graphical confirmation'))
    parser.add_argument('--scope', help=_('user, system or system:ID; required for --remove'))
    parser.add_argument('--fetch-dependencies', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--do-install', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.fetch_dependencies or args.do_install:
        parser.error(_('--fetch-dependencies and --do-install were discontinued: they were internal Bash helpers. '
                       'Open a .flatpakref file and use Install. No operation was performed.'))
    if args.scope and args.scope not in ('user', 'system'):
        import re
        if not re.fullmatch(r'system:[A-Za-z0-9_.-]+', args.scope):
            parser.error(_('Invalid destination: use user, system or system:ID.'))
    if args.scope == 'system:default':
        args.scope = 'system'
    if args.remove and (not args.reference or not args.scope):
        parser.error(_('--remove requires a .flatpakref file and --scope user|system|system:ID; the identity comes from the file.'))
    if args.reference and Path(args.reference).suffix.lower() != '.flatpakref':
        parser.error(_('Provide a local .flatpakref file. Standalone IDs or URLs from the old installer are not accepted.'))
    if args.demo and (args.reference or args.remove or args.override_appname is not None or args.scope):
        parser.error(_('--demo is isolated: it does not accept a file, destination, removal or overridden name.'))
    return args


def main():
    args = arguments()
    if os.geteuid() == 0:
        print(_('Run the interface as a normal user. Flatpak/Polkit will ask for authorization when needed.'), file=sys.stderr)
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
        print(_('Qt dependency unavailable: {error}. See README.md.').format(error=exc), file=sys.stderr)
        return 1
    app = QApplication(sys.argv[:1])  # Enables the Plasma native file dialog helper.
    app.setApplicationName('mainuan-flatpak-install-gui')
    translators = install_qt_translators(app)  # noqa: F841 (kept alive with the app)
    app.setApplicationDisplayName(_('Mainuan Flatpak Installer'))
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
