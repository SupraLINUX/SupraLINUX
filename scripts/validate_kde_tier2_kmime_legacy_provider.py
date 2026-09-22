#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v:
        errors.append(m)

m=json.loads((ROOT/"manifests/kde-tier2-kmime-legacy-provider.json").read_text())
tier2=json.loads((ROOT/"manifests/kde-frameworks-tier2.json").read_text())
audit=json.loads((ROOT/"manifests/kde-tier2-kmime-compatibility-audit.json").read_text())
km=next(x for x in tier2["nodes"] if x["id"]=="kmime")

req(m.get("schema")==1 and m.get("provider")=="kmime-legacy-runtime","provider identity")
req(m.get("state") in {"materialization-pending","materialized","PASS"},"provider state")
req(m.get("role")=="ubuntu-application-compatibility-only","provider role")
req(m.get("package_state_effect")=="none","pre-PASS package-state semantics")
req(m.get("authority",{}).get("kde_frameworks")=="kf6-kmime-6.30.0","KDE authority unchanged")
req(m.get("authority",{}).get("compatibility_target")=="ubuntu-resolute","compatibility target")

r=m.get("source_reference",{})
req(r.get("source_package")=="kmime" and r.get("ubuntu_version")=="25.12.3-0ubuntu1","legacy source identity")
req(r.get("upstream_version")=="25.12.3","legacy upstream version")
for k in ("dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
    req(len(r.get(k,""))==64,f"source reference {k}")

p=m.get("supralinux_package",{})
req(p.get("package_version")=="25.12.3-0ubuntu1+supralinux1","provider package version")
req(p.get("build_arch_all") is False,"provider must not build arch:all data package")
req(p.get("expected_binary_packages")==["libkmime-dev","libkpim6mime6"],"provider arch:any binary set")
req(p.get("excluded_binary_packages")==["libkmime-data"],"legacy data exclusion")
req(p.get("runtime_package")=="libkpim6mime6" and p.get("runtime_soname")=="libKPim6Mime.so.6","legacy runtime contract")
req(p.get("versioned_provides")=="libkpim6mime6-25.12","Ubuntu versioned virtual contract")
req(p.get("multi_arch")=="same","legacy runtime Multi-Arch")
req(p.get("development_package")=="libkmime-dev","legacy dev package")
req(p.get("development_cmake_package")=="KPim6Mime" and p.get("development_cmake_target")=="KPim6::Mime","legacy development contract")

a=m.get("adaptation",{})
req(a.get("classification")=="data-provider-alternative","adaptation classification")
req(a.get("old_dependency")=="libkmime-data (= ${source:Version})","baseline data dependency")
req(a.get("new_dependency")=="libkmime-data (= 25.12.3-0ubuntu1) | libkf6mime-data (>= 6.30.0-0supralinux1)","selected data alternative")
req(a.get("framework_package_changes")==[] and a.get("runtime_abi_changes")==[],"Frameworks/runtime ABI must remain unchanged")
req(a.get("duplicated_data_payload") is False and a.get("kde_feature_effect")=="none","no duplicate data / no KDE feature effect")

req(audit.get("state")=="PASS","compatibility audit must be PASS")
selected=audit.get("result",{}).get("selected_remediation",{})
req(selected.get("strategy")=="supralinux-legacy-runtime-provider-with-framework-data-alternative","provider follows audit remediation")
req(km.get("planning",{}).get("compatibility_audit",{}).get("status")=="PASS","canonical compatibility audit PASS")
if km.get("state")=="PASS":
    req(m.get("state")=="PASS","KMime cannot be PASS before compatibility provider PASS")
    req(km.get("planning",{}).get("readiness")=="retained-pass","KMime PASS readiness")
    req(km.get("planning",{}).get("compatibility_provider",{}).get("status")=="PASS","canonical compatibility provider PASS")
else:
    req(km.get("state")=="pending" and km.get("planning",{}).get("readiness")=="compatibility-provider-required","KMime remains pending until provider PASS")

for path in (
    "scripts/materialize-kde-tier2-kmime-legacy-provider.sh",
    "scripts/run-kde-tier2-kmime-legacy-provider-build.sh",
    ".github/workflows/kde-tier2-kmime-legacy-provider.yml",
    "docs/kde-tier2-kmime-legacy-provider.md",
):
    req((ROOT/path).exists(),f"missing legacy provider component: {path}")

if m.get("state")=="materialized":
    ev=m.get("materialization_evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_attempted") is False,"materialization evidence semantics")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"materialization artifact evidence")

if m.get("state")=="PASS":
    ev=m.get("build_evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_attempted") is True,"provider PASS build evidence")
    req(ev.get("coinstallation")=="PASS" and ev.get("legacy_consumer")=="PASS" and ev.get("framework_consumer")=="PASS","provider dual compatibility gates")
    req(m.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 2 KMime legacy compatibility-provider definition: PASS")
print("state="+m["state"])
