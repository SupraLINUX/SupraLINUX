#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154,SC1090
set -Eeuo pipefail

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

STAGE='exact-original-baseline'
run_r17_test kdirmodeltest testIcon kdirmodel-original
run_r17_test knewfilemenutest 'testFolderIconCollection:default' knewfilemenu-original

python3 - "${EVIDENCE}" <<'PY'
import sys
from pathlib import Path
ev=Path(sys.argv[1])
kd=(ev/"kdirmodel-original.log").read_text(errors="replace")
kn=(ev/"knewfilemenu-original.log").read_text(errors="replace")
kdrc=int((ev/"kdirmodel-original.rc").read_text())
knrc=int((ev/"knewfilemenu-original.rc").read_text())
if kdrc==0 or 'Actual   (icon2.name()): ""' not in kd:
    raise SystemExit("ORIGINAL_BASELINE_INVALID: kdirmodel did not reproduce")
if knrc==0 or 'Actual   (iconLabel->property("iconName").toString()): ""' not in kn:
    raise SystemExit("ORIGINAL_BASELINE_INVALID: knewfilemenu did not reproduce")
PY

source "${ROOT}/scripts/run-kde-tier3-kio-round17-instrument.sh"

STAGE='kdirmodel-local-result-variant'
r17_patch_kdirmodel_local_result
cmake --build "${OBJ}" --target kdirmodeltest --parallel 2 |& tee "${EVIDENCE}/kdirmodel-local-result-build.log"
run_r17_test kdirmodeltest testIcon kdirmodel-local-result

STAGE='restore-after-kdirmodel'
r17_restore_sources
cmake --build "${OBJ}" --target kdirmodeltest --parallel 2 |& tee "${EVIDENCE}/kdirmodel-restored-build.log"
run_r17_test kdirmodeltest testIcon kdirmodel-restored

STAGE='knewfilemenu-named-default-variant'
r17_patch_knew_named_default
cmake --build "${OBJ}" --target knewfilemenutest --parallel 2 |& tee "${EVIDENCE}/knewfilemenu-named-default-build.log"
run_r17_test knewfilemenutest 'testFolderIconCollection:default' knewfilemenu-named-default

STAGE='restore-after-knewfilemenu'
r17_restore_sources
cmake --build "${OBJ}" --target knewfilemenutest --parallel 2 |& tee "${EVIDENCE}/knewfilemenu-restored-build.log"
run_r17_test knewfilemenutest 'testFolderIconCollection:default' knewfilemenu-restored

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
    return {"rc":rc,"original_failure":marker in text,"pass":rc==0}

kd0=read("kdirmodel-original",kdmarker)
kn0=read("knewfilemenu-original",knmarker)
kdr=read("kdirmodel-restored",kdmarker)
knr=read("knewfilemenu-restored",knmarker)
kdv=read("kdirmodel-local-result",kdmarker)
knv=read("knewfilemenu-named-default",knmarker)

baseline_valid=(
    kd0["rc"]!=0 and kd0["original_failure"] and
    kn0["rc"]!=0 and kn0["original_failure"] and
    kdr["rc"]!=0 and kdr["original_failure"] and
    knr["rc"]!=0 and knr["original_failure"]
)
if not baseline_valid:
    result="DIAG_INVALID"
    conclusion="original-or-restored-baseline-drift"
    next_scope="repair-build-reproducibility-before-structural-ab"
elif kdv["pass"] and knv["pass"]:
    result="DIAG_COMPLETE"
    conclusion="minimal-QIcon-local-lifetime-changes-heal-both-failures"
    next_scope="confirm-temporary-lifetime-copy-move-vs-LTO-root-cause"
elif kdv["pass"] or knv["pass"]:
    result="DIAG_COMPLETE"
    conclusion="minimal-QIcon-local-lifetime-change-heals-one-failure"
    next_scope="confirm-healed-path-and-isolate-unresolved-path"
else:
    result="DIAG_COMPLETE"
    conclusion="minimal-local-lifetime-changes-do-not-heal"
    next_scope="isolate-other-attempt1-codegen-perturbations"

findings={
 "result":result,
 "package_attempted":False,
 "package_state_effect":"none",
 "baseline_valid":baseline_valid,
 "original":{"kdirmodel":kd0,"knewfilemenu":kn0},
 "restored":{"kdirmodel":kdr,"knewfilemenu":knr},
 "variants":{
   "kdirmodel-local-result":kdv,
   "knewfilemenu-named-default":knv,
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
echo 'KIO Round 17 original-source structural A/B diagnostic: COMPLETE (non-promoting)'
