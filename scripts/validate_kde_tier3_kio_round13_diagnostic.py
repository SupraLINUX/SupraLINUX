#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
M=json.loads((ROOT/"manifests/kde-tier3-kio-round13-diagnostic.json").read_text())
D12=json.loads((ROOT/"manifests/kde-tier3-kio-round12-diagnostic.json").read_text())
W=(ROOT/".github/workflows/kde-tier3-kio-round13-diagnostic.yml").read_text()
R=(ROOT/"scripts/run-kde-tier3-kio-round13-diagnostic.sh").read_text()
D=(ROOT/"docs/kde-tier3-kio-round13-diagnostic.md").read_text()

def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==13,"Round13 identity")
req(M.get("claim")=="non-promoting-kio-build-tree-process-diagnostic" and M.get("non_promoting") is True,"Round13 non-promoting claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round13 package state")
req(M.get("execution_authorized") is False,"Round13 must not authorize canonical execution")
req(M.get("status") in {"definition-pending-diagnostic","diagnostic-PASS"},"Round13 lifecycle")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round13 canonical snapshot")

req(D12.get("status")=="diagnostic-PASS" and D12.get("next_gate")=="tier3-round13-kio-build-tree-diagnostic-definition","Round12 closure handoff")
e12=M.get("round12_evidence",{})
req(e12.get("workflow_run")==36082312546 and e12.get("job_id")==107906716315,"Round12 evidence identity")
req(e12.get("artifact_id")==10842450967 and e12.get("artifact_sha256")=="5b34f0a73e1e0f9b32e0c88d6c5bc90d3463d4b4854931eecda66244a9c52df6","Round12 evidence artifact")
req(e12.get("isolated_reproduction") is False,"Round12 non-reproduction handoff")

sm=M.get("source_materialization",{})
req(sm.get("artifact_id")==10839162922 and sm.get("artifact_sha256")=="ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c","Round13 exact source materialization")
req(sm.get("package_version")=="6.30.0-0supralinux7","Round13 source revision")

scope=M.get("diagnostic_scope",{})
req(scope.get("build_only_targets")==["kdirmodeltest","knewfilemenutest"],"Round13 test targets")
req(scope.get("build_support_targets")==["kio_file","kioworker"],"Round13 runtime support targets")
req(scope.get("direct_test_functions")=={"kdirmodeltest":"testIcon","knewfilemenutest":"testFolderIconCollection"},"Round13 direct primary test functions")
req(scope.get("per_process_timeout_seconds")=={"test":180,"trace":180},"Round13 per-process timeout policy")
req(scope.get("exact_provider_closure_from")=="manifests/kde-tier3-build-level1.json","Round13 provider closure authority")
req(set(scope.get("variants",[]))=={
 "ctest-exact-attempt7-environment","direct-exact-attempt7-environment",
 "direct-without-qt-plugin-path","direct-without-kdeci-platform-path",
 "direct-with-explicit-xdg-data-dirs"},"Round13 variants")
req(scope.get("source_modification") is False and scope.get("package_build") is False and scope.get("package_revision_allocation") is False and scope.get("test_suppression") is False,"Round13 safety scope")

for token in (
 "KDE Frameworks Tier 3 KIO Round 13 diagnostic",
 "ubuntu-26.04",
 "scripts/run-kde-tier3-kio-round13-diagnostic.sh",
 "scripts/validate_kde_tier3_kio_round13_diagnostic.py",
):
    req(token in W,f"Round13 workflow token {token}")
for token in (
 "10839162922","ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c",
 "kdirmodeltest","knewfilemenutest","kio_file","kioworker","QT_DEBUG_PLUGINS","strace","timeout --signal=TERM",
 "KDECI_PLATFORM_PATH","QT_PLUGIN_PATH","XDG_DATA_DIRS",
 "override_dh_auto_configure",
):
    req(token in R,f"Round13 runner token {token}")
for forbidden in ("dpkg-buildpackage","sbuild --"):
    req(forbidden not in R,f"Round13 must not build a Debian package: {forbidden}")
req("No new KIO revision is allocated" in D and "build-tree" in D and "sbuild/unshare" in D,"Round13 documentation")

if M.get("status")=="definition-pending-diagnostic":
    req(M.get("next_gate")=="tier3-round13-kio-build-tree-diagnostic-evidence","Round13 definition gate")
else:
    req(M.get("next_gate")=="tier3-round14-kio-kiconthemes-engine-provider-diagnostic-definition","Round13 closure next gate")
    ev=M.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36146880757 and ev.get("job_id")==108110145068 and ev.get("commit")=="7ede12eba5bd301687e074646027ebc293a4b489","Round13 closure workflow identity")
    req(ev.get("artifact_id")==10869413386 and ev.get("artifact_sha256")=="f96d4fdfebc5fcebe63633650ebf3998a51e37e5c84c12b50bc3d745097d7cd7","Round13 closure artifact identity")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round13 closure evidence")
    dr=M.get("diagnostic_results",{})
    req(dr.get("conclusion")=="build-tree-reproduces-no-simple-env-recovery-inspect-traces","Round13 conclusion")
    variants=dr.get("variants",{})
    req(len(variants)==5 and all(x.get("both_primary_failures") is True for x in variants.values()),"Round13 all variants reproduce both primary failures")
    ts=dr.get("trace_summary",{})
    req(ts.get("kdirmodeltest",{}).get("mentions_breeze") is True and ts.get("kdirmodeltest",{}).get("mentions_unknown") is True,"Round13 KDirModel trace")
    req(ts.get("knewfilemenutest",{}).get("mentions_breeze") is True and ts.get("knewfilemenutest",{}).get("mentions_inode_directory") is True,"Round13 KNewFileMenu trace")
    pc=dr.get("provider_candidate",{})
    req(pc.get("classification")=="strong-hypothesis-unproven","Round13 provider candidate remains unproven")
    req(pc.get("binary_package")=="libkf6iconthemes-bin" and pc.get("binary_deb_sha256")=="6806b7b03b3f30d21620c315118066c9c7f35714e6a12e0b3360e01cbcfaff0c","Round13 provider candidate identity")
    req(pc.get("plugin_path")=="/usr/lib/x86_64-linux-gnu/qt6/plugins/kiconthemes6/iconengines/KIconEnginePlugin.so","Round13 KIconEngine plugin path")

req(M.get("stable_promotion_requires_explicit_user_approval") is True,"Round13 stable gate")
print("KDE Tier 3 KIO Round 13 historical diagnostic evidence: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7")
print("next_gate="+M["next_gate"])
