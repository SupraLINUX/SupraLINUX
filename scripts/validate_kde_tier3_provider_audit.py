#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

a=load("manifests/kde-tier3-provider-audit.json")
t=load("manifests/kde-frameworks-tier3.json")
d=load("manifests/kde-frameworks-tier3-dependencies.json")

canonical=[n["id"] for n in t.get("nodes",[])]
nodes={n["id"]:n for n in t.get("nodes",[])}

req(a.get("schema")==1,"Tier3 provider audit schema")
req(a.get("authority")=="kde-upstream","Tier3 provider audit authority")
req(a.get("frameworks_series")=="6.30.0","Tier3 provider audit Frameworks series")
req(a.get("release_reference")=="https://kde.org/info/kde-frameworks-6.30.0/","Tier3 provider audit release reference")
req(a.get("provider_platform")=="ubuntu-resolute","Tier3 provider audit platform")
req(a.get("claim")=="framework-provider-selection-only","Tier3 provider audit claim")
req(a.get("authoritative_package_build") is False,"Tier3 provider audit must not certify package builds")
req(a.get("package_state_effect")=="none","Tier3 provider audit package-state semantics")
req(a.get("status") in {"pending-ci","PASS"},"Tier3 provider audit lifecycle")
req(a.get("selected_nodes")==canonical and len(canonical)==20,"Tier3 provider audit canonical 20-node set")
req(set(a.get("components",{}))==set(canonical),"Tier3 provider audit component set")

support=d.get("support_components",{})
req(set(support)=={"breeze-icons","kdoctools","kded"},"Tier3 support component set")
req(all(support[x].get("state")=="PASS" and support[x].get("readiness")=="PASS" for x in support),"Tier3 provider audit requires support 3/3 PASS")
subdag=d.get("topology",{}).get("support_subdag",{})
req(subdag.get("status")=="PASS" and subdag.get("pass")==["breeze-icons","kdoctools","kded"],"Tier3 support sub-DAG prerequisite")
req(subdag.get("pending")==[] and subdag.get("current_fail")==[] and subdag.get("blocked")==[],"Tier3 support sub-DAG closed")

pc=a.get("platform_contract",{})
req(pc.get("qt_minimum")=="6.9.0" and pc.get("cmake_minimum")=="3.29","Tier3 provider platform minima")
req(pc.get("qt_probe_package")=="qt6-base-dev","Tier3 Qt provider probe package")

for node_id in canonical:
    c=a["components"].get(node_id,{})
    n=nodes[node_id]
    req(c.get("required_upstream_version")=="6.30.0",f"{node_id}: required upstream version")
    req(c.get("kde_source_url")==n.get("source_url"),f"{node_id}: KDE source URL linkage")
    req(c.get("kde_source_sha256")==n.get("source_sha256"),f"{node_id}: KDE source SHA linkage")
    req(c.get("ubuntu_source_package")==f"kf6-{node_id}",f"{node_id}: Ubuntu source-package probe")
    req(c.get("provider_decision") in {"pending-ci","ubuntu-compatible","supralinux-required"},f"{node_id}: provider decision lifecycle")
    req(n.get("state")=="pending",f"{node_id}: provider audit must not alter package state")
    planning=n.get("planning",{})
    req(planning.get("readiness")=="dependency-graph-ready",f"{node_id}: dependency-ready state")
    req(planning.get("package_contract")=="not-authorized",f"{node_id}: package contract remains unauthorized")
    req(planning.get("provider_audit") in {"pending-ci","PASS"},f"{node_id}: canonical provider audit lifecycle")

if a.get("status")=="pending-ci":
    req(all(c.get("provider_decision")=="pending-ci" for c in a["components"].values()),"pending Tier3 provider decisions")
    req(a.get("evidence") is None,"pending Tier3 provider audit evidence")
    req(a.get("execution_request",{}).get("status")=="requested","pending Tier3 provider audit execution request")
else:
    ev=a.get("evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_state_effect")=="none","Tier3 provider audit PASS evidence")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"Tier3 provider audit run/job evidence")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"Tier3 provider audit artifact evidence")
    req(len(ev.get("result_sha256",""))==64,"Tier3 provider audit result digest")
    req(all(c.get("provider_decision") in {"ubuntu-compatible","supralinux-required"} for c in a["components"].values()),"Tier3 final provider decisions")
    req(a.get("execution_request",{}).get("status")=="consumed","Tier3 provider audit execution request consumed")

req(a.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
doc=(ROOT/"docs/kde-tier3-provider-audit.md").read_text()
for token in ("20","KDE Frameworks 6.30.0","Ubuntu Resolute","provider","not a package PASS"):
    req(token in doc,f"Tier3 provider audit docs missing {token}")

for path in (
 "scripts/run-kde-tier3-provider-audit.sh",
 "scripts/kde-tier3-provider-audit-needed.sh",
 "scripts/test-kde-tier3-provider-audit-scope.sh",
 ".github/workflows/kde-tier3-provider-audit.yml",
):
    req((ROOT/path).exists(),f"missing Tier3 provider audit component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Frameworks Tier 3 provider-audit definition: PASS")
print("status="+a["status"])
print("nodes=20")
