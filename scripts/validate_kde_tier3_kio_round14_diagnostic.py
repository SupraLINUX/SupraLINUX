#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
M=json.loads((ROOT/"manifests/kde-tier3-kio-round14-diagnostic.json").read_text())
D13=json.loads((ROOT/"manifests/kde-tier3-kio-round13-diagnostic.json").read_text())
W=(ROOT/".github/workflows/kde-tier3-kio-round14-diagnostic.yml").read_text()
R=(ROOT/"scripts/run-kde-tier3-kio-round14-diagnostic.sh").read_text()
D=(ROOT/"docs/kde-tier3-kio-round14-diagnostic.md").read_text()
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)
req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==14,"Round14 identity")
req(M.get("claim")=="non-promoting-kiconthemes-engine-provider-diagnostic" and M.get("non_promoting") is True,"Round14 non-promoting claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round14 package state")
req(M.get("execution_authorized") is False,"Round14 canonical execution must remain closed")
req(M.get("status") in {"definition-pending-diagnostic","diagnostic-PASS"},"Round14 lifecycle")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round14 canonical snapshot")
req(D13.get("status")=="diagnostic-PASS" and D13.get("next_gate")=="tier3-round14-kio-kiconthemes-engine-provider-diagnostic-definition","Round13 closure handoff")
e13=M.get("round13_evidence",{})
req(e13.get("workflow_run")==36146880757 and e13.get("job_id")==108110145068,"Round13 evidence identity")
req(e13.get("artifact_id")==10869413386 and e13.get("artifact_sha256")=="f96d4fdfebc5fcebe63633650ebf3998a51e37e5c84c12b50bc3d745097d7cd7","Round13 evidence artifact")
req(e13.get("conclusion")=="build-tree-reproduces-no-simple-env-recovery-inspect-traces","Round13 conclusion")
pc=M.get("provider_candidate",{})
req(pc.get("node")=="kiconthemes" and pc.get("package_version")=="6.30.0-0supralinux3","Round14 provider version")
req(pc.get("canonical_artifact_id")==10731249726 and pc.get("canonical_artifact_sha256")=="5b06a92638fb67409710b140f3ebc597400d0d739db497e3d570fbe42cfa5206","Round14 provider artifact")
req(pc.get("binary_package")=="libkf6iconthemes-bin" and pc.get("binary_deb_sha256")=="6806b7b03b3f30d21620c315118066c9c7f35714e6a12e0b3360e01cbcfaff0c","Round14 binary provider identity")
req(pc.get("plugin_path")=="/usr/lib/x86_64-linux-gnu/qt6/plugins/kiconthemes6/iconengines/KIconEnginePlugin.so","Round14 plugin path")
scope=M.get("diagnostic_scope",{})
req(scope.get("build_support_targets")==["kio_file","kioworker"],"Round14 support targets")
req(scope.get("build_test_targets")==["kdirmodeltest","knewfilemenutest"],"Round14 test targets")
req(scope.get("direct_test_functions")=={"kdirmodeltest":"testIcon","knewfilemenutest":"testFolderIconCollection"},"Round14 primary functions")
req(scope.get("post_provider_ctest_targets")==["kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"],"Round14 post-provider CTest targets")
req(scope.get("package_build") is False and scope.get("source_modification") is False and scope.get("package_revision_allocation") is False and scope.get("test_suppression") is False,"Round14 safety scope")
for token in ("KDE Frameworks Tier 3 KIO Round 14 diagnostic","ubuntu-26.04","scripts/run-kde-tier3-kio-round14-diagnostic.sh","scripts/validate_kde_tier3_kio_round14_diagnostic.py"):
    req(token in W,f"Round14 workflow token {token}")
for token in ("10839162922","ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c","10731249726","6806b7b03b3f30d21620c315118066c9c7f35714e6a12e0b3360e01cbcfaff0c","libkf6iconthemes-bin","KIconEnginePlugin.so","kdirmodeltest","knewfilemenutest","kio_file","kioworker","QT_DEBUG_PLUGINS","override_dh_auto_configure"):
    req(token in R,f"Round14 runner token {token}")
for forbidden in ("dpkg-buildpackage","sbuild --"):
    req(forbidden not in R,f"Round14 must not build a Debian package: {forbidden}")
req("A/B" in D and "libkf6iconthemes-bin" in D and "No KIO revision is allocated" in D,"Round14 documentation")
if M.get("status")=="definition-pending-diagnostic":
    req(M.get("next_gate")=="tier3-round14-kio-kiconthemes-engine-provider-diagnostic-evidence","Round14 definition gate")
else:
    req(M.get("next_gate")=="tier3-round15-kio-breeze-icons-init-state-diagnostic-definition","Round14 closure next gate")
    ev=M.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36163272251 and ev.get("job_id")==108164792241 and ev.get("commit")=="49e27249ecaa8f7d1ba20fe38615bdc2ee11d991","Round14 closure workflow identity")
    req(ev.get("artifact_id")==10876807762 and ev.get("artifact_sha256")=="2dda498091873a1c99a649ddb15c795130592c91100a3d97a78a608b8f531b87","Round14 closure artifact identity")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round14 closure evidence")
    dr=M.get("diagnostic_results",{})
    req(dr.get("conclusion")=="libkf6iconthemes-bin-does-not-recover-both-kio-tests","Round14 conclusion")
    req(dr.get("provider_plugin_seen") is False,"Round14 provider plugin remains unloaded")
    for side in ("baseline","provider"):
        direct=dr.get(side,{}).get("direct",{})
        ctest=dr.get(side,{}).get("ctest",{})
        req(direct.get("rc")==1 and direct.get("kdirmodel_empty_icon") is True and direct.get("knewfilemenu_empty_icon") is True,f"Round14 {side} direct reproduction")
        req(ctest.get("rc")==8 and ctest.get("kdirmodel_empty_icon") is True and ctest.get("knewfilemenu_empty_icon") is True,f"Round14 {side} CTest reproduction")
    req(dr.get("next_diagnostic_scope")=="breeze-icons-fallback-and-resource-init-state","Round14 next diagnostic scope")
req(M.get("stable_promotion_requires_explicit_user_approval") is True,"Round14 stable gate")
print("KDE Tier 3 KIO Round 14 historical diagnostic evidence: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7")
print("next_gate="+M["next_gate"])
