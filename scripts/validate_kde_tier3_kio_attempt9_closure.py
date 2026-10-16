#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
A9=load("manifests/kde-tier3-kio-attempt9-remediation.json")
LED=load("manifests/kde-tier3-build-level1-attempts.json")
RUN=36416891314; COMMIT="e7dfc689bf18aea5ed194df03f31e9c74627ead0"
ROOTFS_ID=10967311404; ROOTFS_SHA="533a74c6ad1dbce5b6ce5e219cabbc720ad9e692017d24899afbe8dede69f72e"
KIO_JOB=108910323115; KIO_ART=10968800996; KIO_SHA="17a0d0160104a1d095b433e3e80b5a8153c811a25ae802cb382ebcf85bf48260"
KXML_JOB=108910323005; KXML_ART=10967257671; KXML_SHA="91d0f5100748097446079fe1cead44444c88cf1d7a729d286c442402774921e5"
req(A9.get("attempt")==9 and A9.get("status")=="attempt9-closed-mixed","Attempt9 historical closure")
r=A9.get("attempt9_result",{})
req(r.get("workflow_run")==RUN and r.get("commit")==COMMIT and r.get("result")=="MIXED","Attempt9 workflow/result")
req(r.get("rootfs")=={"artifact_id":ROOTFS_ID,"artifact_sha256":ROOTFS_SHA},"Attempt9 rootfs")
k=r.get("kio",{})
req(k.get("job_id")==KIO_JOB and k.get("artifact_id")==KIO_ART and k.get("artifact_sha256")==KIO_SHA,"Attempt9 KIO artifact")
req(k.get("package_version")=="6.30.0-0supralinux9" and k.get("tests")=={"total":69,"pass":69,"fail":0},"Attempt9 KIO 69/69")
req(k.get("failure_substage")=="lintian/symbol-metadata" and k.get("downstream_eligible") is False,"Attempt9 KIO package failure")
lint=k.get("lintian",{})
req(lint.get("result")=="FAIL" and lint.get("new_symbol_count")==34,"Attempt9 Lintian signature")
req(lint.get("core_private_test_symbols")==1 and lint.get("gui_build_testing_only_symbols")==33,"Attempt9 symbol classes")
x=r.get("kxmlgui",{})
req(x.get("job_id")==KXML_JOB and x.get("artifact_id")==KXML_ART and x.get("artifact_sha256")==KXML_SHA,"Attempt9 KXMLGui artifact")
req(x.get("tests")=={"total":7,"pass":7,"fail":0} and x.get("python_import")=="PASS","Attempt9 KXMLGui PASS")
req(r.get("functional_remediation_result")=="PASS","Attempt9 functional remediation proof")
hist=[x for x in LED.get("campaign_history",[]) if x.get("attempt")==9]
req(len(hist)==1 and hist[0].get("workflow_run")==RUN and hist[0].get("result")=="MIXED","Attempt9 ledger campaign")
ki=[x for x in LED.get("nodes",{}).get("kio",[]) if x.get("attempt")==9]
kx=[x for x in LED.get("nodes",{}).get("kxmlgui",[]) if x.get("attempt")==9]
req(len(ki)==1 and ki[0].get("tests")=={"total":69,"pass":69,"fail":0} and ki[0].get("failure_substage")=="lintian/symbol-metadata","Attempt9 KIO ledger")
req(len(kx)==1 and kx[0].get("result")=="PASS" and kx[0].get("tests")=={"total":7,"pass":7,"fail":0},"Attempt9 KXMLGui ledger")
req(A9.get("package_execution_authorized") is False and A9.get("execution_authorized") is False,"Attempt9 closed authorization")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 KIO Attempt 9 historical closure: PASS")
print("KIO 69/69 upstream tests PASS; package FAIL at lintian/symbol-metadata")
print("KXMLGui 7/7 + Python import PASS")
