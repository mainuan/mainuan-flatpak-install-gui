#!/usr/bin/env python3
"""Prévia da migração. Nenhuma operação Flatpak é executada."""
import argparse
import sys
from pathlib import Path
from metadata import read_reference

def main():
    parser = argparse.ArgumentParser(description="Mainuan Instalador Flatpak — prévia")
    parser.add_argument("reference", nargs="?")
    parser.add_argument("--demo", choices=["ready", "progress", "success", "error", "cancelled"], default="ready")
    args = parser.parse_args()
    info = {"name": "Aplicativo de exemplo", "id": "org.example.App", "source": "https://flathub.org"}
    error = ""
    if args.reference:
        try:
            info = read_reference(args.reference)
        except (ValueError, OSError) as exc:
            error = str(exc)
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtQml import QQmlApplicationEngine
    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("Mainuan Instalador Flatpak")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appInfo", info)
    engine.rootContext().setContextProperty("initialPhase", "error" if error else args.demo)
    engine.rootContext().setContextProperty("initialError", error)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        return 1
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
