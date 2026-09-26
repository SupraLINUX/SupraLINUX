#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

d=load("manifests/kde-frameworks-tier3-dependencies.json")
t1=load("manifests/kde-frameworks-tier1.json")
t2=load("manifests/kde-frameworks-tier2.json")
t3=load("manifests/kde-frameworks-tier3.json")

req(d.get("schema")==1 and d.get("authority")=="kde-upstream","Tier3 dependency schema/authority")
req(d.get("frameworks")=="6.30.0" and d.get("tier")==3 and d.get("target")=="linux","Tier3 dependency series/tier/target")
req(d.get("common",{}).get("cmake_minimum")=="3.29","Tier3 upstream CMake minimum")
req(d.get("common",{}).get("ecm")=="6.30.0","Tier3 ECM dependency")
req(d.get("common",{}).get("qt_minimum")=="6.9.0","Tier3 Qt minimum")

ids1={n["id"] for n in t1["nodes"]}
ids2={n["id"] for n in t2["nodes"]}
ids3={n["id"] for n in t3["nodes"]}
nodes=d.get("nodes",{})
support=d.get("support_components",{})
req(set(nodes)==ids3 and len(ids3)==20,"Tier3 dependency nodes match canonical inventory")
req(set(support)=={"breeze-icons","kdoctools","kded"},"Tier3 support-component set")
known=ids1|ids2|ids3|set(support)

for node_id,n in nodes.items():
    md=n.get("metadata",{})
    req(md.get("repo")==f"KDE/{node_id}" and md.get("ref")=="v6.30.0",f"{node_id}: upstream repo/ref")
    for field in ("commit","root_cmake_blob","kde_ci_blob"):
        req(isinstance(md.get(field),str) and len(md[field])==40,f"{node_id}: {field}")
    fw=n.get("frameworks",{})
    for field in ("source_required","selected_linux_profile","qml_required","test_required","runtime_required","ci_environment_required"):
        vals=fw.get(field,[])
        req(isinstance(vals,list) and len(vals)==len(set(vals)),f"{node_id}: {field} list/uniqueness")
        for dep in vals:
            req(dep in known,f"{node_id}: unknown KDE dependency {dep}")
    edges=n.get("tier3_edges",{})
    expected={
      "build_required":[x for x in fw.get("source_required",[]) if x in ids3],
      "selected_profile":[x for x in fw.get("selected_linux_profile",[]) if x in ids3],
      "qml_required":[x for x in fw.get("qml_required",[]) if x in ids3],
      "test_required":[x for x in fw.get("test_required",[]) if x in ids3],
      "runtime_validation":[x for x in fw.get("runtime_required",[]) if x in ids3],
    }
    for field,vals in expected.items():
        req(edges.get(field)==vals,f"{node_id}: derived Tier3 edge {field}")

req("breeze-icons" in nodes["kiconthemes"]["frameworks"]["selected_linux_profile"],"KIconThemes selects BreezeIcons")
req(nodes["kio"]["tier3_edges"]["selected_profile"]==["kwallet"],"KIO Linux CI profile selects KWallet")
req("kded" in nodes["kio"]["frameworks"]["runtime_required"],"KIO KDED runtime gate")
req("kdoctools" in nodes["kio"]["frameworks"]["ci_environment_required"],"KIO KDocTools CI/documentation profile")
req(nodes["knotifyconfig"]["tier3_edges"]["test_required"]==["kconfigwidgets","kxmlgui"],"KNotifyConfig Tier3 test-only edges")
req(nodes["knewstuff"]["tier3_edges"]["runtime_validation"]==["kcmutils"],"KNewStuff KCMUtils runtime-validation edge")
req(nodes["purpose"]["tier3_edges"]["qml_required"]==["kcmutils"],"Purpose KCMUtils required QML edge")

b=support["breeze-icons"]
req(b.get("source_sha256")=="93866c19791838fc9757b305e010e23bb38cb5f201e4ecc96cc8ef5f1173ebe6","BreezeIcons release hash")
req(b.get("commit")=="ac9c67bf20ba6b100d037f07b873e7053467334c","BreezeIcons tag commit")
req(b.get("role")=="selected-build-predecessor" and b.get("required_by")==["kiconthemes"],"BreezeIcons role")
kd=support["kdoctools"]
req(kd.get("source_sha256")=="b90b42ab222a3034729e517d0c06258abf6bdc28591ec78ad56f24aebbaaed94","KDocTools release hash")
req(kd.get("role")=="ci-documentation-predecessor","KDocTools role")
kded=support["kded"]
req(kded.get("source_sha256")=="0adf6e22300cee74d57e790b5db844f03a1366a4d6315edbaa49174b12bf1861","KDED release hash")
req(kded.get("role")=="runtime-predecessor" and kded.get("runtime_for")==["kio"],"KDED runtime role")

# Compute Tier3 build/test/QML selected-profile levels. Runtime-only edges are validation gates.
deps={}
for node_id,n in nodes.items():
    e=n["tier3_edges"]
    deps[node_id]=set(e["build_required"]+e["selected_profile"]+e["qml_required"]+e["test_required"])
remaining=set(ids3); done=set(); levels=[]
while remaining:
    ready=sorted(x for x in remaining if deps[x] <= done)
    if not ready:
        errors.append("Tier3 dependency cycle: "+repr({x:sorted(deps[x]-done) for x in sorted(remaining)}))
        break
    levels.append(ready)
    done.update(ready); remaining.difference_update(ready)
req(levels==d.get("topology",{}).get("build_and_test_levels"),"Tier3 topological levels")
req(d.get("topology",{}).get("acyclic") is True,"Tier3 acyclic declaration")
req(d.get("topology",{}).get("support_preconditions",{}).get("kiconthemes")==["breeze-icons"],"KIconThemes support gate")
req(d.get("topology",{}).get("support_preconditions",{}).get("kio_ci_profile")==["kdoctools"],"KIO documentation support gate")
req(d.get("topology",{}).get("support_preconditions",{}).get("kio_runtime_validation")==["kded"],"KIO runtime support gate")
req(d.get("topology",{}).get("deferred_runtime_validation",{}).get("knewstuff")==["kcmutils"],"KNewStuff deferred runtime gate")

for node in ("breeze-icons","kdoctools","kded"):
    c=support[node]
    req(c.get("readiness") in {"package-contract-ready","materialized","PASS","build-level1-ready"},f"{node}: support lifecycle readiness")
    pc=c.get("package_contract",{})
    req(pc.get("status")=="ready" and pc.get("manifest")=="manifests/kde-tier3-support-package-contracts.json",f"{node}: support contract linkage")
req(d.get("topology",{}).get("support_build_levels")==[["breeze-icons","kdoctools"],["kded"]],"support build topology")
req(d.get("topology",{}).get("support_contracts",{}).get("status")=="ready","support contract topology state")

sm=d.get("topology",{}).get("support_materialization",{})
req(sm.get("status")=="PASS" and sm.get("manifest")=="manifests/kde-tier3-support-materialization.json","support materialization topology state")
for node in ("breeze-icons","kdoctools","kded"):
    c=support[node]
    mat=c.get("materialization",{})
    req(mat.get("status")=="PASS" and mat.get("package_state_effect")=="none",f"{node}: materialization evidence linkage")
for node in ("breeze-icons","kdoctools"):
    c=support[node]
    req(c.get("state")=="PASS" and c.get("readiness")=="PASS",f"{node}: support package PASS readiness")
    pkg=c.get("packaging",{})
    req(pkg.get("state")=="PASS" and pkg.get("downstream_eligible") is True,f"{node}: downstream PASS packaging")
    ev=pkg.get("evidence",{})
    req(ev.get("workflow_run")==35700002095 and isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,f"{node}: support PASS evidence")
req(support["kded"].get("state")=="PASS" and support["kded"].get("readiness")=="PASS","KDED support PASS readiness")
kded_pkg=support["kded"].get("packaging",{})
req(kded_pkg.get("state")=="PASS" and kded_pkg.get("downstream_eligible") is True,"KDED downstream PASS packaging")
kded_ev=kded_pkg.get("evidence",{})
req(kded_ev.get("workflow_run")==35721085911 and kded_ev.get("artifact_id")==10691372157,"KDED PASS evidence")
req(len(kded_ev.get("artifact_sha256",""))==64 and kded_ev.get("tests")=="1/1 PASS","KDED PASS artifact/test evidence")
req(support["kded"].get("build_gate",{}).get("state")=="PASS","KDED closed build gate")
gate=d.get("topology",{}).get("support_build_gate",{})
req(gate.get("level0")==["breeze-icons","kdoctools"] and gate.get("level1")==["kded"],"support binary-build gate")
req(gate.get("manifest")=="manifests/kde-tier3-support-build-level0.json","support build level0 campaign link")
req(gate.get("level0_status")=="PASS" and gate.get("level1_status")=="PASS","support build level closure")
req(gate.get("kdoctools_pass_artifact_id")==10682066198,"KDocTools level1 predecessor artifact")
req(gate.get("level1_manifest")=="manifests/kde-tier3-support-build-level1.json","support build level1 campaign link")
req(gate.get("kded_pass_artifact_id")==10691372157 and len(gate.get("kded_pass_artifact_sha256",""))==64,"KDED level1 PASS artifact")
subdag=d.get("topology",{}).get("support_subdag",{})
req(subdag.get("status")=="PASS" and subdag.get("pass")==["breeze-icons","kdoctools","kded"],"support sub-DAG PASS")
req(subdag.get("pending")==[] and subdag.get("current_fail")==[] and subdag.get("blocked")==[],"support sub-DAG closed state")
t3audit=d.get("topology",{}).get("tier3_provider_audit",{})
req(t3audit.get("status")=="pending-ci","Tier3 provider audit topology state")
req(t3audit.get("manifest")=="manifests/kde-tier3-provider-audit.json","Tier3 provider audit topology manifest")
req(set(t3audit.get("selected_nodes",[]))==set(nodes),"Tier3 provider audit topology nodes")
req(t3audit.get("package_state_effect")=="none","Tier3 provider audit topology package-state semantics")

doc=(ROOT/"docs/kde-tier3.md").read_text()
for token in ("Tier 3 dependency graph","Breeze Icons","KDocTools","KDED","4 topological"):
    req(token in doc,f"Tier3 docs token: {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Frameworks Tier 3 dependency validation: PASS")
print("Tier3 nodes: 20")
print("Support components: breeze-icons, kdoctools, kded")
print("Build/test topology: 4 levels, acyclic")
