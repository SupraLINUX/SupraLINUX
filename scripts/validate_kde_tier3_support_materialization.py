#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

m=load("manifests/kde-tier3-support-materialization.json")
contracts=load("manifests/kde-tier3-support-package-contracts.json")
tier3=load("manifests/kde-frameworks-tier3.json")

req(m.get("schema")==1 and m.get("authority")=="kde-upstream","support materialization schema/authority")
req(m.get("role")=="support-source-materialization","support materialization role")
req(m.get("frameworks_series")=="6.30.0","support materialization series")
req(m.get("contract_manifest")=="manifests/kde-tier3-support-package-contracts.json","support materialization contract link")
req(m.get("state") in {"pending-ci","PASS"},"support materialization lifecycle")
req(m.get("package_attempted") is False and m.get("package_state_effect")=="none","materialization must not claim package attempt/PASS")
req(m.get("selected_nodes")==["breeze-icons","kdoctools","kded"],"support materialization node order")

req(contracts.get("state") in {"contracts-ready","materialized"},"materialization requires finalized contracts")
req(contracts.get("packaging_tree_capture",{}).get("status")=="PASS","materialization requires packaging-tree PASS")

a=m.get("common_adaptations",{})
req(a.get("maintainer")=="SupraLINUX Build System <build@supralinux.invalid>","materialization maintainer")
req(a.get("remove_reference_uploaders") is True and a.get("remove_reference_vcs_fields") is True,"reference metadata removal")
dh=a.get("debhelper_compat",{})
req(dh.get("from")=="debhelper-compat (= 14)" and dh.get("to")=="debhelper-compat (= 13)","Resolute debhelper compatibility adaptation")

nodes=m.get("nodes",{})
req(set(nodes)=={"breeze-icons","kdoctools","kded"},"support materialization node set")
for node,n in nodes.items():
    c=contracts["components"][node]
    contract=c.get("contract",{})
    req(n.get("state") in {"pending","materialized"},f"{node}: materialization state")
    req(n.get("source_package")==contract.get("source_package"),f"{node}: source package contract")
    req(n.get("upstream_version")==c.get("upstream_version"),f"{node}: upstream version")
    req(n.get("upstream_source_sha256")==c.get("upstream_source_sha256"),f"{node}: upstream source SHA")
    req(n.get("packaging_reference_version")==contract.get("packaging_reference",{}).get("version"),f"{node}: packaging reference version")
    req(n.get("packaging_reference_tree_sha256")==contract.get("packaging_reference",{}).get("tree_sha256"),f"{node}: packaging tree pin")
    req(n.get("package_version")==contract.get("package_version_candidate"),f"{node}: package version contract")
    req(n.get("expected_binary_packages")==contract.get("target_binary_packages"),f"{node}: binary package contract")
    if n.get("state")=="materialized":
        ev=n.get("evidence",{})
        req(ev.get("result")=="PASS" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none",f"{node}: materialization evidence semantics")
        req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),f"{node}: run/job evidence")
        req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,f"{node}: artifact evidence")
        req(ev.get("package_version")==n.get("package_version"),f"{node}: evidence package version")
        req(ev.get("orig_tar_sha256")==n.get("upstream_source_sha256"),f"{node}: authoritative source retained")
        req(ev.get("debhelper_compat")=="13",f"{node}: materialized Resolute debhelper contract")
        for key in ("dsc_sha256","debian_tar_sha256","adapted_control_sha256"):
            req(len(ev.get(key,""))==64,f"{node}: {key}")

if m.get("state")=="pending-ci":
    req(all(n.get("state")=="pending" for n in nodes.values()),"pending materialization nodes")
else:
    req(all(n.get("state")=="materialized" for n in nodes.values()),"PASS materialization requires all nodes materialized")

    summary=m.get("evidence_summary",{})
    req(summary.get("result")=="PASS" and summary.get("workflow_run")==35698463205,"materialization summary evidence")
    req(summary.get("package_attempted") is False and summary.get("package_state_effect")=="none","materialization summary semantics")

support=tier3.get("support_components",{})
req(support.get("next_gate") in {"support-materialization","support-build","support-build-level0","support-build-level1","tier3-provider-audit","tier3-package-contracts"},"canonical support materialization gate")

for path in (
 "scripts/materialize-kde-tier3-support-package.sh",
 "scripts/kde-tier3-support-materialization-needed.sh",
 "scripts/test-kde-tier3-support-materialization-scope.sh",
 ".github/workflows/kde-tier3-support-materialization.yml",
 "docs/kde-tier3-support-materialization.md",
):
    req((ROOT/path).exists(),f"missing support materialization component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 support materialization definition: PASS")
print("state="+m["state"])
