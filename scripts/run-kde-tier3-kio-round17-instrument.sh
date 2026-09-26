#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154
set -Eeuo pipefail

r17_record_svg_state() {
  local label="$1"
  {
    echo "=== dpkg ==="
    dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' qt6-svg-plugins qt6-svg-dev 2>&1 || true
    echo "=== policy ==="
    apt-cache policy qt6-svg-plugins qt6-svg-dev
    echo "=== depends qt6-svg-dev ==="
    apt-cache depends qt6-svg-dev
    echo "=== depends breeze-icon-theme ==="
    apt-cache depends breeze-icon-theme 2>&1 || true
    echo "=== svg plugin files ==="
    find /usr/lib /usr/local/lib -type f \( -iname '*qsvg*' -o -path '*/qt6/plugins/*svg*' \) -print 2>/dev/null | sort
  } > "${EVIDENCE}/svg-state-${label}.txt"
}

r17_remove_svg_plugin() {
  sudo DEBIAN_FRONTEND=noninteractive apt-get remove -y qt6-svg-plugins |& tee "${EVIDENCE}/svg-remove.log"
  if dpkg-query -W -f='${Status}' qt6-svg-plugins 2>/dev/null | grep -q 'install ok installed'; then
    echo "qt6-svg-plugins remained installed after removal" >&2
    return 1
  fi
}

r17_install_svg_plugin() {
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends qt6-svg-plugins |& tee "${EVIDENCE}/svg-reinstall.log"
  dpkg-query -W -f='${Status}' qt6-svg-plugins | grep -q 'install ok installed'
}
