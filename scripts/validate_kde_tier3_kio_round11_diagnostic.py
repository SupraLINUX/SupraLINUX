#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
M=ROOT/"manifests/kde-tier3-kio-round11-diagnostic.json"
T=ROOT/"manifests/kde-frameworks-tier3.json"
L=ROOT/"manifests/kde-tier3-build-level1.json"
W=ROOT/".github/workflows/kde-tier3-kio-round11-diagnostic.yml"
R=ROOT/"scripts/run-kde-tier3-kio-round11-diagnostic.sh"
D=ROOT/"docs/kde-tier3-kio-round11-diagnostic.md"

def fail(msg):
    raise SystemExit(msg)

m=json.loads(M.read_text())
t=json.loads(T.read_text())
l=json.loads(L.read_text())

if m.get("schema")!=1 or m.get("node")!="kio" or m.get("round")!=11:
    fail("KIO Round11 diagnostic identity")
if m.get("authority")!="kde-upstream" or m.get("frameworks_series")!="6.30.0":
    fail("KIO Round11 authority/version")
if m.get("claim")!="non-promoting-kio-test-environment-diagnostic" or m.get("non_promoting") is not True:
    fail("KIO Round11 must remain explicitly non-promoting")
if m.get("package_attempted") is not False or m.get("package_state_effect")!="none":
    fail("KIO Round11 diagnostic must not attempt/promote a package")
if m.get("dag_state_changes_allowed") is not False or m.get("downstream_eligibility_changes_allowed") is not False:
    fail("KIO Round11 diagnostic cannot mutate DAG/downstream state")
if m.get("status")!="definition-pending-diagnostic" or m.get("next_gate")!="tier3-round11-kio-diagnostic-evidence":
    fail("KIO Round11 diagnostic lifecycle")

canonical={n["id"]:n for n in t.get("nodes",[])}
kio=canonical.get("kio",{})
if kio.get("state")!="FAIL":
    fail("KIO canonical state must remain FAIL during diagnostic definition")
pack=kio.get("packaging",{})
if pack.get("state")!="FAIL" or pack.get("package_version")!="6.30.0-0supralinux6" or pack.get("downstream_eligible") is not False:
    fail("KIO canonical packaging state/version drift")
if l.get("state")!="attempt6-closed-mixed" or l.get("execution_authorized") is not False:
    fail("Level1 must stay closed while Round11 is diagnostic-only")
if l.get("canonical_snapshot")!="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED":
    fail("Round11 diagnostic must not alter canonical snapshot")
if l.get("next_gate")!="tier3-round11-kio-remediation-definition":
    fail("canonical next gate must remain Round11 definition until diagnostic evidence exists")

a5=m.get("attempt5_evidence",{})
a6=m.get("attempt6_evidence",{})
if a5.get("workflow_run")!=35991007820 or a5.get("job_id")!=107605066803 or a5.get("tests")!={"total":69,"pass":67,"fail":2}:
    fail("Attempt5 diagnostic evidence linkage")
if set(a5.get("failed_tests",[]))!={"kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"}:
    fail("Attempt5 failed-test set")
if "QT_PLUGIN_PATH=<build-tree>/bin" not in a5.get("observed_target_ctest_environment",[]):
    fail("Attempt5 upstream QT_PLUGIN_PATH evidence")
if a6.get("workflow_run")!=36035351270 or a6.get("job_id")!=107754320435 or a6.get("tests")!={"total":69,"pass":66,"fail":3}:
    fail("Attempt6 diagnostic evidence linkage")
if set(a6.get("failed_tests",[]))!={"kiocore-krecentdocumenttest","kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"}:
    fail("Attempt6 failed-test set")
if a6.get("missing_from_target_ctest_environment")!=["QT_PLUGIN_PATH"]:
    fail("Attempt6 target environment-loss evidence")

b=m.get("retained_breeze_provider",{})
if b.get("version")!="4:6.30.0-0supralinux1" or b.get("workflow_run")!=35700002095 or b.get("job_id")!=106656021938:
    fail("Breeze retained provider identity")
if b.get("artifact_id")!=10682012012 or b.get("artifact_sha256")!="daaa5abda5a8f824c6fa509142d7cd9132de213d782cb32e0561873f427aa577":
    fail("Breeze retained provider artifact")
if b.get("breeze_deb_sha256")!="308a20089ef387da2d5ba08b42be4299dd62fe5f5535786a0d8881d93b0d1e09":
    fail("Breeze exact package digest")

findings={x.get("id"):x for x in m.get("established_findings",[])}
if findings.get("round10-destructive-ctest-environment-replacement",{}).get("state")!="PROVEN":
    fail("Round10 environment replacement finding")
if findings.get("breeze-provider-payload-present",{}).get("state")!="PROVEN":
    fail("Breeze payload finding")
if findings.get("krecentdocument-timestamp-tie-risk",{}).get("state")!="EVIDENCE-BACKED-HYPOTHESIS":
    fail("KRecentDocument finding must remain hypothesis before focused runtime evidence")

mechanism=m.get("proposed_non_destructive_mechanism",{})
if mechanism.get("cmake_property")!="ENVIRONMENT_MODIFICATION":
    fail("Round11 must use non-destructive CTest environment mechanism candidate")
if mechanism.get("operations")!=["QT_QPA_PLATFORM=set:xcb","QT_QPA_SYSTEM_ICON_THEME=set:breeze"]:
    fail("Round11 environment modification operations")
if mechanism.get("status")!="candidate-pending-diagnostic-evidence" or mechanism.get("package_revision") is not None:
    fail("Round11 must not claim a new package revision yet")

workflow=W.read_text()
runner=R.read_text()
doc=D.read_text()
for token in ("KDE Frameworks Tier 3 KIO Round 11 diagnostic","artifact-ids: '10682012012'","run-kde-tier3-kio-round11-diagnostic.sh","retention-days: 90"):
    if token not in workflow:
        fail(f"Round11 workflow missing {token}")
for token in ("package_attempted",'"package_state_effect":"none"',"ENVIRONMENT_MODIFICATION","QT_PLUGIN_PATH=/probe/upstream-build-tree/bin","QT_QPA_PLATFORM=set:xcb","QT_QPA_SYSTEM_ICON_THEME=set:breeze","QIcon::themeSearchPaths","QIcon::hasThemeIcon","krecentdocument-static.json","DIAG_COMPLETE"):
    if token not in runner:
        fail(f"Round11 runner missing {token}")
if "sbuild " in runner or "dpkg-buildpackage" in runner:
    fail("Round11 diagnostic runner must not build a package")
for token in ("Attempt 5","Attempt 6","ENVIRONMENT_MODIFICATION","QT_PLUGIN_PATH","Breeze","krecentdocumenttest","no crea","6.30.0-0supralinux7"):
    if token not in doc:
        fail(f"Round11 diagnostic docs missing {token}")
if m.get("stable_promotion_requires_explicit_user_approval") is not True:
    fail("stable approval policy")

print("KDE Tier 3 KIO Round 11 diagnostic definition: PASS")
print("canonical state unchanged; package build disabled")
