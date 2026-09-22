#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

m=load("manifests/kde-tier3-support-package-contracts.json")
audit=load("manifests/kde-tier3-support-provider-audit.json")
deps=load("manifests/kde-frameworks-tier3-dependencies.json")
tier3=load("manifests/kde-frameworks-tier3.json")

expected={
 "breeze-icons":{
   "sha":"93866c19791838fc9757b305e010e23bb38cb5f201e4ecc96cc8ef5f1173ebe6",
   "source":"kf6-breeze-icons",
 },
 "kdoctools":{
   "sha":"b90b42ab222a3034729e517d0c06258abf6bdc28591ec78ad56f24aebbaaed94",
   "source":"kf6-kdoctools",
 },
 "kded":{
   "sha":"0adf6e22300cee74d57e790b5db844f03a1366a4d6315edbaa49174b12bf1861",
   "source":"kf6-kded",
 },
}

req(m.get("schema")==1,"Tier3 support package-contract schema")
req(m.get("authority")=="kde-upstream","Tier3 support contract authority")
req(m.get("role")=="support-component-package-contract-preparation","Tier3 support contract role")
req(m.get("frameworks_series")=="6.30.0","Tier3 support contract series")
req(m.get("selected_components")==["breeze-icons","kdoctools","kded"],"Tier3 support selected components")
req(m.get("state") in {"reference-capture-pending","reference-capture-pass","contracts-ready","materialized"},"Tier3 support contract lifecycle")

pa=m.get("provider_audit",{})
req(pa.get("manifest")=="manifests/kde-tier3-support-provider-audit.json","support contract provider-audit link")
req(pa.get("required_status")=="PASS" and pa.get("selected_provider")=="supralinux","support contract provider selection")
req(audit.get("status")=="PASS","support contract requires provider-audit PASS")
req(all(c.get("provider_decision")=="supralinux-required" for c in audit.get("components",{}).values()),"all support providers selected SupraLINUX")

components=m.get("components",{})
req(set(components)==set(expected),"support contract component set")
support=deps.get("support_components",{})
for node,e in expected.items():
    c=components.get(node,{})
    req(c.get("upstream_source")==node,f"{node}: upstream source identity")
    req(c.get("upstream_version")=="6.30.0",f"{node}: upstream version")
    req(c.get("upstream_source_sha256")==e["sha"],f"{node}: upstream source SHA-256")
    refs=c.get("reference_sources",{})
    req(refs.get("ubuntu")==e["source"] and refs.get("debian")==e["source"],f"{node}: technical reference source identity")
    req(c.get("contract_state") in {"reference-capture-pending","reference-capture-pass","contract-ready","materialized"},f"{node}: contract state")
    dep=support.get(node,{})
    req(dep.get("provider")=="supralinux",f"{node}: dependency manifest selected provider")
    req(dep.get("provider_audit",{}).get("status")=="PASS",f"{node}: dependency provider-audit PASS")

capture=m.get("reference_capture",{})
req(capture.get("claim")=="packaging-reference-snapshot-only" and capture.get("authoritative") is False,"reference capture non-authority")
req(capture.get("package_state_effect")=="none","reference capture package-state semantics")
req(capture.get("ubuntu_suite")=="resolute" and capture.get("debian_suite")=="sid","reference suites")
req(capture.get("debian_selection_policy")=="prefer-exact-kde-6.30.0-otherwise-newest-not-newer","Debian reference selection policy")

if m.get("state")=="reference-capture-pending":
    req(capture.get("status")=="pending-ci" and capture.get("evidence") is None,"pending reference capture state")
    req(all(c.get("contract_state")=="reference-capture-pending" for c in components.values()),"pending component contracts")
    req(m.get("materialization",{}).get("status")=="not-authorized-before-reference-capture","materialization blocked before capture")
else:
    req(capture.get("status")=="PASS","reference capture PASS lifecycle")
    ev=capture.get("evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_state_effect")=="none","reference capture PASS evidence")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"reference capture run/job evidence")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"reference capture artifact evidence")
    refs=m.get("technical_references",{})
    req(set(refs)==set(expected),"captured technical reference set")
    for node,r in refs.items():
        req(r.get("ubuntu",{}).get("source_package")==expected[node]["source"],f"{node}: captured Ubuntu source")
        req(r.get("debian",{}).get("source_package")==expected[node]["source"],f"{node}: captured Debian source")
        req(r.get("debian",{}).get("upstream_version")=="6.30.0",f"{node}: Debian exact KDE 6.30 technical reference")
        for side in ("ubuntu","debian"):
            rr=r.get(side,{})
            req(isinstance(rr.get("version"),str) and rr.get("version"),f"{node}: {side} version")
            req(isinstance(rr.get("binary_packages"),list) and rr.get("binary_packages"),f"{node}: {side} binary package set")
            req(isinstance(rr.get("checksums_sha256"),list) and rr.get("checksums_sha256"),f"{node}: {side} source checksums")
    if m.get("state")=="reference-capture-pass":
        req(all(c.get("contract_state")=="reference-capture-pass" for c in components.values()),"captured component contract state")
        req(m.get("materialization",{}).get("status")=="not-authorized-before-contract-review","materialization blocked until contract review")

sc=tier3.get("support_components",{})
req(sc.get("provider_audit")=="PASS","Tier3 canonical support provider audit")
req(sc.get("next_gate") in {"support-package-contracts","support-contract-reference-capture","support-contract-tree-capture","support-contract-review"},"Tier3 support contract next gate")
req(m.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

for path in (
 "scripts/run-kde-tier3-support-contract-reference.sh",
 "scripts/kde-tier3-support-contract-reference-needed.sh",
 "scripts/test-kde-tier3-support-contract-reference-scope.sh",
 ".github/workflows/kde-tier3-support-contract-reference.yml",
 "docs/kde-tier3-support-package-contracts.md",
):
    req((ROOT/path).exists(),f"missing support contract reference component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 support package-contract preparation: PASS")
print("state="+m["state"])
print("components="+",".join(m["selected_components"]))
