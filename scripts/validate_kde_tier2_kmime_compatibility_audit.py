#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
m=json.loads((ROOT/"manifests/kde-tier2-kmime-compatibility-audit.json").read_text())
tier2=json.loads((ROOT/"manifests/kde-frameworks-tier2.json").read_text())
plan=json.loads((ROOT/"manifests/kde-tier2-campaign-plan.json").read_text())
km=next(x for x in tier2["nodes"] if x["id"]=="kmime")

req(m.get("schema")==1 and m.get("audit")=="kmime-legacy-provider-coinstallation","audit identity")
req(m.get("state") in {"pending-ci","PASS"},"audit state")
req(m.get("provider_platform")=="ubuntu-resolute","provider platform")
req(m.get("frameworks_authority")=="kde-upstream-6.30.0","KDE authority")
req(m.get("package_state_effect")=="none","audit package-state semantics")
fe=m.get("framework_build_evidence",{})
req(fe.get("workflow_run")==35687831684 and fe.get("run_attempt")==2 and fe.get("job_id")==106619132039,"framework trigger build binding")
req(fe.get("artifact_id")==10677716050 and len(fe.get("artifact_sha256",""))==64,"framework artifact binding")
req(fe.get("package_version")=="6.30.0-0supralinux1","framework package version")
req(fe.get("binary_packages")==["libkf6mime-data","libkf6mime-dev","libkf6mime6"],"framework binary set")
req(fe.get("observed_gates",{}).get("upstream_tests")=="17/17 PASS","framework upstream tests evidence")
legacy=m.get("legacy_reference",{})
req(legacy.get("source_package")=="kmime" and legacy.get("version")=="25.12.3-0ubuntu1","legacy source/version")
req(legacy.get("binary_packages")==["libkmime-data","libkmime-dev","libkpim6mime6"],"legacy binary set")
req(legacy.get("runtime_install_set")==["libkmime-data","libkpim6mime6"],"legacy runtime install set")
req(legacy.get("runtime_soname")=="libKPim6Mime.so.6","legacy runtime SONAME")
fc=m.get("framework_contract",{})
req(fc.get("runtime_soname")=="libKF6Mime.so.6" and fc.get("authoritative_for_kde") is True,"Frameworks authority/SONAME")
req(m.get("trigger_observation",{}).get("removed_framework_packages")==["libkf6mime-data","libkf6mime-dev","libkf6mime6"],"observed solver removal set")
required=set(m.get("required_checks",[]))
req({"depends-conflicts-breaks-replaces-provides","pairwise-file-overlap","overlap-content-sha256","runtime-soname-separation","apt-solver-simulation"} <= required,"audit required checks")
req(km.get("state")=="pending" and km.get("planning",{}).get("readiness")=="compatibility-provider-required","canonical KMime compatibility-provider state")
req(plan.get("compatibility_provider_required")==["kmime"] and "kmime" not in plan.get("build_queue",[]),"campaign compatibility queue")
for path in (
    "scripts/run-kde-tier2-kmime-compatibility-audit.sh",
    ".github/workflows/kde-tier2-kmime-compatibility-audit.yml",
    "docs/kde-tier2-kmime-compatibility-audit.md",
):
    req((ROOT/path).exists(),f"missing compatibility audit component: {path}")
if m.get("state")=="PASS":
    result=m.get("result",{})
    ev=result.get("evidence",{})
    req(result.get("audit_result")=="PASS","audit PASS evidence")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"audit run/job evidence")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"audit artifact evidence")
    req(result.get("package_state_effect")=="none","audit PASS package-state semantics")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 KMime compatibility-provider audit definition: PASS")
print("state="+m["state"])
