#!/usr/bin/env bash
# shellcheck disable=SC1090,SC2034,SC2154

STAGE=probe-matrix
run_probe() {
  local binary="$1" sequence="$2" mode="$3"
  local label="${sequence}--${mode}" home="${WORK}/homes/${sequence}--${mode}"
  mkdir -p "${home}"
  HOME="${home}" KDECI_PLATFORM_PATH="${SRC}" \
  QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze QT_PLUGIN_PATH="${OBJ}/bin" \
  LD_LIBRARY_PATH="${OBJ}/bin${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" \
  timeout --signal=TERM --kill-after=5s 60s \
    dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' \
    "${PROBE}/build/${binary}" "${sequence}" "${mode}" > "${EVIDENCE}/${label}.txt"
}

for sequence in normal kdirmodel-testmode knewfilemenu-sequence; do
  run_probe qtprobe "${sequence}" qt-baseline
  run_probe kiconthemesprobe "${sequence}" kiconthemes-only
  run_probe kiocoreprobe "${sequence}" kiocore-only
  run_probe kiconthemeskiocoreprobe "${sequence}" kiconthemes-plus-kiocore
  run_probe kiowidgetsprobe "${sequence}" kiowidgets-closure
  run_probe kiofilewidgetsprobe "${sequence}" kiofilewidgets-closure
done

source "${ROOT}/scripts/run-kde-tier3-kio-round16-classify.sh"
