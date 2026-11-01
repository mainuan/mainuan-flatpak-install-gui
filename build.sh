#!/bin/sh
set -eu
umask 022
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output=${1:-"$here/dist"}
mkdir -p "$output"
output=$(CDPATH= cd -- "$output" && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT HUP INT TERM
chmod 755 "$stage"
install -d "$stage/DEBIAN" "$stage/usr/bin" "$stage/usr/share/applications" \
    "$stage/usr/share/mainuan-flatpak-install-gui/qt" \
    "$stage/usr/share/doc/mainuan-flatpak-install-gui"
install -m 644 "$here/packaging/control" "$stage/DEBIAN/control"
install -m 755 "$here/packaging/postinst" "$stage/DEBIAN/postinst"
install -m 755 "$here/packaging/postrm" "$stage/DEBIAN/postrm"
install -m 644 "$here/packaging/mainuan-mimeapps.list" "$stage/usr/share/mainuan-flatpak-install-gui/mainuan-mimeapps.list"
install -m 755 "$here/packaging/mainuan-flatpak-install-gui" "$stage/usr/bin/mainuan-flatpak-install-gui"
install -m 755 "$here/flatpak-install-gui" "$stage/usr/bin/flatpak-install-gui"
for file in "$here"/qt/*.py "$here"/qt/*.qml; do
    install -m 644 "$file" "$stage/usr/share/mainuan-flatpak-install-gui/qt/"
done
install -m 644 "$here/launcher" "$stage/usr/share/applications/mainuan-flatpak-install-gui.desktop"
install -m 644 "$here/packaging/copyright" "$stage/usr/share/doc/mainuan-flatpak-install-gui/copyright"
for file in "$here/LICENSE" "$here/README.md" "$here"/docs/*; do
    test -f "$file" || continue
    gzip -n -9 -c "$file" > "$stage/usr/share/doc/mainuan-flatpak-install-gui/$(basename "$file").gz"
done
install -d "$stage/usr/share/man/man1"
gzip -n -9 -c "$here/packaging/mainuan-flatpak-install-gui.1" > "$stage/usr/share/man/man1/mainuan-flatpak-install-gui.1.gz"
gzip -n -9 -c "$here/packaging/flatpak-install-gui.1" > "$stage/usr/share/man/man1/flatpak-install-gui.1.gz"
gzip -n -9 -c "$here/packaging/changelog" > "$stage/usr/share/doc/mainuan-flatpak-install-gui/changelog.gz"
version=$(sed -n 's/^Version: //p' "$here/packaging/control")
dpkg-deb --root-owner-group --build "$stage" "$output/mainuan-flatpak-install-gui_${version}_all.deb"
