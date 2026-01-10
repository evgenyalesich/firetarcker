#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"
if [[ -z "${VERSION}" ]]; then
  echo "Usage: tools/build_installer_macos.sh <version>"
  exit 1
fi

DIST_DIR="${ROOT_DIR}/dist"
OUT_DIR="${ROOT_DIR}/dist_installer/macos"
APP_NAME="FireStorm"

rm -rf "${DIST_DIR}" "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

python -m pip install --upgrade pip pyinstaller
python setup.py build_ext --inplace

pyinstaller \
  --noconfirm \
  --clean \
  --name "${APP_NAME}" \
  --windowed \
  --add-data "FireStorm/settings:settings" \
  --add-data "FireStorm/layouts:layouts" \
  --add-data "FireStorm/img:img" \
  --add-data "FireStorm/ver:ver" \
  "FireStorm/FireStorm.py"

DMG_PATH="${OUT_DIR}/FireStorm-${VERSION}.dmg"
hdiutil create -volname "FireStorm" -srcfolder "${DIST_DIR}/${APP_NAME}.app" -ov -format UDZO "${DMG_PATH}"

echo "OK: ${DMG_PATH}"
