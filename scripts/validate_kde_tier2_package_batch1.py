#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
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
req(c.get("schema")==2 and c.get("batch")=="tier2-batch-1" and c.get("lane")=="core-authorization","Batch1 identity")
req(c.get("state") in {"prepared-pending-build","remediation-pending-build","PASS"},"Batch1 campaign state")
req(c.get("selected_nodes")==["kauth"],"Batch1 must contain only KAuth")
n=c.get("nodes",{}).get("kauth",{})
req(n.get("upstream_version")=="6.30.0" and n.get("source_package")=="kf6-kauth","KAuth identity")
req(n.get("package_version")=="6.30.0-0supralinux3","KAuth current revision")
req(n.get("source_sha256")=="60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9","KAuth source hash")
req(n.get("kde_framework_build_dependencies")==["KCoreAddons","KWindowSystem"],"KAuth predecessors")
req(n.get("backend_profile")=={"KAUTH_BACKEND_NAME":"POLKITQT6-1","KAUTH_HELPER_BACKEND_NAME":"DBUS","fake_backend_allowed":False},"KAuth backend profile")
ref=c.get("technical_references",{}).get("debian_6_30",{})
req(ref.get("role")=="technical-packaging-reference-only" and ref.get("version")=="6.30.0-1","Debian reference role/version")
req(ref.get("debian_tar_sha256")=="f304bd772cf958ca9dccab78ad33e12f8e2f7bf0b038999e629cf270bb068fc3","Debian reference tar hash")
req(ref.get("imported_file_sha256")=="77ab200ea8f5e9335831ef021dd2e446598b95d886d13237e91ea69e25812259","Debian symbols reference hash")
adj=ref.get("symbols_adjustment",{})
req(adj.get("tag")=="optional=private","KAuth symbols adjustment tag")
req(adj.get("symbols")==["_ZTIN5KAuth11AuthBackend7PrivateE@Base 6.23.0","_ZTVN5KAuth11AuthBackend7PrivateE@Base 6.23.0"],"KAuth private symbol adjustment set")

tier={x["id"]:x for x in t.get("nodes",[])}
req(tier.get("kauth",{}).get("state")=="pending","KAuth canonical state remains pending before PASS")
req(tier.get("kauth",{}).get("packaging",{}).get("state")=="remediation-pending-build","KAuth packaging readiness")
req(tier.get("kmime",{}).get("package_identity",{}).get("package_version_candidate") is None,"KMime must remain decision-gated")
req(g.get("nodes",{}).get("kauth",{}).get("readiness")=="remediation-pending-build","KAuth discovery readiness")
req(g.get("nodes",{}).get("kmime",{}).get("readiness")=="compatibility-decision-required","KMime discovery decision gate")

package=ROOT/"packages/kde/kauth/debian"
for rel in ("changelog","control","copyright","README.source","rules","source/format","patches/series","patches/helper-install-dir-cache.patch","libkf6auth-data.install","libkf6auth-dev.install","libkf6auth-dev-bin.install","libkf6authcore6.install","libkf6auth-data.lintian-overrides","upstream/signing-key.asc"):
    req((package/rel).exists(),f"KAuth packaging file missing: {rel}")
if (package/"upstream/signing-key.asc").exists():
    req(hashlib.sha256((package/"upstream/signing-key.asc").read_bytes()).hexdigest()==n.get("signing_key",{}).get("sha256"),"KAuth signing key hash")
control=text("packages/kde/kauth/debian/control"); rules=text("packages/kde/kauth/debian/rules")
for token in ("libkf6coreaddons-dev (>= 6.30.0~)","libkf6windowsystem-dev (>= 6.30.0~)","libpolkit-qt6-1-dev (>= 0.200.0-2~)","qt6-base-dev (>= 6.9.0~)"):
    req(token in control,f"KAuth Build-Depends missing {token}")
for token in ("-DKAUTH_BACKEND_NAME=POLKITQT6-1","-DKAUTH_HELPER_BACKEND_NAME=DBUS","-DBUILD_TESTING=ON","dbus-run-session","xvfb-run"):
    req(token in rules,f"KAuth rules missing {token}")
req("FAKE" not in rules.upper(),"KAuth package rules must not select Fake backend")

workflow=text(".github/workflows/kde-tier2-package-batch1.yml"); router=text(".github/workflows/pr-ci-router.yml")
scope=text("scripts/kde-tier2-package-batch1-needed.sh"); scope_test=text("scripts/test-kde-tier2-package-batch1-scope.sh"); runner=text("scripts/run-kde-tier2-package-batch1-preflight.sh")
req("workflow_call:" in workflow and "workflow_dispatch:" in workflow,"KAuth workflow reusable/manual")
req("run-id: '35122522242'" in workflow and "artifact-ids: '10457958023'" in workflow,"KCoreAddons retained artifact")
req("run-id: '35047623320'" in workflow and "artifact-ids: '10428130399'" in workflow,"KWindowSystem retained artifact")
req("scripts/kde-tier2-package-batch1-needed.sh" in workflow and "scripts/run-kde-tier2-package-batch1-preflight.sh" in workflow,"KAuth workflow scope/runner")
req("uses: ./.github/workflows/kde-tier2-package-batch1.yml" in router,"PR router must invoke Tier2 Batch1")
for token in ("--extra-package","POLKITQT6-1","development-contract-artifact","consumer-runtime-closure","libkf6authcore6.symbols","DEBIAN_REF_SHA","DEBIAN_SYMBOLS_SHA","optional=private","abi-exports.txt"):
    req(token in runner,f"KAuth runner missing {token}")
req("packages/kde/kauth/*" in scope and "kde-tier2-package-campaign-batch1.json" in scope,"KAuth scope inputs")
req("KDE Tier 2 Batch 1 scope selector: PASS" in scope_test,"KAuth scope test marker")

history=a.get("real_attempts",{}).get("kauth",[])
req(len(history)==2,"KAuth remediation state must retain attempts 1-2 before rerun")
if len(history)==2:
    h1,h2=history
    req(h1.get("attempt")==1 and h1.get("package_version")=="6.30.0-0supralinux1","KAuth attempt 1 identity")
    req(h1.get("workflow_run")==35496293561 and h1.get("job_id")==106039776267 and h1.get("artifact_id")==10600690671,"KAuth attempt 1 evidence identity")
    req(h1.get("artifact_sha256")=="8387279d8cdadd05cf73c2c16177f1d2635a331648638ca3397cef77d04c1ac3","KAuth attempt 1 artifact digest")
    req(h1.get("package_attempted") is True and h1.get("result")=="FAIL" and h1.get("stage")=="source-package" and h1.get("sbuild_started") is False,"KAuth attempt 1 semantics")
    req(h2.get("attempt")==2 and h2.get("package_version")=="6.30.0-0supralinux2","KAuth attempt 2 identity")
    req(h2.get("workflow_run")==35496445770 and h2.get("job_id")==106040197856 and h2.get("artifact_id")==10601410551,"KAuth attempt 2 evidence identity")
    req(h2.get("artifact_sha256")=="4ea7588f1749ce7588cc06fc6bc9dc80350d7fc270bb30688ef173ee6262cfc9","KAuth attempt 2 artifact digest")
    req(h2.get("rootfs_sha256")=="bf90d45c1b750369d482757a4521ea3578a5ef8e10835bf008b258ffad49cbcf","KAuth attempt 2 rootfs")
    req(h2.get("package_attempted") is True and h2.get("result")=="FAIL" and h2.get("stage")=="sbuild-dh_makeshlibs" and h2.get("sbuild_started") is True,"KAuth attempt 2 semantics")
    req(h2.get("tests")=="6/6 PASS" and h2.get("technical_reference_symbols_sha256")=="77ab200ea8f5e9335831ef021dd2e446598b95d886d13237e91ea69e25812259","KAuth attempt 2 passed-test/reference evidence")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 1 KAuth preparation: PASS")
print("KAuth 6.30.0 remediation prepared after retained source-package FAIL; backend/dependencies unchanged")
print("KMime remains compatibility-decision-required")
