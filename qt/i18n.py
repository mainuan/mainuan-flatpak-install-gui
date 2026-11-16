"""Gettext catalog shared by Python and QML (qsTr) code.

The language comes from the session (LANGUAGE, LC_ALL, LC_MESSAGES, LANG), as
set by Plasma; nothing here forces a language.  Catalogs are installed in
/usr/share/locale/<lang>/LC_MESSAGES/mainuan-flatpak-install-gui.mo.  From a
checkout, compile them with ``po/i18n.sh compile build/locale``: that folder is
used when present, or set MAINUAN_FLATPAK_INSTALL_GUI_LOCALEDIR.
"""
import functools
import gettext
import os
from pathlib import Path

DOMAIN = 'mainuan-flatpak-install-gui'
_ENV = ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG')


def localedir():
    override = os.environ.get('MAINUAN_FLATPAK_INSTALL_GUI_LOCALEDIR')
    if override:
        return override
    build = Path(__file__).resolve().parents[1] / 'build' / 'locale'
    if build.is_dir():
        return str(build)
    return None  # gettext default: /usr/share/locale


@functools.lru_cache(maxsize=8)
def _catalog(environment, directory):
    return gettext.translation(DOMAIN, directory, fallback=True)


def catalog():
    # Keyed by the environment so tests can switch languages within a process.
    return _catalog(tuple(os.environ.get(k, '') for k in _ENV), localedir())


def _(message):
    return catalog().gettext(message)


def N_(message):
    """Mark a literal for extraction; translate it later with _()."""
    return message


def ngettext(singular, plural, n):
    return catalog().ngettext(singular, plural, n)


def pgettext(context, message):
    return catalog().pgettext(context, message)


def install_qt_translators(app):
    """qsTr() in QML resolves through this gettext catalog; Qt's own strings
    come from qtbase_<lang>.qm for the system locale.  Returns the translators,
    which must stay referenced for the application's lifetime."""
    from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator

    class GettextTranslator(QTranslator):
        def translate(self, context, source, disambiguation=None, n=-1):
            if not source:
                return None
            text = pgettext(disambiguation, source) if disambiguation else _(source)
            # None (null QString) lets Qt try other translators and fall back to the source.
            return text if text != source else None

        def isEmpty(self):
            return False

    translators = [GettextTranslator(app)]
    qtbase = QTranslator(app)
    if qtbase.load(QLocale.system(), 'qtbase', '_',
                   QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        translators.append(qtbase)
    # The last installed translator is queried first; qtbase returns null for our strings.
    for translator in translators:
        app.installTranslator(translator)
    apply_catalog_layout_direction(app)
    return translators


def apply_catalog_layout_direction(app):
    """Qt mirrors only when qtbase_<lang> says so (Urdu has none; qtbase may be
    missing): follow the direction of the application catalog in use.  Without
    a catalog the interface is English and the direction is left untouched."""
    from PyQt6.QtCore import QLocale, Qt

    language = catalog().info().get('language')
    if language and QLocale(language).textDirection() == Qt.LayoutDirection.RightToLeft:
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
