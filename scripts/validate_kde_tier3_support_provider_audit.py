#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

audit=load("manifests/kde-tier3-support-provider-audit.json")
deps=load("manifests/kde-frameworks-tier3-dependencies.json")
t1=load("manifests/kde-frameworks-tier1.json")
t2=load("manifests/kde-frameworks-tier2.json")

req(audit.get("schema")==1,"Tier3 support provider audit schema")
req(audit.get("authority")=="kde-upstream","Tier3 support authority")
req(audit.get("frameworks_series")=="6.30.0","Tier3 support Frameworks series")
req(audit.get("provider_platform")=="ubuntu-resolute","Tier3 support provider platform")
req(audit.get("claim")=="provider-selection-only","Tier3 support audit claim")
req(audit.get("authoritative_package_build") is False,"Tier3 support audit must not claim package build")
req(audit.get("package_state_effect")=="none","Tier3 support audit package-state semantics")
req(audit.get("status") in {"pending-ci","PASS"},"Tier3 support audit lifecycle")

support=deps.get("support_components",{})
req(set(support)=={"breeze-icons","kdoctools","kded"},"Tier3 support component set")
components=audit.get("components",{})
req(set(components)==set(support),"Tier3 support audit component set")

expected_probe={
 "breeze-icons":"kf6-breeze-icon-theme",
 "kdoctools":"kdoctools6",
 "kded":"kded6",
}
expected_role={
 "breeze-icons":"selected-build-predecessor",
 "kdoctools":"ci-documentation-predecessor",
 "kded":"runtime-predecessor",
}
for node,probe in expected_probe.items():
    c=components.get(node,{})
    req(c.get("role")==expected_role[node],f"{node}: role")
    req(c.get("required_upstream_version")=="6.30.0",f"{node}: required version")
    req(c.get("ubuntu_probe_package")==probe,f"{node}: Ubuntu probe package")
    req(c.get("provider_decision") in {"pending-ci","ubuntu-compatible","supralinux-required"},f"{node}: provider decision")
    req(isinstance(c.get("retained_kde_predecessors"),list) and c.get("retained_kde_predecessors"),f"{node}: retained predecessor list")
    req(isinstance(c.get("external_requirements"),list),f"{node}: external requirement list")

pass1={n["id"] for n in t1.get("nodes",[]) if n.get("state")=="PASS" and n.get("packaging",{}).get("downstream_eligible") is True}
pass2={n["id"] for n in t2.get("nodes",[]) if n.get("state")=="PASS" and n.get("packaging",{}).get("downstream_eligible") is True}
known=pass1|pass2|{"extra-cmake-modules"}
for node,c in components.items():
    for dep in c.get("retained_kde_predecessors",[]):
        req(dep in known,f"{node}: retained KDE predecessor not PASS: {dep}")

req("breeze-icons" in deps["nodes"]["kiconthemes"]["frameworks"]["selected_linux_profile"],"KIconThemes support dependency")
req("kdoctools" in deps["nodes"]["kio"]["frameworks"]["ci_environment_required"],"KIO KDocTools CI dependency")
req("kded" in deps["nodes"]["kio"]["frameworks"]["runtime_required"],"KIO KDED runtime dependency")

if audit.get("status")=="pending-ci":
    req(all(c.get("provider_decision")=="pending-ci" for c in components.values()),"pending audit decisions")
    req(audit.get("evidence") is None,"pending audit must not contain promoted evidence")
else:
    ev=audit.get("evidence",{})
    req(ev.get("result")=="PASS","support audit PASS evidence")
    req(ev.get("package_state_effect")=="none","support audit evidence package-state semantics")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"support audit run/job evidence")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"support audit artifact evidence")
    req(all(c.get("provider_decision") in {"ubuntu-compatible","supralinux-required"} for c in components.values()),"final provider decisions")
    for node,c in components.items():
        dep=support.get(node,{})
        req(dep.get("provider")==c.get("provider_decision").replace("-required","") if c.get("provider_decision")=="supralinux-required" else dep.get("provider") in {"ubuntu","supralinux"},f"{node}: selected provider reflected in dependency manifest")
        req(dep.get("readiness")=="package-contract-required",f"{node}: support package-contract readiness")
        pae=dep.get("provider_audit",{})
        req(pae.get("status")=="PASS" and pae.get("decision")==c.get("provider_decision"),f"{node}: provider-audit promotion")
        req(pae.get("artifact_id")==ev.get("artifact_id") and pae.get("artifact_sha256")==ev.get("artifact_sha256"),f"{node}: provider-audit evidence linkage")
    req(audit.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

doc=(ROOT/"docs/kde-tier3-support-provider-audit.md").read_text()
for token in ("Breeze Icons","KDocTools","KDED","provider audit","not a package PASS"):
    req(token in doc,f"Tier3 support audit docs missing {token}")

for path in (
    "scripts/run-kde-tier3-support-provider-audit.sh",
    "scripts/kde-tier3-support-provider-audit-needed.sh",
    "scripts/test-kde-tier3-support-provider-audit-scope.sh",
    ".github/workflows/kde-tier3-support-provider-audit.yml",
):
    req((ROOT/path).exists(),f"missing Tier3 support audit component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 support provider-audit definition: PASS")
print("status="+audit["status"])
