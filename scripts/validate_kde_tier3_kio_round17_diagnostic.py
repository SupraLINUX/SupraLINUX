#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round17-diagnostic.json")
D16=load("manifests/kde-tier3-kio-round16-diagnostic.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round17-diagnostic.yml").read_text()
D=(ROOT/"docs/kde-tier3-kio-round17-diagnostic.md").read_text()
R="\n".join((ROOT/p).read_text() for p in (
 "scripts/run-kde-tier3-kio-round17-diagnostic.sh",
 "scripts/run-kde-tier3-kio-round17-instrument.sh",
 "scripts/run-kde-tier3-kio-round17-classify.sh",
))

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==17,"Round17 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round17 upstream identity")
req(M.get("claim")=="non-promoting-qt-svg-plugin-environment-root-cause-diagnostic" and M.get("non_promoting") is True,"Round17 claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round17 package state")
req(M.get("canonical_source_modified") is False and M.get("diagnostic_instrumentation") is False and M.get("environment_ab") is True,"Round17 A/B environment contract")
req(M.get("dag_state_changes_allowed") is False and M.get("downstream_eligibility_changes_allowed") is False,"Round17 DAG safety")
req(M.get("execution_authorized") is False and M.get("status") in {"definition-pending-diagnostic","diagnostic-PASS"},"Round17 lifecycle")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round17 snapshot")

req(D16.get("status")=="diagnostic-PASS" and D16.get("next_gate")=="tier3-round17-kio-object-path-state-transition-diagnostic-definition","Round16 handoff")
e16=M.get("round16_evidence",{})
req(e16.get("workflow_run")==36209833629 and e16.get("job_id")==108313880904 and e16.get("artifact_id")==10894374901,"Round16 evidence identity")
req(e16.get("artifact_sha256")=="8cda50173446df052b21e5ca4fe89129af65e1c1e1ff13ac137953b5a9508cf6","Round16 evidence digest")
req(e16.get("conclusion")=="library-preload-alone-does-not-reproduce-kio-icon-name-loss","Round16 conclusion")
sm=M.get("source_materialization",{})
req(sm.get("artifact_id")==10839162922 and sm.get("artifact_sha256")=="ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c","Round17 source materialization")
req(sm.get("package_version")=="6.30.0-0supralinux7" and sm.get("upstream_source_sha256")=="c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2","Round17 source identity")

invalid=M.get("invalid_attempts",[])
req(len(invalid)==3,"Round17 invalid attempt ledger")
a1,a2,a3=invalid
req(a1.get("attempt")==1 and a1.get("workflow_run")==36213295538 and a1.get("job_id")==108324143779,"Round17 invalid Attempt1 workflow")
req(a1.get("artifact_id")==10896761982 and a1.get("artifact_sha256")=="5247d6b2f9f80c15cb04c63c4687d37b707421e3a1f91f0e8f9e2d3360c01084","Round17 invalid Attempt1 artifact")
req(a1.get("result")=="DIAG_INVALID" and a1.get("conclusion")=="instrumentation-perturbed-original-failure" and a1.get("canonical_effect")=="none","Round17 invalid Attempt1 classification")
req(a2.get("attempt")==2 and a2.get("workflow_run")==36214198192 and a2.get("job_id")==108326788757,"Round17 invalid Attempt2 workflow")
req(a2.get("artifact_id")==10896848386 and a2.get("artifact_sha256")=="5b4c14d52b858a2455b7a9ee395db305360c8a386993fad37e92f7620fdb4002","Round17 invalid Attempt2 artifact")
req(a2.get("repository_policy_workflow_run")==36214198247 and a2.get("repository_policy_result")=="FAIL-SHELLCHECK-SC2100","Round17 invalid Attempt2 policy")
req(a2.get("result")=="DIAG_INVALID" and a2.get("conclusion")=="conditional-instrumentation-still-perturbs-baseline" and a2.get("canonical_effect")=="none","Round17 invalid Attempt2 classification")
req(a3.get("attempt")==3 and a3.get("workflow_run")==36215721289 and a3.get("job_id")==108331181346,"Round17 invalid Attempt3 workflow")
req(a3.get("artifact_id")==10897152304 and a3.get("artifact_sha256")=="dfe1356e3e10e4e12894627cab203c96ba9d842f11825ccb405b211da329b8f6","Round17 invalid Attempt3 artifact")
req(a3.get("repository_policy_workflow_run")==36215721283 and a3.get("repository_policy_result")=="PASS","Round17 invalid Attempt3 policy")
req(a3.get("result")=="DIAG_INVALID" and a3.get("conclusion")=="original-baseline-passed-due-to-environment-fixture-drift" and a3.get("canonical_effect")=="none","Round17 invalid Attempt3 classification")

scope=M.get("diagnostic_scope",{})
req(scope.get("source_modified") is False,"Round17 source unchanged")
req(scope.get("exact_test_cases",{}).get("kdirmodeltest")=="testIcon","Round17 KDir test")
req(scope.get("exact_test_cases",{}).get("knewfilemenutest")=="testFolderIconCollection:default","Round17 KNew test")
req(scope.get("environment_variable")=="qt6-svg-plugins package presence","Round17 SVG variable")
req(scope.get("aba_sequence")==["present-initial","absent-after-package-removal","reinstalled"],"Round17 A/B/A sequence")
req(all(scope.get(x) is False for x in ("package_build","canonical_source_modification","package_revision_allocation","test_suppression")),"Round17 safety scope")

for token in ("KDE Frameworks Tier 3 KIO Round 17 diagnostic","ubuntu-26.04","run-kde-tier3-kio-round17-diagnostic.sh"):
    req(token in W,f"workflow token {token}")
for token in ("10839162922","qt6-svg-plugins","r17_remove_svg_plugin","r17_install_svg_plugin","r17_record_svg_state present-initial","testFolderIconCollection:default","historical_empty_name_failure"):
    req(token in R,f"runner token {token}")
for forbidden in ("dpkg-buildpackage","sbuild --"):
    req(forbidden not in R,f"Round17 must not package: {forbidden}")
req("Attempt 4 — Qt SVG plugin A/B/A, no source changes" in D and "PASS with plugin" in D and "Closure — diagnostic PASS" in D and "No snapshot is created" in D,"Round17 documentation")

if M.get("status")=="definition-pending-diagnostic":
    req(M.get("next_gate")=="tier3-round17-kio-object-path-state-transition-diagnostic-evidence","Round17 evidence gate")
else:
    req(M.get("next_gate")=="tier3-round18-kio-qt-svg-provider-contract-remediation-definition","Round17 closed handoff")
    dv=M.get("definition_validation",{})
    req(dv.get("commit")=="0495449acb5c82e535540e346f2341a394bcc8b5" and dv.get("repository_policy_workflow_run")==36218411106 and dv.get("result")=="PASS","Round17 definition validation")
    ev=M.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36218411267 and ev.get("job_id")==108338905718 and ev.get("commit")=="0495449acb5c82e535540e346f2341a394bcc8b5","Round17 workflow identity")
    req(ev.get("artifact_id")==10898332133 and ev.get("artifact_sha256")=="511239dc8fd4581c032d8a7723e2edd772aab450718d44513c528dcf56a862f0","Round17 artifact identity")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round17 closure evidence")
    dr=M.get("diagnostic_results",{})
    req(dr.get("aba_valid") is True and dr.get("conclusion")=="qt6-svg-plugins-presence-controls-both-kio-icon-name-failures","Round17 A/B/A conclusion")
    req(dr.get("present_initial")=={"kdirmodel":"PASS","knewfilemenu":"PASS"},"Round17 present phase")
    req(dr.get("absent")=={"kdirmodel":"historical-empty-name-FAIL","knewfilemenu":"historical-empty-name-FAIL"},"Round17 absent phase")
    req(dr.get("reinstalled")=={"kdirmodel":"PASS","knewfilemenu":"PASS"},"Round17 reinstall phase")
    svg=dr.get("qt_svg_plugins",{})
    req(svg.get("version")=="6.10.2-2" and svg.get("qt6_svg_dev_depends_on_plugin") is False,"Round17 Qt SVG provider contract")
    req(svg.get("icon_engine_plugin")=="/usr/lib/x86_64-linux-gnu/qt6/plugins/iconengines/libqsvgicon.so","Round17 SVG icon engine")
    req(svg.get("image_format_plugin")=="/usr/lib/x86_64-linux-gnu/qt6/plugins/imageformats/libqsvg.so","Round17 SVG image plugin")
    req(dr.get("next_scope")=="qt-svg-provider-contract-ownership-and-remediation","Round17 next scope")

req(M.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval")
print("KDE Tier 3 KIO Round 17 historical diagnostic evidence: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7")
print("next_gate="+M["next_gate"])
