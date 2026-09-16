#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path

R=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((R/p).read_text())
def txt(p): return (R/p).read_text()

c=load("manifests/kde-tier1-package-campaign-batch7.json")
t=load("manifests/kde-frameworks-tier1.json")
d=load("manifests/kde-dag.json")
tier={x["id"]:x for x in t["nodes"]}
dag=d["nodes"]
selected=["kcalendarcore","kcoreaddons","kwidgetsaddons"]

req(c.get("schema")==1,"campaign schema")
req(c.get("batch")=="tier1-batch-7","campaign id")
req(c.get("state")=="prepared-pending-build","campaign state")
req(c.get("authority")=="kde-upstream" and c.get("frameworks_series")=="6.30.0","authority/version")
req(c.get("selected_nodes")==selected,"selected nodes/order")
req(c.get("canonical_snapshot")=={"state":"pre-build","tier1":"18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED"},"canonical snapshot")
counts={s:sum(x.get("state")==s for x in t["nodes"]) for s in ("PASS","pending","FAIL","BLOCKED")}
req(counts=={"PASS":18,"pending":11,"FAIL":0,"BLOCKED":0},f"Tier1 counts {counts}")

probe=c["shared_predecessors"]["upstream_layout_probe"]
req(probe.get("status")=="PASS" and probe.get("workflow_run")==35086226149 and probe.get("job_id")==104761571679,"layout probe identity")
req(probe.get("artifact_id")==10443202060 and probe.get("artifact_sha256")=="c50a32b26e18ee84173b5a00cbd85e0c2b380660be9d939eb489c370f1317e77","layout probe artifact")
req(probe.get("verified_defaults",{}).get("BUILD_PYTHON_BINDINGS")=="ON" and probe["verified_defaults"].get("BUILD_TESTING")=="ON","layout defaults")

provider=c["shared_predecessors"]["dependency_provider"]
req(provider.get("status")=="PASS" and provider.get("workflow_run")==35087361837 and provider.get("job_id")==104765243282,"provider evidence identity")
req(provider.get("artifact_id")==10442512801 and provider.get("artifact_sha256")=="49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9","provider artifact")
req(provider.get("python_build",{}).get("import_status")=="PASS","python build provider")

py=c["shared_packaging_inputs"]["python_policy"]
req(py.get("environment")=="DEB_PYTHON_INSTALL_LAYOUT=deb" and py.get("install_layout")=="deb_system","python install policy")
req(py.get("build_bindings") is True and py.get("tests_enabled") is True and py.get("runtime_smoke")=="import-module","python gates")

expected={
 "kcalendarcore":("6.30.0-0supralinux1","libKF6CalendarCore.so.6","python3-kcalendarcore","KCalendarCore"),
 "kcoreaddons":("6.30.0-0supralinux1","libKF6CoreAddons.so.6","python3-kcoreaddons","KCoreAddons"),
 "kwidgetsaddons":("6.30.0-0supralinux1","libKF6WidgetsAddons.so.6","python3-kwidgetsaddons","KWidgetsAddons"),
}
for n,(ver,soname,pypkg,pymod) in expected.items():
    x=c["nodes"][n]
    req(x.get("state")=="prepared-pending-build" and x.get("downstream_eligible") is False and x.get("evidence")==[],f"{n} prepared only")
    req(x.get("package_version")==ver and x.get("soname")==soname,f"{n} version/soname")
    req(x.get("python_package")==pypkg and x.get("python_module")==pymod,f"{n} python contract")
    req(x.get("upstream_defaults",{}).get("BUILD_PYTHON_BINDINGS")=="ON" and x["upstream_defaults"].get("BUILD_TESTING")=="ON",f"{n} upstream defaults")
    req(tier[n].get("state")=="pending",f"{n} Tier1 must remain pending")
    req(n not in dag,f"{n} must stay absent from promoted package DAG before PASS")
    base=R/"packages"/"kde"/n/"debian"
    for f in ("control","rules","changelog","README.source","copyright.reference",x["symbols"]["file"]+".reference","source/format","upstream/signing-key.asc"):
        req((base/f).is_file(),f"{n} missing {f}")
    rules=(base/"rules").read_text()
    req("DEB_PYTHON_INSTALL_LAYOUT = deb" in rules,f"{n} Debian Python layout")
    req("-DBUILD_PYTHON_BINDINGS=ON" in rules and "-DBUILD_TESTING=ON" in rules,f"{n} Python/tests fail-closed")
    req("BUILD_TESTING=OFF" not in rules and "BUILD_PYTHON_BINDINGS=OFF" not in rules,f"{n} no downstream feature disable")
    if n=="kwidgetsaddons": req("-DBUILD_DESIGNERPLUGIN=ON" in rules,"kwidgetsaddons designer")
    control=(base/"control").read_text()
    for token in ("dh-sequence-python3","python3-build","python3-dev","libshiboken6-dev","libpyside6-dev",f"Package: {pypkg}"):
        req(token in control,f"{n} control missing {token}")
    pyinstall=(base/f"{pypkg}.install").read_text()
    req(f"usr/lib/python3/dist-packages/{pymod}*.so" in pyinstall,f"{n} python install path")
    devinstall=(base/f"{x['development_package']}.install").read_text()
    req("usr/include/PySide6/" in devinstall and "usr/share/PySide6/typesystems/" in devinstall,f"{n} exported PySide development metadata")

req(c["nodes"]["kwidgetsaddons"]["development_package"]=="libkf6widgetsaddons-dev","widgets dev identity")
req(tier["kguiaddons"].get("state")=="pending" and "kguiaddons" not in dag,"KGuiAddons must remain pending and absent from promoted package DAG")
reason=c["selection_rationale"]["deferred"].get("kguiaddons","")
req("KCoreAddons" in reason and "PASS" in reason,"KGuiAddons DAG deferral reason")

runner=txt("scripts/run-kde-tier1-package-batch7-preflight.sh")
for token in ("100% tests passed, 0 tests failed out of","python-import-smoke","import_module","apt-get check","lintian --fail-on error","LD_LIBRARY_PATH","DEB_PYTHON_INSTALL_LAYOUT"):
    req(token in runner,f"runner missing {token}")
scope=txt("scripts/kde-tier1-package-batch7-needed.sh")
req("kcalendarcore|kcoreaddons|kwidgetsaddons" in scope and "run-kde-tier1-package-batch7-preflight.sh" in scope,"scope selector")
wf=txt(".github/workflows/kde-tier1-package-batch7.yml")
req("node: [kcalendarcore, kcoreaddons, kwidgetsaddons]" in wf and "fail-fast: false" in wf and "max-parallel: 3" in wf,"workflow matrix/DAG")
req("10298635300" in wf and "10301938362" in wf,"retained inputs")

doc=txt("docs/kde-tier1-package-batch7.md")
status=txt("docs/status/2026-09-16-batch7.md")
for s,name in ((doc,"batch doc"),(status,"status doc")):
    req("18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED" in s,f"{name} canonical state")
    req("35086226149" in s and "10443202060" in s,f"{name} layout evidence")
    req("DEB_PYTHON_INSTALL_LAYOUT=deb" in s,f"{name} Python layout")
    req("KGuiAddons" in s and "KCoreAddons" in s,f"{name} deferral")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 1 Batch 7 preparation: PASS")
print("Selected: KCalendarCore, KCoreAddons, KWidgetsAddons")
print("Canonical Tier 1 unchanged: 18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED")
