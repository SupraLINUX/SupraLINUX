#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154
set -Eeuo pipefail

run_test() {
  local bin="$1" testcase="$2" label="$3" touch="${4:-}"
  local home="${WORK}/homes/${label}"
  mkdir -p "${home}"
  set +e
  if [[ -n "${touch}" ]]; then
    env HOME="${home}" KDECI_PLATFORM_PATH="${SRC}" SUPRALINUX_R17_TOUCH="${touch}" \
      QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze QT_PLUGIN_PATH="${OBJ}/bin" \
      timeout --signal=TERM --kill-after=10s 180s \
      dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' \
      "${OBJ}/bin/${bin}" "${testcase}" > "${EVIDENCE}/${label}.log" 2>&1
  else
    env HOME="${home}" KDECI_PLATFORM_PATH="${SRC}" \
      QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze QT_PLUGIN_PATH="${OBJ}/bin" \
      timeout --signal=TERM --kill-after=10s 180s \
      dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' \
      "${OBJ}/bin/${bin}" "${testcase}" > "${EVIDENCE}/${label}.log" 2>&1
  fi
  local rc=$?
  set -e
  echo "${rc}" > "${EVIDENCE}/${label}.rc"
}

STAGE=touch-perturbation-matrix
mkdir -p "${WORK}/homes"
run_test kdirmodeltest testIcon kdirmodel-baseline
for touch in KDIR_FALLBACK KDIR_ABSOLUTE KDIR_FROMTHEME KDIR_BEFORE_OVERLAYS KDIR_AFTER_OVERLAYS; do
  run_test kdirmodeltest testIcon "kdirmodel-${touch}" "${touch}"
done
run_test knewfilemenutest 'testFolderIconCollection:default' knewfilemenu-baseline
for touch in KNEW_CONSTRUCTOR KNEW_CHECK_ENTRY KNEW_CHECK_EXIT KNEW_SHOW_ENTRY KNEW_AFTER_INIT KNEW_DEFAULT_CREATED KNEW_SETICON_INPUT; do
  run_test knewfilemenutest 'testFolderIconCollection:default' "knewfilemenu-${touch}" "${touch}"
done

STAGE=classification
set +e
python3 - "${EVIDENCE}" <<'PY'
import json,sys
from pathlib import Path
ev=Path(sys.argv[1])
kd_marker='Actual   (icon2.name()): ""'
kn_marker='Actual   (iconLabel->property("iconName").toString()): ""'

def read(label,marker):
    text=(ev/f"{label}.log").read_text(errors="replace")
    rc=int((ev/f"{label}.rc").read_text().strip())
    return {"rc":rc,"original_failure":marker in text,"pass":rc==0}

kd_order=["KDIR_FALLBACK","KDIR_ABSOLUTE","KDIR_FROMTHEME","KDIR_BEFORE_OVERLAYS","KDIR_AFTER_OVERLAYS"]
kn_order=["KNEW_CONSTRUCTOR","KNEW_CHECK_ENTRY","KNEW_CHECK_EXIT","KNEW_SHOW_ENTRY","KNEW_AFTER_INIT","KNEW_DEFAULT_CREATED","KNEW_SETICON_INPUT"]
kd_base=read("kdirmodel-baseline",kd_marker)
kn_base=read("knewfilemenu-baseline",kn_marker)
kd={x:read(f"kdirmodel-{x}",kd_marker) for x in kd_order}
kn={x:read(f"knewfilemenu-{x}",kn_marker) for x in kn_order}

baseline_valid=(kd_base["rc"]!=0 and kd_base["original_failure"] and kn_base["rc"]!=0 and kn_base["original_failure"])
kd_first=next((x for x in kd_order if kd[x]["pass"]),None)
kn_first=next((x for x in kn_order if kn[x]["pass"]),None)

if not baseline_valid:
    result="DIAG_INVALID"
    conclusion="conditional-instrumentation-still-perturbs-baseline"
    next_scope="remove-all-baseline-code-delta-and-use-link-time-interposition"
elif kd_first and kn_first:
    result="DIAG_COMPLETE"
    conclusion="single-QIcon-name-read-heals-both-failures"
    next_scope="confirm-lazy-QIcon-name-materialization-root-cause"
elif kd_first or kn_first:
    result="DIAG_COMPLETE"
    conclusion="single-QIcon-name-read-heals-one-failure"
    next_scope="confirm-localized-read-heal-and-investigate-unresolved-path"
else:
    result="DIAG_COMPLETE"
    conclusion="single-QIcon-name-read-alone-does-not-heal"
    next_scope="reproduce-attempt1-minimal-combination"

findings={
 "result":result,
 "package_attempted":False,
 "package_state_effect":"none",
 "baseline_valid":baseline_valid,
 "baseline":{"kdirmodel":kd_base,"knewfilemenu":kn_base},
 "kdirmodel":{"variants":kd,"first_healing_touch":kd_first},
 "knewfilemenu":{"variants":kn,"first_healing_touch":kn_first},
 "conclusion":conclusion,
 "next_scope":next_scope
}
(ev/"findings.json").write_text(json.dumps(findings,indent=2,sort_keys=True)+"\n")
print(conclusion)
print("kdirmodel_first_healing_touch="+str(kd_first))
print("knewfilemenu_first_healing_touch="+str(kn_first))
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
echo 'KIO Round 17 conditional name-read perturbation diagnostic: COMPLETE (non-promoting)'
