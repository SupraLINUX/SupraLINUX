#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

tier2=load("manifests/kde-frameworks-tier2.json")
deps=load("manifests/kde-frameworks-tier2-dependencies.json")
discovery=load("manifests/kde-tier2-global-discovery.json")
tier1=load("manifests/kde-frameworks-tier1.json")
dag=load("manifests/kde-dag.json")

req(tier2.get("schema")==1 and tier2.get("authority")=="kde-upstream","Tier2 identity/authority")
req(tier2.get("frameworks_series")=="6.30.0" and tier2.get("tier")==2,"Tier2 series/tier")
nodes={n.get("id"):n for n in tier2.get("nodes",[])}
req(set(nodes)=={"kauth","kmime"},"Tier2 node set")
for node,sha in {
 "kauth":"60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9",
 "kmime":"2969a5ef484e98f91bf78e88c98a9d613bdd3bb86ac154ceece0557b70f373bc",
}.items():
    req(nodes[node].get("upstream_version")=="6.30.0",f"{node}: upstream version")
    req(nodes[node].get("source_sha256")==sha,f"{node}: source SHA")

k=nodes["kauth"]; m=nodes["kmime"]
req(k.get("state")=="PASS","KAuth canonical PASS")
kp=k.get("packaging",{})
req(kp.get("state")=="PASS" and kp.get("package_version")=="6.30.0-0supralinux3" and kp.get("downstream_eligible") is True,"KAuth packaging PASS")
req(k["package_identity"].get("package_version_candidate")==kp.get("package_version"),"KAuth package identity/current revision")
kev=[x for x in kp.get("evidence",[]) if x.get("result")=="PASS"]
req(len(kev)==1,"KAuth exactly one retained PASS")
if kev:
    e=kev[0]
    req(e.get("workflow_run")==35497461178 and e.get("job_id")==106043001431 and e.get("artifact_id")==10601382235,"KAuth PASS run/job/artifact")
    req(e.get("artifact_sha256")=="443a47a67188a52faae6c20b03c2c53203d5a9386dbbb5765af4f69e0cd1744b","KAuth PASS artifact digest")
    req(e.get("rootfs_sha256")=="15113b108b939e2575758c6696fc34808dfa925fa2dd3cc5e6c13e65e7be4668","KAuth rootfs")
    req(e.get("tests")=="6/6 PASS" and e.get("lintian")=="PASS-errors" and e.get("abi_soname")=="libKF6AuthCore.so.6" and e.get("abi_export_count")==118,"KAuth tests/Lintian/ABI")
    req(e.get("consumer_smoke")=="PASS" and e.get("apt_check")=="PASS" and e.get("development_contract")=="PASS","KAuth runtime/development gates")
req(m.get("state")=="pending" and m.get("packaging",{}).get("state")=="pending","KMime remains pending")
req(m["package_identity"].get("package_version_candidate") is None,"KMime version remains undecided")

req(k.get("depends_on")==["extra-cmake-modules","kcoreaddons","kwindowsystem"],"KAuth selected DAG predecessors")
req(m.get("depends_on")==["extra-cmake-modules","kcodecs"],"KMime DAG predecessors")
p=deps.get("external_requirements",{}).get("polkitqt6-1",{})
req(p.get("provider_version")=="0.200.0-4ubuntu1","Polkit provider")
req(sum(n.get("state")=="PASS" for n in tier1.get("nodes",[]))==29 and not any(n.get("state")!="PASS" for n in tier1.get("nodes",[])),"Tier1 precondition")

req(set(discovery.get("nodes",{}))=={"kmime"},"Only KMime may remain active in Tier2 discovery")
req(discovery["nodes"]["kmime"].get("readiness")=="compatibility-decision-required","KMime decision gate")
snap=discovery.get("promoted_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(1,1,0,0),"Tier2 promoted snapshot")
done=discovery.get("completed_nodes",{}).get("kauth",{})
req(done.get("state")=="PASS" and done.get("package_version")=="6.30.0-0supralinux3" and done.get("artifact_id")==10601382235 and done.get("downstream_eligible") is True,"KAuth completed discovery record")

kd=dag.get("nodes",{}).get("kauth",{})
req(kd.get("tier")==2 and kd.get("state")=="PASS" and kd.get("package_version")=="6.30.0-0supralinux3" and kd.get("downstream_eligible") is True,"KAuth canonical DAG promotion")

cmp=subprocess.run(["dpkg","--compare-versions","6.30.0-0supralinux1","lt","25.12.3-0ubuntu1"])
req(cmp.returncode==0,"KMime naive Frameworks version ordering fact")
adr=(ROOT/"docs/decisions/ADR-0002-kmime-frameworks-transition.md").read_text()
for token in ("decision required","KPim6::Mime","KF6::Mime","libKPim6Mime.so.6","libKF6Mime.so.6","Pending human approval"):
    req(token in adr,f"KMime ADR missing {token}")
doc=(ROOT/"docs/kde-tier2.md").read_text()
for token in ("KAuth","KMime","1 PASS / 1 pending","POLKITQT6-1","compatibility-decision-required"):
    req(token in doc,f"Tier2 doc missing {token}")
policy=(ROOT/".github/workflows/repository-policy.yml").read_text()
req("python3 scripts/validate_kde_tier2.py" in policy,"Repository Policy Tier2 gate")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Frameworks 6.30 Tier 2 discovery validation: PASS")
print("Canonical Tier 2: 1 PASS / 1 pending / 0 FAIL / 0 BLOCKED")
print("KAuth PASS/downstream-eligible; KMime compatibility-decision-required")
