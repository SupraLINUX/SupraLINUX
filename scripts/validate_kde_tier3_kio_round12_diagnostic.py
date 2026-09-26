#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
M=json.loads((ROOT/"manifests/kde-tier3-kio-round12-diagnostic.json").read_text())
T=json.loads((ROOT/"manifests/kde-frameworks-tier3.json").read_text())
L=json.loads((ROOT/"manifests/kde-tier3-build-level1.json").read_text())
A=json.loads((ROOT/"manifests/kde-tier3-build-level1-attempts.json").read_text())
W=(ROOT/".github/workflows/kde-tier3-kio-round12-diagnostic.yml").read_text()
R=(ROOT/"scripts/run-kde-tier3-kio-round12-diagnostic.sh").read_text()
D=(ROOT/"docs/kde-tier3-kio-round12-diagnostic.md").read_text()
D13=json.loads((ROOT/"manifests/kde-tier3-kio-round13-diagnostic.json").read_text())
D14=json.loads((ROOT/"manifests/kde-tier3-kio-round14-diagnostic.json").read_text())
D15=json.loads((ROOT/"manifests/kde-tier3-kio-round15-diagnostic.json").read_text())

def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==12,"Round12 diagnostic identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round12 upstream authority/version")
req(M.get("upstream_source_sha256")=="c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2","Round12 KIO source digest")
req(M.get("claim")=="non-promoting-kio-icon-resolution-diagnostic" and M.get("non_promoting") is True,"Round12 must remain non-promoting")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round12 cannot claim a package attempt/state effect")
req(M.get("dag_state_changes_allowed") is False and M.get("downstream_eligibility_changes_allowed") is False,"Round12 cannot mutate DAG/downstream state")
req(M.get("execution_authorized") is False,"Round12 binary execution authority must remain false")
req(M.get("status") in {"definition-pending-diagnostic","diagnostic-PASS"},"Round12 diagnostic lifecycle")
if M.get("status")=="definition-pending-diagnostic":
    req(M.get("next_gate")=="tier3-round12-kio-diagnostic-evidence","Round12 definition next gate")
if M.get("status")=="diagnostic-PASS":
    req(M.get("next_gate")=="tier3-round13-kio-build-tree-diagnostic-definition","Round12 PASS next gate")

nodes={n["id"]:n for n in T.get("nodes",[])}
kio=nodes.get("kio",{})
kxml=nodes.get("kxmlgui",{})
req(kio.get("state")=="FAIL" and kio.get("packaging",{}).get("package_version")=="6.30.0-0supralinux7","Round12 must retain canonical KIO -7 FAIL")
req(kio.get("packaging",{}).get("downstream_eligible") is False,"Round12 KIO remains downstream-ineligible")
req(kxml.get("state")=="PASS" and kxml.get("packaging",{}).get("package_version")=="6.30.0-0supralinux5","Round12 must retain KXMLGui PASS")
req(L.get("state")=="attempt7-closed-mixed" and L.get("execution_authorized") is False,"Level1 must remain Attempt7 closed")
req(L.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round12 canonical snapshot")
if M.get("status")=="definition-pending-diagnostic":
    req(L.get("next_gate")=="tier3-round12-kio-diagnostic-definition","canonical next gate remains Round12 definition until evidence is closed")
else:
    current_next = "tier3-round16-kio-kiconthemes-startup-kio-library-diagnostic-definition" if D15.get("status")=="diagnostic-PASS" else ("tier3-round15-kio-breeze-icons-init-state-diagnostic-definition" if D14.get("status")=="diagnostic-PASS" else ("tier3-round14-kio-kiconthemes-engine-provider-diagnostic-definition" if D13.get("status")=="diagnostic-PASS" else "tier3-round13-kio-build-tree-diagnostic-definition"))
    req(L.get("next_gate")==current_next,"closed Round12 live handoff")
req(L.get("current_attempt")==7 and L.get("next_attempt")==8,"Round12 attempt counters")

e=M.get("attempt7_evidence",{})
req(e.get("workflow_run")==36079116873 and e.get("commit")=="ef6262ac9018df2c0d111d97f99919d8acdeb215","Attempt7 workflow identity")
ke=e.get("kio",{})
req(ke.get("job_id")==107897110171 and ke.get("artifact_id")==10840963289 and ke.get("artifact_sha256")=="32b10c0ac337040239edea709440c5b09b898d76da1ac3c8e10339bf1477d239","Attempt7 KIO evidence")
req(ke.get("tests")=={"total":69,"pass":67,"fail":2},"Attempt7 KIO totals")
req(set(ke.get("failed_tests",[]))=={"kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"},"Attempt7 KIO failed set")
be=M.get("retained_breeze_provider",{})
req(be.get("version")=="4:6.30.0-0supralinux1" and be.get("artifact_id")==10682012012,"Round12 Breeze provider")
req(be.get("artifact_sha256")=="daaa5abda5a8f824c6fa509142d7cd9132de213d782cb32e0561873f427aa577","Round12 Breeze artifact digest")
req(be.get("breeze_deb_sha256")=="308a20089ef387da2d5ba08b42be4299dd62fe5f5535786a0d8881d93b0d1e09","Round12 Breeze deb digest")

findings={x.get("id"):x for x in M.get("established_findings",[])}
for fid in (
    "attempt7-ctest-environment-preserved",
    "breeze-installed-in-attempt7-chroot",
    "krecentdocument-recovered",
    "knewfilemenu-primary-failure-is-icon-resolution",
    "kdirmodel-primary-failure-is-icon-resolution",
):
    req(findings.get(fid,{}).get("state")=="PROVEN",f"Round12 established finding {fid}")

hist=[x for x in A.get("campaign_history",[]) if x.get("attempt")==7]
req(len(hist)==1 and hist[0].get("result")=="MIXED" and hist[0].get("next_gate")=="tier3-round12-kio-diagnostic-definition","Attempt7 ledger closure linkage")

for token in (
    "KDE Frameworks Tier 3 KIO Round 12 diagnostic",
    "ubuntu-26.04",
    "scripts/validate_kde_tier3_kio_round12_diagnostic.py",
    "scripts/run-kde-tier3-kio-round12-diagnostic.sh",
):
    req(token in W,f"Round12 workflow token {token}")
for forbidden in ("dpkg-buildpackage","sbuild --","dh_auto_test"):
    req(forbidden not in R,f"Round12 diagnostic must not build a package: {forbidden}")
for token in (
    "10840963289",
    "32b10c0ac337040239edea709440c5b09b898d76da1ac3c8e10339bf1477d239",
    "10682012012",
    "c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2",
    "QStandardPaths::setTestModeEnabled",
    "QIcon::fromTheme",
):
    req(token in R,f"Round12 runner evidence/probe token {token}")
req("No package revision is allocated" in D and "67/69" in D and "inode-directory" in D,"Round12 documentation contract")

if M.get("status")=="diagnostic-PASS":
    ev=M.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36082312546 and ev.get("job_id")==107906716315 and ev.get("commit")=="91b57e78d5d74ed6ad7c87313086d1476bf60ba6","Round12 PASS workflow identity")
    req(ev.get("artifact_id")==10842450967 and ev.get("artifact_sha256")=="5b34f0a73e1e0f9b32e0c88d6c5bc90d3463d4b4854931eecda66244a9c52df6","Round12 PASS artifact identity")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round12 PASS non-promoting evidence")
    dr=M.get("diagnostic_results",{})
    req(dr.get("qt_version")=="6.10.2" and dr.get("theme_name")=="breeze","Round12 Qt/Breeze identity")
    req(dr.get("baseline",{}).get("unknown")=={"has":True,"null":False,"name":"unknown"},"Round12 baseline unknown icon")
    req(dr.get("baseline",{}).get("inode-directory")=={"has":True,"null":False,"name":"inode-directory"},"Round12 baseline inode-directory icon")
    req(dr.get("kdirmodel_testmode",{}).get("reproduced") is False,"Round12 KDirModel isolated sequence must not reproduce")
    req(dr.get("knewfilemenu_sequence",{}).get("reproduced") is False,"Round12 KNewFileMenu isolated sequence must not reproduce")
    req(dr.get("next_diagnostic_scope")=="kio-build-tree-process-specific-icon-resolution-diagnostic","Round12 next diagnostic scope")

req(M.get("stable_promotion_requires_explicit_user_approval") is True,"Round12 stable gate")
print("KDE Tier 3 KIO Round 12 diagnostic definition: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7")
print("next_gate="+M["next_gate"])
