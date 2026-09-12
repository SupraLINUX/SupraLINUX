#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HEAD="5edf71b390088a551af81e7fc7e8d87a8378104f"; RUN=34720201713
FAILS={'ktexttemplate': {'job_id': 103624554096, 'artifact_id': 10306265683, 'artifact_sha256': 'c164640037e564a43479daaa740f55c0f7578d977a7c38bfeb691fbd6b88544a', 'cause': 'KDE 6.30 built and all 10 autotests passed, but dpkg-gensymbols rejected the retained Debian 6.28 symbols baseline after upstream moved scriptable-tags into a plugin and added binary-compatible Filter API.', 'substage': 'dh_makeshlibs/dpkg-gensymbols', 'tests': '10/10 PASS'}, 'karchive': {'job_id': 103624554004, 'artifact_id': 10305889632, 'artifact_sha256': '1850a0a6dd7f267870fda83f17f5990f806ec76ae8fe810144557c46af532d01', 'cause': 'dh_auto_configure failed because ECM ECMPoQmTools requires Qt6 LinguistTools for translation installation and qt6-tools-dev was missing from Build-Depends.', 'substage': 'dh_auto_configure/Qt6LinguistTools', 'tests': 'not-reached'}, 'kholidays': {'job_id': 103624554109, 'artifact_id': 10305513311, 'artifact_sha256': '522257440d6e04563162178dd3d3ab3ae658dc56c129dcf7f482fef8219bb0dc', 'cause': 'dh_auto_configure failed because ECM ECMPoQmTools requires Qt6 LinguistTools for translation installation and qt6-tools-dev was missing from Build-Depends.', 'substage': 'dh_auto_configure/Qt6LinguistTools', 'tests': 'not-reached'}}
def read(s): return (ROOT/s).read_text(encoding="utf-8")
def write(s,t): (ROOT/s).write_text(t,encoding="utf-8")
def load(s): return json.loads(read(s))
def dump(s,o): write(s,json.dumps(o,indent=2,ensure_ascii=False)+"\n")
c=load("manifests/kde-tier1-package-campaign-batch2.json"); assert c["state"]=="prepared-pending-build"; c["state"]="remediation-pending-build"
for node,f in FAILS.items():
    d=c["nodes"][node]; assert d["package_version"]=="6.30.0-0supralinux1"
    d["state"]="remediation-pending-build"; d["last_result"]="FAIL"; d["downstream_eligible"]=False; d["package_version"]="6.30.0-0supralinux2"
    d["evidence"]=[{"result":"FAIL","workflow_run":RUN,"job_id":f["job_id"],"commit":HEAD,"attempted_package_version":"6.30.0-0supralinux1","artifact_id":f["artifact_id"],"artifact_sha256":f["artifact_sha256"],"failure_stage":"sbuild","failure_substage":f["substage"],"tests":f["tests"],"cause":f["cause"]}]
    d["remediation"]={"next_package_version":"6.30.0-0supralinux2","state":"prepared","cause_addressed":f["substage"]}
s=c["nodes"]["ktexttemplate"]["symbols"]; s["review_patch"]="libkf6texttemplate6.symbols.review.patch"; s["review_patch_sha256"]="cddd2cd123d81a2f11ed07c0e764a43113d4327d9b9c0341cf2c71682ec334ba"; s["reviewed_sha256"]="e5c0e999ec374102a6b6693fa70f55f4b12bf38eed2013c573e765a521cf0585"
dump("manifests/kde-tier1-package-campaign-batch2.json",c)
t=load("manifests/kde-frameworks-tier1.json")
for item in t["nodes"]:
    node=item["id"]
    if node not in FAILS: continue
    f=FAILS[node]; ev={"result":"FAIL","workflow_run":RUN,"job_id":f["job_id"],"commit":HEAD,"attempted_package_version":"6.30.0-0supralinux1","artifact_id":f["artifact_id"],"artifact_sha256":f["artifact_sha256"],"failure_stage":"sbuild","failure_substage":f["substage"],"tests":f["tests"],"cause":f["cause"]}
    item["state"]="FAIL"; item["packaging"]={"state":"FAIL","package_version":"6.30.0-0supralinux1","claim":"hosted-clean-package-preflight","authoritative":False,"downstream_eligible":False,"evidence":[ev],"remediation":{"next_package_version":"6.30.0-0supralinux2","state":"prepared-pending-build"}}
dump("manifests/kde-frameworks-tier1.json",t)
entries={'karchive': '  * Add qt6-tools-dev as the Ubuntu provider of Qt6 LinguistTools required by\n    KDE ECM translation installation during the default build.\n  * Correct the documentation package description: QDoc is outside the default\n    Frameworks build profile, so the package is a compatibility placeholder.', 'kholidays': '  * Add qt6-tools-dev as the Ubuntu provider of Qt6 LinguistTools required by\n    KDE ECM translation installation during the default build.\n  * Correct the documentation package description: QDoc is outside the default\n    Frameworks build profile, so the package is a compatibility placeholder.', 'ktexttemplate': '  * Review the Debian 6.28 symbols baseline against the real KDE 6.30 build:\n    retain compiler/template emissions as optional, account for the upstream\n    scriptable-tags plugin split, and add the new Filter API at minimum 6.30.0.\n  * Correct the documentation package description: QDoc is outside the default\n    Frameworks build profile, so the package is a compatibility placeholder.'}
for node,body in entries.items():
    path=f"packages/kde/{node}/debian/changelog"; old=read(path); source=f"kf6-{node}"; assert old.startswith(source+" (6.30.0-0supralinux1)")
    write(path,f"{source} (6.30.0-0supralinux2) resolute; urgency=medium\n\n{body}\n\n -- SupraLINUX Project <packages@supralinux.invalid>  Sat, 12 Sep 2026 19:15:00 -0300\n\n"+old)
for node in ("karchive","kholidays"):
    path=f"packages/kde/{node}/debian/control"; x=read(path); assert "qt6-tools-dev" not in x; needle="               qt6-base-dev (>= 6.9.0~),"; assert needle in x
    write(path,x.replace(needle,needle+"\n               qt6-tools-dev (>= 6.5.0~),",1))
repls={"karchive":("This package contains the qch documentation files.","This package is a compatibility placeholder. QDoc generation is outside the\n default SupraLINUX Frameworks build profile."),"kholidays":("This package contains the qch documentation files.","This package is a compatibility placeholder. QDoc generation is outside the\n default SupraLINUX Frameworks build profile."),"ktexttemplate":("This package contains the documentation for KTextTemplate.","This package is a compatibility placeholder. QDoc generation is outside the\n default SupraLINUX Frameworks build profile.")}
for node,(a,b) in repls.items():
    path=f"packages/kde/{node}/debian/control"; x=read(path); assert a in x; write(path,x.replace(a,b,1))
path="packages/kde/ktexttemplate/debian/README.source"; x=read(path); assert "## KDE 6.30 symbols review" not in x
write(path,x+"\n## KDE 6.30 symbols review\n\nThe first 6.30 hosted build completed configure/build/install and 10/10 autotests, then dpkg-gensymbols exposed a real delta from the retained Debian 6.28 baseline. The reviewed packaging patch is applied only after the retained baseline hash is verified.\n\nUpstream 6.29 moved scriptable-tags from libKF6TextTemplate.so.6 into its own plugin, so the two generic qt_plugin_* symbols are removed from the main-library baseline and Qt metatype/template emissions are optional. KDE 6.30 adds the binary-compatible Filter constructor/context API; those symbols use upstream minimum version 6.30.0. Exception's inline virtual implementation can make its weak vtable emission toolchain-dependent and is tagged optional=inline.\n\nThe runner verifies the reviewed symbols SHA-256 before source-package assembly.\n")
print("state and package metadata generated")
