#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
def text(p): return (ROOT/p).read_text()

c=load("manifests/kde-tier2-package-campaign-batch1.json")
a=load("manifests/kde-tier2-package-batch1-attempts.json")
t=load("manifests/kde-frameworks-tier2.json")
g=load("manifests/kde-tier2-global-discovery.json")
d=load("manifests/kde-dag.json")
req(c.get("schema")==2 and c.get("batch")=="tier2-batch-1" and c.get("lane")=="core-authorization","Batch1 identity")
req(c.get("state")=="PASS","Batch1 campaign PASS")
req(c.get("canonical_snapshot")=={"tier1":"29 PASS / 0 pending / 0 current FAIL / 0 BLOCKED","tier2":"0 PASS / 2 pending / 0 current FAIL / 0 BLOCKED"},"historical pre-Batch1 snapshot")
req(c.get("canonical_promotion")=={"status":"promotion-candidate","tier2":"1 PASS / 1 pending / 0 current FAIL / 0 BLOCKED","dag_nodes":["kauth"]},"Batch1 historical promotion record")
ctx=c.get("inventory_context",{})
req(ctx.get("status")=="historical-incomplete-inventory" and ctx.get("corrected_inventory_count")==15 and ctx.get("corrected_current_state")=="1 PASS / 14 pending / 0 current FAIL / 0 BLOCKED","Batch1 inventory correction context")
post=c.get("post_campaign_inventory_correction",{})
req(post.get("kAuth_pass_unchanged") is True and post.get("additional_pending_nodes")==13 and post.get("kmime_state")=="compatibility-decision-required" and post.get("package_state_effect")=="none","Batch1 post-campaign correction semantics")
n=c.get("nodes",{}).get("kauth",{})
req(n.get("package_version")=="6.30.0-0supralinux3" and n.get("state")=="PASS" and n.get("last_result")=="PASS" and n.get("downstream_eligible") is True,"KAuth campaign PASS")
pe=n.get("pass_evidence",{})
req(pe.get("workflow_run")==35497461178 and pe.get("job_id")==106043001431 and pe.get("artifact_id")==10601382235,"KAuth pass identity")
req(pe.get("artifact_sha256")=="443a47a67188a52faae6c20b03c2c53203d5a9386dbbb5765af4f69e0cd1744b","KAuth pass artifact digest")
req(pe.get("rootfs_sha256")=="15113b108b939e2575758c6696fc34808dfa925fa2dd3cc5e6c13e65e7be4668","KAuth pass rootfs")
req(pe.get("tests")=="6/6 PASS" and pe.get("lintian")=="PASS-errors" and pe.get("abi_soname")=="libKF6AuthCore.so.6" and pe.get("abi_export_count")==118,"KAuth build/test ABI gates")
req(pe.get("backend")=="POLKITQT6-1" and pe.get("helper_backend")=="DBUS","KAuth backend gates")
req(pe.get("symbols_reference_sha256")=="77ab200ea8f5e9335831ef021dd2e446598b95d886d13237e91ea69e25812259" and pe.get("symbols_adjusted_sha256")=="b8cf2fa877c94255f015cee08b89816d538cba23f1064d0360a329189fee0b78","KAuth symbols evidence")
req(pe.get("consumer_smoke")=="PASS" and pe.get("apt_check")=="PASS" and pe.get("development_contract")=="PASS" and pe.get("source_development_contract")=="PASS","KAuth final gates")

ref=c.get("technical_references",{}).get("debian_6_30",{})
req(ref.get("debian_tar_sha256")=="f304bd772cf958ca9dccab78ad33e12f8e2f7bf0b038999e629cf270bb068fc3" and ref.get("imported_file_sha256")=="77ab200ea8f5e9335831ef021dd2e446598b95d886d13237e91ea69e25812259","Debian technical reference")
req(ref.get("symbols_adjustment",{}).get("symbols")==["_ZTIN5KAuth11AuthBackend7PrivateE@Base 6.23.0","_ZTVN5KAuth11AuthBackend7PrivateE@Base 6.23.0"],"private-only symbols adjustment")

tier={x["id"]:x for x in t.get("nodes",[])}
expected_ids={"kauth","kcolorscheme","kcompletion","kcontacts","kcrash","kdeclarative","kfilemetadata","knotifications","kpackage","kpty","kservice","kstatusnotifieritem","kunitconversion","syndication","kmime"}
req(set(tier)==expected_ids,"current Tier2 inventory must contain 15 upstream nodes")
kt=tier["kauth"]
req(kt.get("state")=="PASS" and kt.get("packaging",{}).get("state")=="PASS" and kt["packaging"].get("downstream_eligible") is True,"KAuth Tier2 canonical PASS")
req(tier["kmime"].get("state")=="pending" and tier["kmime"].get("package_identity",{}).get("package_version_candidate") is None,"KMime remains pending/undecided")
active=g.get("nodes",{})
req(set(active)==expected_ids-{"kauth"},"current Tier2 active discovery must contain 14 pending nodes")
req(active["kmime"].get("readiness")=="compatibility-decision-required","KMime decision gate")
for node in sorted(expected_ids-{"kauth","kmime"}):
    req(active[node].get("readiness")==tier[node].get("planning",{}).get("readiness"),f"{node}: later readiness must match canonical Tier2 planning")
req(g.get("promoted_snapshot")=={"pass":1,"pending":14,"current_fail":0,"blocked":0},"current Tier2 snapshot")
req(g.get("completed_nodes",{}).get("kauth",{}).get("artifact_id")==10601382235,"KAuth completed discovery evidence")
req(d.get("nodes",{}).get("kauth",{}).get("state")=="PASS" and d["nodes"]["kauth"].get("downstream_eligible") is True,"KAuth DAG PASS")

history=a.get("real_attempts",{}).get("kauth",[])
req(len(history)==3,"KAuth must retain exactly three real attempts")
if len(history)==3:
    h1,h2,h3=history
    req(h1.get("attempt")==1 and h1.get("result")=="FAIL" and h1.get("stage")=="source-package","attempt1")
    req(h2.get("attempt")==2 and h2.get("result")=="FAIL" and h2.get("tests")=="6/6 PASS" and h2.get("stage")=="sbuild-dh_makeshlibs","attempt2")
    req(h3.get("attempt")==3 and h3.get("package_version")=="6.30.0-0supralinux3" and h3.get("result")=="PASS" and h3.get("stage")=="complete","attempt3 identity")
    req(h3.get("workflow_run")==35497461178 and h3.get("job_id")==106043001431 and h3.get("artifact_id")==10601382235,"attempt3 evidence")
    req(h3.get("artifact_sha256")=="443a47a67188a52faae6c20b03c2c53203d5a9386dbbb5765af4f69e0cd1744b" and h3.get("rootfs_sha256")=="15113b108b939e2575758c6696fc34808dfa925fa2dd3cc5e6c13e65e7be4668","attempt3 hashes")
    req(h3.get("tests")=="6/6 PASS" and h3.get("lintian")=="PASS-errors" and h3.get("consumer_smoke")=="PASS" and h3.get("apt_check")=="PASS" and h3.get("development_contract")=="PASS","attempt3 gates")

infra=a.get("infrastructure_incidents",[])
req(any(x.get("workflow_run")==35497460988 and x.get("package_state_effect")=="none" for x in infra),"scope-test INFRA incident retained")
req(any(x.get("workflow_run")==35497248610 and x.get("package_attempted") is False for x in infra),"superseded queued-run incident retained")

scope=text("scripts/kde-tier2-package-batch1-needed.sh")
scope_test=text("scripts/test-kde-tier2-package-batch1-scope.sh")
req("kde-tier2-package-batch1-attempts.json" in scope and "package_attempted" in scope,"unattempted-revision rescue scope")
req("KDE Tier 2 Batch 1 scope selector: PASS" in scope_test and "mkdir -p docs" in scope_test,"scope test final contract")

doc=text("docs/kde-tier2-package-batch1.md")
for token in ("KAuth PASS","10601382235","443a47a67188a52faae6c20b03c2c53203d5a9386dbbb5765af4f69e0cd1744b","6/6 PASS","1 PASS / 14 pending"):
    req(token in doc,f"Batch1 docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 1 KAuth canonical promotion: PASS")
print("KAuth 6.30.0-0supralinux3 PASS/downstream-eligible")
print("Tier 2 current inventory: 1 PASS / 14 pending; KAuth evidence unchanged")
