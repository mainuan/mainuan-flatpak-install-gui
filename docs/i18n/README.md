# Internacionalização

Contrato comum: `docs/03-arquitetura-i18n-kde.md` do repositório de documentação Mainuan.

* **Domínio gettext:** `mainuan-flatpak-install-gui` (nome do pacote Debian).
* **Idioma-fonte:** inglês. A interface brasileira está em `po/pt_BR.po`
  (texto português original, sem alterações).
* **Instalação:** `/usr/share/locale/<lang>/LC_MESSAGES/mainuan-flatpak-install-gui.mo`,
  gerado por `build.sh`; o `.desktop` instalado recebe `Name[<lang>]`/`Comment[<lang>]`
  via `msgfmt --desktop` a partir do modelo `launcher`.
* **Idioma em execução:** só o da sessão (`LANGUAGE`, `LC_ALL`, `LC_MESSAGES`, `LANG`,
  como o Plasma exporta). Nada força idioma.

## Layout

```
po/i18n.sh        script padrão Mainuan (extract, update, add, validate, check-pot, coverage, compile)
po/i18n.conf      domínio e palavras-chave (qsTr com contexto opcional)
po/POTFILES.in    arquivos-fonte extraídos (Python, QML e o modelo .desktop `launcher`)
po/LINGUAS        idiomas instalados (por enquanto só pt_BR)
po/mainuan-flatpak-install-gui.pot
po/pt_BR.po
qt/i18n.py        _(), N_(), ngettext(), pgettext() e o QTranslator para o QML
```

## Python + QML com um só catálogo

* Python: `from i18n import _, pgettext` e `_('Text {name}').format(name=...)`.
* QML: `qsTr("Text %1").arg(valor)`; `qsTr("Text", "contexto")` vira `msgctxt`.
  `install_qt_translators(app)` (chamado em `main.py` antes de carregar o QML)
  instala um `QTranslator` cujo `translate()` consulta o gettext do mesmo domínio,
  e o `qtbase_<lang>.qm` do `QLocale.system()` para textos do próprio Qt.
* Não use plural em `qsTr` (o gettext não recebe `msgid_plural` por esse caminho):
  monte plurais no Python com `ngettext`.

## Tarefas

```sh
po/i18n.sh extract            # regenerar o POT depois de mudar textos
po/i18n.sh update             # mesclar o POT em po/*.po
po/i18n.sh validate           # msgfmt --check + placeholders (CI)
po/i18n.sh check-pot          # falha se o POT estiver desatualizado (CI)
po/i18n.sh coverage
po/i18n.sh add es             # novo idioma (Plural-Forms verificado) e LINGUAS
```

Executar do checkout em outro idioma:

```sh
po/i18n.sh compile build/locale   # qt/i18n.py usa build/locale quando existe
LANGUAGE=pt_BR ./mainuan-flatpak-install-gui --demo
LANGUAGE=en ./mainuan-flatpak-install-gui --demo
```

Também é possível apontar `MAINUAN_FLATPAK_INSTALL_GUI_LOCALEDIR` para outra pasta.

## Testes

`tests/test_i18n.py` compila `po/pt_BR.po` numa pasta temporária e verifica, com o
código real, `LANGUAGE=pt_BR` (português) e `LANGUAGE=en`/`LC_ALL=C` (inglês) para
Python, mensagens de linha de comando, erros do Flatpak e o QML (`tests/qml_i18n.py`,
em `QT_QPA_PLATFORM=offscreen`). Os demais testes comparam o msgid inglês
(`LANGUAGE=en`); `tests/package_smoke.py` usa `LANGUAGE=pt_BR` para validar o
catálogo instalado no pacote.

## Particularidades

* Nome e resumo de aplicativos vêm do AppStream/.desktop do próprio Flatpak: são
  dados externos, não vão ao POT. `metadata.ui_languages()` escolhe a variante
  traduzida pelos idiomas de interface do usuário (`QLocale.system().uiLanguages()`,
  que segue `LANGUAGE`), em vez do `LC_CTYPE` usado antes.
* Saída do libflatpak (status de progresso, texto de `GLib.Error`, erros de operação)
  é exibida como veio, sem tradução; só as mensagens do próprio instalador são traduzidas.
* Valores técnicos (`user`, `system`, `system:ID`, referências, URLs, IDs) não são traduzidos.
* As manpages (`packaging/*.1`) ficam fora do escopo desta etapa.
* Build: requer `gettext` (`msgfmt`) além de `dpkg-deb`.
