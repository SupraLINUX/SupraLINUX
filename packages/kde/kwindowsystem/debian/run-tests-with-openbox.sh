#!/bin/sh
set -eu

log="${TMPDIR:-/tmp}/kwindowsystem-openbox.log"
openbox --sm-disable >"${log}" 2>&1 &
wm_pid=$!
cleanup() {
    kill "${wm_pid}" 2>/dev/null || true
    wait "${wm_pid}" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

i=0
while [ "${i}" -lt 50 ]; do
    if ! kill -0 "${wm_pid}" 2>/dev/null; then
        cat "${log}" >&2
        echo "OpenBox exited before becoming ready" >&2
        exit 1
    fi
    if xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -q 'window id #'; then
        dh_auto_test -Skf6
        exit $?
    fi
    i=$((i + 1))
    sleep 0.1
done

cat "${log}" >&2
echo "OpenBox did not publish _NET_SUPPORTING_WM_CHECK within 5 seconds" >&2
exit 1
