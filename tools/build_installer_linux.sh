#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
if [[ -z "${VERSION}" ]]; then
  VERSION="$(date +%d.%m.%Y)"
fi

DIST_DIR="${ROOT_DIR}/dist"
OUT_DIR="${ROOT_DIR}/dist_installer/linux"
PKG_ROOT="${ROOT_DIR}/build/linux_pkg"
APP_NAME="FireStorm"

rm -rf "${DIST_DIR}" "${OUT_DIR}" "${PKG_ROOT}"
mkdir -p "${OUT_DIR}" "${PKG_ROOT}"

python -m pip install --upgrade pip pyinstaller
python setup.py build_ext --inplace

pyinstaller \
  --noconfirm \
  --clean \
  --name "${APP_NAME}" \
  --onedir \
  --windowed \
  --hidden-import=tkinter \
  --hidden-import=PIL._tkinter_finder \
  --collect-submodules PIL \
  --add-data "FireStorm/settings:settings" \
  --add-data "FireStorm/layouts:layouts" \
  --add-data "FireStorm/img:img" \
  --add-data "FireStorm/ver:ver" \
  "FireStorm/FireStorm.py"

mkdir -p "${PKG_ROOT}/opt/firestorm"
cp -R "${DIST_DIR}/${APP_NAME}/." "${PKG_ROOT}/opt/firestorm/"

mkdir -p "${PKG_ROOT}/usr/bin"
cp "${ROOT_DIR}/tools/installer/linux/firestorm" "${PKG_ROOT}/usr/bin/firestorm"
chmod 755 "${PKG_ROOT}/usr/bin/firestorm"

mkdir -p "${PKG_ROOT}/usr/share/applications"
cp "${ROOT_DIR}/tools/installer/linux/firestorm.desktop" "${PKG_ROOT}/usr/share/applications/firestorm.desktop"

mkdir -p "${PKG_ROOT}/usr/share/pixmaps"
cp "${ROOT_DIR}/FireStorm/img/logo.png" "${PKG_ROOT}/usr/share/pixmaps/firestorm.png"

mkdir -p "${PKG_ROOT}/DEBIAN"
cat > "${PKG_ROOT}/DEBIAN/control" <<EOF
Package: firestorm
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: FireTracker <support@firestorm.team>
Description: FireStorm tracker client
EOF

DEB_PATH="${OUT_DIR}/firestorm_${VERSION}_amd64.deb"
dpkg-deb --build "${PKG_ROOT}" "${DEB_PATH}"

echo "OK: ${DEB_PATH}"
