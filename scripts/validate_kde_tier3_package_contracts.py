#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier3-package-contracts.json")
t=load("manifests/kde-frameworks-tier3.json")
a=load("manifests/kde-tier3-provider-audit.json")
canonical=[n["id"] for n in t["nodes"]]
nodes={n["id"]:n for n in t["nodes"]}

req(c.get("schema")==1,"Tier3 package-contract schema")
req(c.get("state") in {"reference-capture-pending","reference-capture-pass","packaging-tree-pending","packaging-tree-pass","contract-review-pass","contracts-ready","materialized"},"Tier3 package-contract lifecycle")
req(c.get("source_authority")=="kde-upstream" and c.get("packaging_authority")=="supralinux","Tier3 contract authority boundary")
req(c.get("frameworks_series")=="6.30.0","Tier3 contract Frameworks series")
req(c.get("selected_nodes")==canonical and len(canonical)==20,"Tier3 contract canonical node set")
req(set(c.get("nodes",{}))==set(canonical),"Tier3 contract node map")
req(a.get("status")=="PASS","Tier3 contracts require provider audit PASS")
req(all(a["components"][x].get("provider_decision")=="supralinux-required" for x in canonical),"Tier3 contracts require SupraLINUX provider")

refs=c.get("compatibility_reference",{})
req(refs.get("ubuntu",{}).get("series")=="resolute" and refs.get("ubuntu",{}).get("role")=="technical-reference-only","Ubuntu technical reference")
req(refs.get("debian",{}).get("series")=="sid" and refs.get("debian",{}).get("role")=="technical-reference-only","Debian technical reference")
rc=c.get("reference_capture",{})
req(rc.get("claim")=="packaging-reference-snapshot-only" and rc.get("authoritative") is False,"reference capture non-authority")
req(rc.get("package_state_effect")=="none","reference capture package-state semantics")
req(rc.get("selection_policy")=="prefer-exact-kde-6.30.0-otherwise-newest-not-newer","reference selection policy")

for node in canonical:
    x=c["nodes"][node]
    n=nodes[node]
    req(x.get("upstream_version")=="6.30.0" and x.get("source_sha256")==n.get("source_sha256"),f"{node}: KDE source linkage")
    req(x.get("source_package")==f"kf6-{node}",f"{node}: source package")
    req(x.get("provider")=="supralinux",f"{node}: provider selection")
    req(x.get("contract_state") in {"reference-capture-pending","reference-capture-pass","packaging-tree-pass","review-pending","review-pass","contract-ready","materialized"},f"{node}: contract lifecycle")
    packaging=n.get("packaging",{})
    if n.get("state")=="PASS":
        req(packaging.get("state")=="PASS" and packaging.get("downstream_eligible") is True,f"{node}: promoted packaging PASS")
    elif node=="knewstuff" and packaging.get("state")=="runtime-validation-required":
        req(n.get("state")=="pending" and packaging.get("downstream_eligible") is False,f"{node}: runtime validation remains pending")
    else:
        req(n.get("state")=="pending",f"{node}: package state pending")
        req(packaging.get("state")=="pending" and packaging.get("downstream_eligible") is False,f"{node}: packaging remains pending")
    planning=n.get("planning",{})
    req(planning.get("provider_audit")=="PASS" and planning.get("provider")=="supralinux",f"{node}: provider audit canonical linkage")
    req(planning.get("package_contract") in {"required","reference-capture-pending","reference-capture-pass","packaging-tree-pending","packaging-tree-pass","review-pending","review-pass","ready","not-materialized","materialized","retained-pass"},f"{node}: canonical package-contract lifecycle")

if c.get("state")=="reference-capture-pending":
    req(rc.get("status")=="pending-ci" and rc.get("evidence") is None,"pending reference capture state")
    req(all(x.get("contract_state")=="reference-capture-pending" for x in c["nodes"].values()),"pending node contracts")
    req(c.get("execution_request",{}).get("status")=="requested","pending reference execution request")
else:
    req(rc.get("status")=="PASS","reference capture PASS state")
    ev=rc.get("evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_state_effect")=="none","reference capture evidence semantics")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"reference capture run/job")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"reference capture artifact")
    req(len(ev.get("snapshot_sha256",""))==64,"reference capture snapshot digest")
    for node in canonical:
        x=c["nodes"][node]
        tr=x.get("technical_references",{})
        for side in ("ubuntu","debian"):
            rr=tr.get(side,{})
            req(rr.get("source_package")==f"kf6-{node}",f"{node}/{side}: source identity")
            req(isinstance(rr.get("version"),str) and rr.get("version"),f"{node}/{side}: version")
            req(isinstance(rr.get("binary_packages"),list) and rr.get("binary_packages"),f"{node}/{side}: binary packages")
            for prefix in ("dsc","debian_tar","orig_tar"):
                req(isinstance(rr.get(prefix+"_file"),str) and rr.get(prefix+"_file"),f"{node}/{side}: {prefix} file pin")
                req(len(rr.get(prefix+"_sha256",""))==64,f"{node}/{side}: {prefix} SHA-256 pin")
        req(tr["ubuntu"]["binary_packages"]==tr["debian"]["binary_packages"],f"{node}: Ubuntu/Debian binary package identity")
        req(tr["debian"].get("upstream_version")=="6.30.0",f"{node}: exact Debian KDE 6.30 reference")
        req(tr["debian"].get("orig_tar_sha256")==x.get("source_sha256"),f"{node}: Debian orig matches KDE authority")
    req(rc.get("evidence",{}).get("debian_exact_selected_kde")==20,"all Debian references exact KDE 6.30")
    req(c.get("execution_request",{}).get("status")=="consumed","reference execution request consumed")

req(c.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
for path in (
 "scripts/run-kde-tier3-contract-reference-snapshot.sh",
 "scripts/kde-tier3-contract-reference-needed.sh",
 "scripts/test-kde-tier3-contract-reference-scope.sh",
 ".github/workflows/kde-tier3-contract-reference.yml",
 "docs/kde-tier3-package-contracts.md",
):
    req((ROOT/path).exists(),f"missing Tier3 contract-reference component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 package-contract definition: PASS")
print("state="+c["state"])
print("nodes=20")
