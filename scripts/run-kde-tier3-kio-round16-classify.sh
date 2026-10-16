#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154

STAGE=classification
set +e
python3 - "${EVIDENCE}" <<'PY'
import json,re,sys
from pathlib import Path
ev=Path(sys.argv[1])
seqs=["normal","kdirmodel-testmode","knewfilemenu-sequence"]
modes=["qt-baseline","kiconthemes-only","kiocore-only","kiconthemes-plus-kiocore","kiowidgets-closure","kiofilewidgets-closure"]
icons=("unknown","inode-directory","folder-red")

def parse(path):
    text=path.read_text(errors="replace")
    def scalar(key):
        m=re.search(rf"^{re.escape(key)}=(.*)$",text,re.M)
        return m.group(1) if m else None
    got={}
    for name in icons:
        m=re.search(rf"^ICON={re.escape(name)} HAS=(true|false) NULL=(true|false) NAME=(.*)$",text,re.M)
        if not m:
            raise SystemExit(f"missing icon line {name} in {path.name}")
        got[name]={"has":m.group(1)=="true","null":m.group(2)=="true","name":m.group(3)}
    return {
      "pre_theme":scalar("PRE_THEME"),"pre_fallback":scalar("PRE_FALLBACK"),"pre_resource":scalar("PRE_RESOURCE")=="true",
      "post_theme":scalar("POST_THEME"),"post_fallback":scalar("POST_FALLBACK"),"post_resource":scalar("POST_RESOURCE")=="true",
      "icons":got,
      "primary_empty":got["unknown"]["name"]=="" or got["inode-directory"]["name"]==""
    }

matrix={s:{m:parse(ev/f"{s}--{m}.txt") for m in modes} for s in seqs}
baseline_valid=all(all(matrix[s]["qt-baseline"]["icons"][i]["name"]==i for i in icons) for s in seqs)
startup_observed=all(
    matrix[s]["kiconthemes-only"]["post_resource"] and matrix[s]["kiconthemes-only"]["post_fallback"]=="breeze"
    for s in seqs
)
def repro(mode): return any(matrix[s][mode]["primary_empty"] for s in seqs)

if not baseline_valid:
    result,conclusion,next_scope="DIAG_INVALID","baseline-drift-invalid","restore-baseline-fixture"
elif not startup_observed:
    result,conclusion,next_scope="DIAG_INVALID","kiconthemes-startup-not-observed","repair-link-retention-or-startup-probe"
elif repro("kiconthemes-only"):
    result,conclusion,next_scope="DIAG_COMPLETE","kiconthemes-startup-load-reproduces-kio-icon-name-loss","root-cause-confirmation-and-remediation-definition"
elif repro("kiocore-only"):
    result,conclusion,next_scope="DIAG_COMPLETE","kiocore-load-reproduces-kio-icon-name-loss","root-cause-confirmation-and-remediation-definition"
elif repro("kiconthemes-plus-kiocore"):
    result,conclusion,next_scope="DIAG_COMPLETE","kiconthemes-kiocore-interaction-reproduces-kio-icon-name-loss","root-cause-confirmation-and-remediation-definition"
elif repro("kiowidgets-closure"):
    result,conclusion,next_scope="DIAG_COMPLETE","kiowidgets-closure-reproduces-kio-icon-name-loss","root-cause-confirmation-and-remediation-definition"
elif repro("kiofilewidgets-closure"):
    result,conclusion,next_scope="DIAG_COMPLETE","kiofilewidgets-only-reproduces-does-not-explain-common-kdirmodel-cause","actual-kdirmodel-and-knewfilemenu-object-path-comparison"
else:
    result,conclusion,next_scope="DIAG_COMPLETE","library-preload-alone-does-not-reproduce-kio-icon-name-loss","actual-kio-object-path-state-transition"

findings={
 "result":result,"package_attempted":False,"package_state_effect":"none",
 "baseline_valid":baseline_valid,"kiconthemes_startup_observed":startup_observed,
 "matrix":matrix,"conclusion":conclusion,"next_scope":next_scope
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

STAGE=complete
DIAG_RESULT=DIAG_COMPLETE
echo 'KIO Round 16 library linkage threshold diagnostic: COMPLETE (non-promoting)'
