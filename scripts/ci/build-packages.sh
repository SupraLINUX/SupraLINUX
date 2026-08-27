#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/debs"

rm -rf "${ROOT_DIR}/build"
mkdir -p "${BUILD_DIR}"

packages=(
  "supralinux-snap-policy"
  "supralinux-base"
  "supralinux-settings"
  "supralinux-desktop"
)

for package in "${packages[@]}"; do
  package_dir="${ROOT_DIR}/packages/${package}"
  echo "==> Building ${package}"
  (
    cd "${package_dir}"
    dpkg-buildpackage --build=binary --no-sign
  )
done

find "${ROOT_DIR}/packages" -maxdepth 1 -type f -name '*.deb' -print -exec cp -v '{}' "${BUILD_DIR}/" ';'

count="$(find "${BUILD_DIR}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
if [[ "${count}" -ne "${#packages[@]}" ]]; then
  echo "Expected ${#packages[@]} .deb files, found ${count}." >&2
  exit 1
fi

echo "Built packages:"
dpkg-deb --show "${BUILD_DIR}"/*.deb
