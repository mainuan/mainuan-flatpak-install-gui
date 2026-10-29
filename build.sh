#!/bin/bash

[ ! "${EUID}" = "0" ] && {
  echo "Execute esse script como root:"
  echo
  echo "  sudo ${0}"
  echo
  exit 1
}

HERE="$(dirname "$(readlink -f "${0}")")"

working_dir=$(mktemp -d)

mkdir -p {${working_dir}/DEBIAN,${working_dir}/usr/bin,${working_dir}/usr/share/applications}

cp -v "${HERE}/flatpak-install-gui"        "${working_dir}/usr/bin/"
cp -v "${HERE}/launcher"                   "${working_dir}/usr/share/applications/flatpak-install-gui.desktop"

chmod +x "${working_dir}/usr/bin/flatpak-install-gui"

(
 echo "Package: flatpak-install-gui"
 echo "Priority: optional"
 echo "Version: $(date +%y.%m.%d%H%M%S)"
 echo "Architecture: all"
 echo "Maintainer: Natanael Barbosa Santos"
 echo "Depends: "
 echo "Description: Instalador GUI para Flatpak"
 echo
) > "${working_dir}/DEBIAN/control"

dpkg -b ${working_dir}
rm -rfv ${working_dir}

mv "${working_dir}.deb" "${HERE}/flatpak-install-gui.deb"

chmod 777 "${HERE}/flatpak-install-gui.deb"
chmod -x  "${HERE}/flatpak-install-gui.deb"
