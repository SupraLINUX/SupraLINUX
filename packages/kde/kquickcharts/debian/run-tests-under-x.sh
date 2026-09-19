#!/usr/bin/env bash
set -Eeuo pipefail
openbox >"${TMPDIR:-/tmp}/supralinux-openbox.log" 2>&1 &
wm_pid=$!
cleanup() { kill "${wm_pid}" 2>/dev/null || true; wait "${wm_pid}" 2>/dev/null || true; }
trap cleanup EXIT
ready=false
for _ in $(seq 1 100); do
  if xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -Eq 'window id # 0x[0-9a-fA-F]+'; then ready=true; break; fi
  sleep 0.1
done
[[ "${ready}" == true ]] || { echo "Openbox did not publish an EWMH supporting-WM window" >&2; exit 1; }
export QT_QPA_PLATFORM=xcb
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
dh_auto_test --no-parallel
