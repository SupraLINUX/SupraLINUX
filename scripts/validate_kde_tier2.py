#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def req(v,m):
    if not v:
        errors.append(m)

def load(path):
    return json.loads((ROOT/path).read_text())

tier2=load("manifests/kde-frameworks-tier2.json")
deps=load("manifests/kde-frameworks-tier2-dependencies.json")
discovery=load("manifests/kde-tier2-global-discovery.json")
tier1=load("manifests/kde-frameworks-tier1.json")

req(tier2.get("schema")==1 and tier2.get("authority")=="kde-upstream","Tier2 identity/authority")
req(tier2.get("frameworks_series")=="6.30.0" and tier2.get("tier")==2,"Tier2 series/tier")
req(tier2.get("tier_reference")=="https://api.kde.org/","Tier2 classification reference")
nodes={n.get("id"):n for n in tier2.get("nodes",[])}
req(set(nodes)=={"kauth","kmime"} and len(tier2.get("nodes",[]))==2,"KDE Tier2 node set must be exactly KAuth + KMime")
expected_hashes={
    "kauth":"60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9",
    "kmime":"2969a5ef484e98f91bf78e88c98a9d613bdd3bb86ac154ceece0557b70f373bc",
}
for node,sha in expected_hashes.items():
    n=nodes[node]
    req(n.get("upstream_version")=="6.30.0",f"{node}: upstream version")
    req(n.get("source_sha256")==sha,f"{node}: source SHA")
    req(n.get("state")=="pending" and n.get("packaging",{}).get("state")=="pending",f"{node}: discovery must not promote package state")

req(nodes["kauth"].get("depends_on")==["extra-cmake-modules","kcoreaddons","kwindowsystem"],"KAuth selected DAG predecessors")
req(nodes["kmime"].get("depends_on")==["extra-cmake-modules","kcodecs"],"KMime DAG predecessors")
req(nodes["kauth"]["package_identity"].get("package_version_candidate")=="6.30.0-0supralinux1","KAuth candidate revision")
req(nodes["kmime"]["package_identity"].get("package_version_candidate") is None,"KMime Debian revision must remain undecided")

req(deps.get("schema")==1 and deps.get("frameworks")=="6.30.0" and deps.get("tier")==2,"Tier2 dependency manifest identity")
p=deps.get("external_requirements",{}).get("polkitqt6-1",{})
req(p.get("minimum")=="0.112.0" and p.get("provider_packages")==["libpolkit-qt6-1-dev"] and p.get("provider_version")=="0.200.0-4ubuntu1","KAuth Polkit provider mapping")
kp=deps.get("nodes",{}).get("kauth",{}).get("selected_linux_profile",{})
req(kp.get("auth_backend")=="POLKITQT6-1" and kp.get("helper_backend")=="DBUS" and kp.get("fake_backend_allowed") is False,"KAuth real Linux backend profile")

pred=deps.get("retained_predecessors",{})
expected_pred={
 "kcoreaddons":("6.30.0-0supralinux4",10457958023,"c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64"),
 "kwindowsystem":("6.30.0-0supralinux4",10428130399,"9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272"),
 "kcodecs":("6.30.0-0supralinux4",10305050385,"d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45"),
}
for node,(version,artifact,digest) in expected_pred.items():
    x=pred.get(node,{})
    req(x.get("state")=="PASS" and x.get("version")==version and x.get("artifact_id")==artifact and x.get("artifact_sha256")==digest,f"{node}: retained predecessor evidence")

req(sum(n.get("state")=="PASS" for n in tier1.get("nodes",[]))==29,"Tier2 requires 29/29 Tier1 PASS")
req(not any(n.get("state")!="PASS" for n in tier1.get("nodes",[])),"Tier2 requires no non-PASS Tier1 nodes")

req(discovery.get("nodes",{}).get("kauth",{}).get("readiness")=="package-lane-pending","KAuth discovery readiness")
req(discovery.get("nodes",{}).get("kmime",{}).get("readiness")=="compatibility-decision-required","KMime must remain decision-gated")
req(discovery.get("state_model",{}).get("note","").startswith("These are planning/readiness states"),"readiness must not be confused with package BLOCKED")

# Debian version ordering is an independently executable fact: a naive
# Frameworks version would not supersede Ubuntu's PIM/Gear version.
cmp=subprocess.run(["dpkg","--compare-versions","6.30.0-0supralinux1","lt","25.12.3-0ubuntu1"])
req(cmp.returncode==0,"KMime naive Frameworks version must sort below Ubuntu 25.12.3 reference")

adr=(ROOT/"docs/decisions/ADR-0002-kmime-frameworks-transition.md").read_text()
for token in ("decision required","KPim6::Mime","KF6::Mime","libKPim6Mime.so.6","libKF6Mime.so.6","Pending human approval"):
    req(token in adr,f"KMime ADR missing {token}")
req("selected strategy" not in adr.lower(),"KMime ADR must not silently claim a selected strategy")

doc=(ROOT/"docs/kde-tier2.md").read_text()
for token in ("KAuth","KMime","29 PASS / 0 pending","POLKITQT6-1","compatibility-decision-required"):
    req(token in doc,f"Tier2 documentation missing {token}")

policy=(ROOT/".github/workflows/repository-policy.yml").read_text()
req("python3 scripts/validate_kde_tier2.py" in policy,"Repository Policy must execute Tier2 validator")

if errors:
    for e in errors:
        print(f"ERROR: {e}",file=sys.stderr)
    raise SystemExit(1)

print("KDE Frameworks 6.30 Tier 2 discovery validation: PASS")
print("Nodes: KAuth package-lane-pending; KMime compatibility-decision-required")
print("Canonical package state: 0 PASS / 2 pending / 0 FAIL / 0 BLOCKED")
