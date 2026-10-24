#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154
STAGE=classification
set +e
python3 - "${EVIDENCE}" <<'PY'
import json,re,sys
from pathlib import Path
ev=Path(sys.argv[1])
sequences=["normal","kdirmodel-testmode","knewfilemenu-sequence"]
modes=["qt-baseline","qt-fallback-breeze","breeze-linked-no-init","breeze-init"]
def parse(path):
    text=path.read_text(errors="replace")
    def scalar(key):
        m=re.search(rf"^{re.escape(key)}=(.*)$",text,re.M)
        return m.group(1) if m else None
    icons={}
    for name in ("unknown","inode-directory","folder-red"):
        m=re.search(rf"^ICON={re.escape(name)} HAS=(true|false) NULL=(true|false) NAME=(.*)$",text,re.M)
        if not m: raise SystemExit(f"missing icon line {name} in {path.name}")
        icons[name]={"has":m.group(1)=="true","null":m.group(2)=="true","name":m.group(3)}
    primary_empty=icons["unknown"]["name"]=="" or icons["inode-directory"]["name"]==""
    return {
      "pre_theme":scalar("PRE_THEME"),"pre_fallback":scalar("PRE_FALLBACK"),"pre_resource":scalar("PRE_RESOURCE")=="true",
      "post_theme":scalar("POST_THEME"),"post_fallback":scalar("POST_FALLBACK"),"post_resource":scalar("POST_RESOURCE")=="true",
      "icons":icons,"primary_empty":primary_empty
    }
results={}
for seq in sequences:
    results[seq]={}
    for mode in modes:
        results[seq][mode]=parse(ev/f"{seq}--{mode}.txt")
baseline_valid=all(
    all(results[s]["qt-baseline"]["icons"][i]["name"]==i for i in ("unknown","inode-directory","folder-red"))
    for s in sequences
)
def any_repro(mode): return any(results[s][mode]["primary_empty"] for s in sequences)
if not baseline_valid:
    conclusion,result="baseline-drift-invalid","DIAG_INVALID"
elif any_repro("qt-fallback-breeze"):
    conclusion,result="fallback-breeze-alone-reproduces-kio-icon-name-loss","DIAG_COMPLETE"
elif any_repro("breeze-linked-no-init"):
    conclusion,result="breeze-linkage-state-reproduces-kio-icon-name-loss","DIAG_COMPLETE"
elif any_repro("breeze-init"):
    conclusion,result="breeze-initicons-reproduces-kio-icon-name-loss","DIAG_COMPLETE"
else:
    conclusion,result="breeze-init-state-does-not-reproduce-kio-icon-name-loss","DIAG_COMPLETE"
if result=="DIAG_INVALID":
    next_scope="restore-round12-qt-svg-fixture-and-rerun"
elif conclusion.endswith("does-not-reproduce-kio-icon-name-loss"):
    next_scope="kiconthemes-startup-or-kio-library-interaction"
else:
    next_scope="root-cause-confirmation-and-remediation-definition"
findings={
  "result":result,"package_attempted":False,"package_state_effect":"none",
  "baseline_valid":baseline_valid,"matrix":results,"conclusion":conclusion,
  "next_scope":next_scope
}
(ev/"findings.json").write_text(json.dumps(findings,indent=2,sort_keys=True)+"\n")
print(conclusion)
if result!="DIAG_COMPLETE": raise SystemExit(3)
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
echo 'KIO Round 15 BreezeIcons init-state diagnostic: COMPLETE (non-promoting)'
