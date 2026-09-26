#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154,SC1090
set -Eeuo pipefail

source "${ROOT}/scripts/run-kde-tier3-kio-round17-instrument.sh"

run_r17_test() {
  local bin="$1" testcase="$2" label="$3"
  local home="${WORK}/homes/${label}"
  mkdir -p "${home}"
  set +e
  env HOME="${home}" KDECI_PLATFORM_PATH="${SRC}" \
    QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze QT_PLUGIN_PATH="${OBJ}/bin" \
    timeout --signal=TERM --kill-after=10s 180s \
    dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' \
    "${OBJ}/bin/${bin}" "${testcase}" > "${EVIDENCE}/${label}.log" 2>&1
  local rc=$?
  set -e
  echo "${rc}" > "${EVIDENCE}/${label}.rc"
}

STAGE='svg-plugin-present-initial'
r17_record_svg_state present-initial
run_r17_test kdirmodeltest testIcon kdirmodel-present-initial
run_r17_test knewfilemenutest 'testFolderIconCollection:default' knewfilemenu-present-initial

STAGE='svg-plugin-absent'
r17_remove_svg_plugin
r17_record_svg_state absent
run_r17_test kdirmodeltest testIcon kdirmodel-absent
run_r17_test knewfilemenutest 'testFolderIconCollection:default' knewfilemenu-absent

STAGE='svg-plugin-reinstalled'
r17_install_svg_plugin
r17_record_svg_state reinstalled
run_r17_test kdirmodeltest testIcon kdirmodel-reinstalled
run_r17_test knewfilemenutest 'testFolderIconCollection:default' knewfilemenu-reinstalled

STAGE='classification'
set +e
python3 - "${EVIDENCE}" <<'PY'
import json,sys
from pathlib import Path
ev=Path(sys.argv[1])
kdmarker='Actual   (icon2.name()): ""'
knmarker='Actual   (iconLabel->property("iconName").toString()): ""'

def read(label,marker):
    text=(ev/f"{label}.log").read_text(errors="replace")
    rc=int((ev/f"{label}.rc").read_text().strip())
    return {"rc":rc,"historical_empty_name_failure":marker in text,"pass":rc==0}

present={
 "kdirmodel":read("kdirmodel-present-initial",kdmarker),
 "knewfilemenu":read("knewfilemenu-present-initial",knmarker),
}
absent={
 "kdirmodel":read("kdirmodel-absent",kdmarker),
 "knewfilemenu":read("knewfilemenu-absent",knmarker),
}
reinstalled={
 "kdirmodel":read("kdirmodel-reinstalled",kdmarker),
 "knewfilemenu":read("knewfilemenu-reinstalled",knmarker),
}

present_ok=all(x["pass"] and not x["historical_empty_name_failure"] for x in present.values())
absent_reproduces=all((not x["pass"]) and x["historical_empty_name_failure"] for x in absent.values())
reinstalled_ok=all(x["pass"] and not x["historical_empty_name_failure"] for x in reinstalled.values())

if present_ok and absent_reproduces and reinstalled_ok:
    result="DIAG_COMPLETE"
    conclusion="qt6-svg-plugins-presence-controls-both-kio-icon-name-failures"
    next_scope="qt-svg-provider-contract-root-cause-confirmation-and-remediation-definition"
elif not present_ok:
    result="DIAG_INVALID"
    conclusion="svg-present-baseline-not-clean"
    next_scope="repair-present-baseline"
elif not absent_reproduces:
    result="DIAG_COMPLETE"
    conclusion="removing-qt6-svg-plugins-does-not-reproduce-both-historical-failures"
    next_scope="compare-round13-environment-beyond-svg-plugin"
else:
    result="DIAG_COMPLETE"
    conclusion="qt6-svg-plugins-removal-reproduces-but-reinstall-does-not-recover"
    next_scope="inspect-process-cache-or-package-removal-side-effects"

findings={
 "result":result,
 "package_attempted":False,
 "package_state_effect":"none",
 "source_modified":False,
 "present_initial":present,
 "absent":absent,
 "reinstalled":reinstalled,
 "aba_invariants":{
   "present_initial_pass":present_ok,
   "absent_reproduces_both_historical_failures":absent_reproduces,
   "reinstalled_pass":reinstalled_ok
 },
 "conclusion":conclusion,
 "next_scope":next_scope
}
(ev/"findings.json").write_text(json.dumps(findings,indent=2,sort_keys=True)+"\n")
print(conclusion)
if result!="DIAG_COMPLETE":
    raise SystemExit(3)
PY
rc=$?
set -e
if [[ "${rc}" -eq 3 ]]; then
  DIAG_RESULT=DIAG_INVALID
  exit 3
elif [[ "${rc}" -ne 0 ]]; then
  exit "${rc}"
fi

STAGE='complete'
DIAG_RESULT=DIAG_COMPLETE
echo 'KIO Round 17 Qt SVG plugin A/B/A diagnostic: COMPLETE (non-promoting)'
