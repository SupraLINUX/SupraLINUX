#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
campaign=json.loads((ROOT/"manifests/kde-tier1-package-campaign-batch2.json").read_text())
tier=json.loads((ROOT/"manifests/kde-frameworks-tier1.json").read_text())
EXPECTED={
"ktexttemplate":{"job":103624554096,"artifact":10306265683,"digest":"c164640037e564a43479daaa740f55c0f7578d977a7c38bfeb691fbd6b88544a","sub":"dh_makeshlibs/dpkg-gensymbols","tests":"10/10 PASS"},
"karchive":{"job":103624554004,"artifact":10305889632,"digest":"1850a0a6dd7f267870fda83f17f5990f806ec76ae8fe810144557c46af532d01","sub":"dh_auto_configure/Qt6LinguistTools","tests":"not-reached"},
"kholidays":{"job":103624554109,"artifact":10305513311,"digest":"522257440d6e04563162178dd3d3ab3ae658dc56c129dcf7f482fef8219bb0dc","sub":"dh_auto_configure/Qt6LinguistTools","tests":"not-reached"},
}
errors=[]
def req(x,m):
    if not x: errors.append(m)
req(campaign.get("state")=="remediation-pending-build","campaign remediation state")
req(campaign.get("selected_nodes")==["ktexttemplate","karchive","kholidays"],"selected nodes")
tm={x["id"]:x for x in tier["nodes"]}
for node,e in EXPECTED.items():
    d=campaign["nodes"][node]
    req(d.get("state")=="remediation-pending-build",f"{node}: campaign state")
    req(d.get("last_result")=="FAIL" and d.get("downstream_eligible") is False,f"{node}: FAIL/downstream")
    req(d.get("package_version")=="6.30.0-0supralinux2",f"{node}: revision 2")
    ev=d.get("evidence",[])
    req(len(ev)==1 and ev[0].get("result")=="FAIL",f"{node}: one FAIL evidence")
    if ev:
        x=ev[0]
        req(x.get("workflow_run")==34720201713 and x.get("job_id")==e["job"],f"{node}: run/job")
        req(x.get("artifact_id")==e["artifact"] and x.get("artifact_sha256")==e["digest"],f"{node}: artifact")
        req(x.get("failure_stage")=="sbuild" and x.get("failure_substage")==e["sub"],f"{node}: failure stage")
        req(x.get("tests")==e["tests"],f"{node}: tests")
    t=tm[node]
    req(t.get("state")=="FAIL" and t.get("packaging",{}).get("state")=="FAIL",f"{node}: canonical FAIL")
    req(t["packaging"].get("downstream_eligible") is False,f"{node}: canonical downstream false")
    req(t["packaging"].get("remediation",{}).get("next_package_version")=="6.30.0-0supralinux2",f"{node}: remediation rev")
    control=(ROOT/f"packages/kde/{node}/debian/control").read_text()
    changelog=(ROOT/f"packages/kde/{node}/debian/changelog").read_text()
    req(changelog.startswith(f"kf6-{node} (6.30.0-0supralinux2)"),f"{node}: changelog rev")
    req("compatibility placeholder" in control and "QDoc generation is outside" in control,f"{node}: doc stub metadata")
for node in ("karchive","kholidays"):
    control=(ROOT/f"packages/kde/{node}/debian/control").read_text()
    req("qt6-tools-dev (>= 6.5.0~)" in control,f"{node}: LinguistTools provider")
control=(ROOT/"packages/kde/ktexttemplate/debian/control").read_text()
req("qt6-tools-dev" not in control,"ktexttemplate: do not add unneeded Qt Tools")
symbols=campaign["nodes"]["ktexttemplate"]["symbols"]
req(symbols.get("sha256")=="552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273","ktexttemplate: retained baseline hash")
req(symbols.get("reviewed_sha256")=="e5c0e999ec374102a6b6693fa70f55f4b12bf38eed2013c573e765a521cf0585","ktexttemplate: reviewed symbols hash")
p=ROOT/"packages/kde/ktexttemplate/debian/libkf6texttemplate6.symbols.review.patch"
req(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()=="cddd2cd123d81a2f11ed07c0e764a43113d4327d9b9c0341cf2c71682ec334ba","ktexttemplate: review patch hash")
runner=(ROOT/"scripts/run-kde-tier1-package-batch2-preflight.sh").read_text()
for tok in ("SYMBOLS_REVIEW_PATCH","SYMBOLS_REVIEWED_SHA256","symbols-review-patch-sha256.txt","reviewed-symbols-sha256.txt"):
    req(tok in runner,f"runner missing {tok}")
doc=(ROOT/"docs/kde-tier1-package-batch2.md").read_text()
for tok in ("34720201713","10306265683","10305889632","10305513311","4 PASS","22 pending","3 FAIL","Qt6::LinguistTools","10/10"):
    req(tok in doc,f"docs missing {tok}")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 1 Batch 2 remediation validation: PASS")
print("Current canonical Tier 1: 4 PASS, 22 pending, 3 FAIL, 0 BLOCKED")
print("Remediation revisions prepared: ktexttemplate/karchive/kholidays = 6.30.0-0supralinux2")
