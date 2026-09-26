#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154
set -Eeuo pipefail

run_test() {
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

STAGE=instrumented-test-execution
mkdir -p "${WORK}/homes"
run_test kdirmodeltest testIcon kdirmodel-testIcon
run_test knewfilemenutest 'testFolderIconCollection:default' knewfilemenu-folder-default

STAGE=classification
set +e
python3 - "${EVIDENCE}" <<'PY'
import json,re,sys
from pathlib import Path
ev=Path(sys.argv[1])
kd=(ev/"kdirmodel-testIcon.log").read_text(errors="replace")
kn=(ev/"knewfilemenu-folder-default.log").read_text(errors="replace")
kd_rc=int((ev/"kdirmodel-testIcon.rc").read_text().strip())
kn_rc=int((ev/"knewfilemenu-folder-default.rc").read_text().strip())

kd_failure='Actual   (icon2.name()): ""' in kd
kn_failure='Actual   (iconLabel->property("iconName").toString()): ""' in kn

def parse(line):
    parts=line.strip().split("|")
    d={}
    for p in parts[2:]:
        if "=" in p:
            k,v=p.split("=",1); d[k]=v
    return d

kdir=[parse(x) for x in kd.splitlines() if "R17|KDIR|" in x]
knew=[parse(x) for x in kn.splitlines() if "R17|KNEW|" in x]
invalid=[x for x in kdir if x.get("source","").endswith(".png")]
if not invalid:
    invalid=[x for x in kdir if x.get("source","").endswith(".svg.svg")]
by={x.get("stage"):x for x in invalid}
def name(stage): return by.get(stage,{}).get("name")
if name("fallback")=="":
    kd_transition="global-icon-state-broken-before-kdirmodel-fallback"
elif name("after-fromtheme")=="":
    kd_transition="invalid-theme-fallback-transition"
elif name("before-overlays") and name("after-overlays")=="":
    kd_transition="KIconUtils-addOverlays-transition"
elif name("after-overlays"):
    kd_transition="after-overlays-to-QVariant-or-test-observation"
else:
    kd_transition="unresolved-kdirmodel-gap"

order=["constructor-body","check-entry","check-exit","show-entry","show-after-init","default-created","seticon-input","seticon-property","seticon-after-pixmap","grid-ready"]
stage_values={}
for stage in order:
    vals=[x.get("name") for x in knew if x.get("stage")==stage]
    if vals: stage_values[stage]=vals[-1]
first_empty=next((s for s in order if s in stage_values and stage_values[s]==""),None)
if first_empty:
    kn_transition="first-empty-"+first_empty
elif stage_values.get("grid-ready"):
    kn_transition="after-grid-ready-to-test-observation"
else:
    kn_transition="unresolved-knewfilemenu-gap"

valid=kd_failure and kn_failure and kd_rc!=0 and kn_rc!=0
if not valid:
    result="DIAG_INVALID"
    conclusion="instrumentation-perturbed-original-failure"
    next_scope="repair-observation-only-instrumentation"
else:
    result="DIAG_COMPLETE"
    conclusion="actual-object-path-transition-localized"
    if "unresolved" in kd_transition or "unresolved" in kn_transition:
        next_scope="narrow-unresolved-object-path-gap"
    else:
        next_scope="minimal-root-cause-confirmation-from-localized-transitions"

findings={
 "result":result,
 "package_attempted":False,
 "package_state_effect":"none",
 "original_failures_reproduced":{"kdirmodel":kd_failure,"knewfilemenu":kn_failure},
 "return_codes":{"kdirmodel":kd_rc,"knewfilemenu":kn_rc},
 "kdirmodel":{"transition":kd_transition,"invalid_path_checkpoints":by},
 "knewfilemenu":{"transition":kn_transition,"stage_values":stage_values,"first_empty_stage":first_empty},
 "conclusion":conclusion,
 "next_scope":next_scope
}
(ev/"findings.json").write_text(json.dumps(findings,indent=2,sort_keys=True)+"\n")
print(conclusion)
print("kdirmodel_transition="+kd_transition)
print("knewfilemenu_transition="+kn_transition)
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

STAGE=complete
DIAG_RESULT=DIAG_COMPLETE
echo 'KIO Round 17 actual object-path state-transition diagnostic: COMPLETE (non-promoting)'
