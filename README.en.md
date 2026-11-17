<div align="center">

<img src="https://raw.githubusercontent.com/mainuan/.github/main/profile/assets/mainuan-logo.svg" width="96" alt="Mainuan logo">

# Mainuan Flatpak Installer

Installs, opens and removes the application described by a local `.flatpakref` file in one click.

[![CI](https://github.com/mainuan/mainuan-flatpak-install-gui/actions/workflows/ci.yml/badge.svg)](https://github.com/mainuan/mainuan-flatpak-install-gui/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mainuan/mainuan-flatpak-install-gui)](https://github.com/mainuan/mainuan-flatpak-install-gui/releases/latest)
[![License](https://img.shields.io/github/license/mainuan/mainuan-flatpak-install-gui)](LICENSE)
![Platform](https://img.shields.io/badge/Kubuntu%2026.04%20%7C%20Plasma%206.6-0079c1)

[Português](README.md) · **English**

</div>

---

## About

The installer opens when a `.flatpakref` file is clicked in Dolphin. It shows
the application name and summary, lets you choose **Only your user** or
**Whole system**, and installs with **Install**; origin, operations and
diagnostics stay under **Show details**. It is a Qt 6 Quick/QML + Kirigami
interface in Python (PyQt6) using libflatpak through PyGObject. The interface
**never runs as root**: Flatpak and the session Polkit agent handle
authorization.

## Features

- One local `.flatpakref` per window, also through the `application/vnd.flatpak.ref` MIME association.
- User or system installation; **Install** authorizes adding the origins the file and its dependencies declare.
- Checks: HTTPS-only URLs without credentials or fragments, GPG verification required, existing origins with a different URL, collection or key stop the operation, `.flatpakref` up to 1 MiB.
- When the exact reference is already installed in the chosen target: **Open**, **Uninstall**, **Close**. Removal asks for confirmation, keeps personal data and does not remove origins or prune runtimes globally.
- Interface in 33 languages, following the KDE Plasma language.

Bare IDs and URLs are out of scope and rejected with a clear error.

## Installation

Preinstalled in the Mainuan Linux ISO. On another Kubuntu/Ubuntu 26.04 system,
download the `.deb` and `SHA256SUMS` from the
[latest release](https://github.com/mainuan/mainuan-flatpak-install-gui/releases/latest):

```bash
sha256sum --check --ignore-missing SHA256SUMS
sudo apt install ./mainuan-flatpak-install-gui_1.1_all.deb
```

The package provides, conflicts with and replaces the legacy `flatpak-install-gui`.

## Usage

```sh
mainuan-flatpak-install-gui "/path/app.flatpakref"
mainuan-flatpak-install-gui --scope system "/path/app.flatpakref"
mainuan-flatpak-install-gui --remove --scope user "/path/app.flatpakref"
mainuan-flatpak-install-gui --override-appname="Shown name" "/path/app.flatpakref"
mainuan-flatpak-install-gui --demo progress
```

`--scope` takes `user`, `system` or `system:ID` and is required with
`--remove`; `--demo` never installs, removes or launches anything.
`flatpak-install-gui` remains as a compatibility alias; the old
`--fetch-dependencies` and `--do-install` helpers fail without doing anything.
MIME integration details: [docs/integracao-mime.md](docs/integracao-mime.md) (Portuguese).

## Building and testing

```bash
git clone https://github.com/mainuan/mainuan-flatpak-install-gui.git
cd mainuan-flatpak-install-gui
sudo apt build-dep ./
dpkg-buildpackage -us -uc -b      # runs python3 -m unittest discover -s tests -v
```

CI ([`ci.yml`](.github/workflows/ci.yml)) also runs the translation checks
(`po/i18n.sh check-pot`, `po/i18n.sh validate`), the offscreen QML harnesses
`tests/qml_flow.py` and `tests/qml_presentation.py`, and a **reproducibility
check** (two builds in different paths must produce identical `.deb` files),
then lints the package and installs, reinstalls and removes it in a clean
Ubuntu 26.04 container. Releases are published only from `v*` tags.

## Translations

33 languages via gettext; see [docs/i18n/README.md](docs/i18n/README.md).

## Credits

Daigo ([@daigoasuka](https://github.com/daigoasuka)) and Rafael Ruscher
([@ruscher](https://github.com/ruscher)). Based on Tiger OS
**flatpak-install-gui** by Natanael Barbosa Santos (MIT,
[docs/LICENSE-original-MIT](docs/LICENSE-original-MIT)).

## License

[GPL-3.0](LICENSE).
