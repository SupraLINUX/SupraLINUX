#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text())
def req(v,m):
    if not v:
        print("ERROR:",m,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/kde-tier3-kio-round15-diagnostic.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
D14=load("manifests/kde-tier3-kio-round14-diagnostic.json")
W=(ROOT/".github/workflows/kde-tier3-kio-round15-diagnostic.yml").read_text()
D=(ROOT/"docs/kde-tier3-kio-round15-diagnostic.md").read_text()
runner_paths=[
 "scripts/run-kde-tier3-kio-round15-diagnostic.sh",
 "scripts/run-kde-tier3-kio-round15-providers.sh",
 "scripts/run-kde-tier3-kio-round15-probe.sh",
 "scripts/run-kde-tier3-kio-round15-classify.sh",
]
R="\n".join((ROOT/p).read_text() for p in runner_paths)

req(M.get("schema")==1 and M.get("node")=="kio" and M.get("round")==15,"Round15 identity")
req(M.get("authority")=="kde-upstream" and M.get("frameworks_series")=="6.30.0" and M.get("upstream_ref")=="v6.30.0","Round15 authority/version")
req(M.get("claim")=="non-promoting-breeze-icons-init-state-diagnostic" and M.get("non_promoting") is True,"Round15 non-promoting claim")
req(M.get("package_attempted") is False and M.get("package_state_effect")=="none","Round15 package state")
req(M.get("dag_state_changes_allowed") is False and M.get("downstream_eligibility_changes_allowed") is False,"Round15 canonical mutation ban")
req(M.get("execution_authorized") is False,"Round15 execution remains closed")
req(M.get("status") in {"definition-pending-diagnostic","diagnostic-PASS"},"Round15 lifecycle")
req(M.get("canonical_snapshot")=="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED","Round15 snapshot")

nodes={n["id"]:n for n in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux7","KIO -7 remains FAIL")
req(nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"KIO remains downstream-ineligible")
req(L.get("state")=="attempt7-closed-mixed" and L.get("execution_authorized") is False,"Level1 remains closed")
req(L.get("current_attempt")==7 and L.get("next_attempt")==8,"Attempt counters")

req(D14.get("status")=="diagnostic-PASS" and D14.get("next_gate")=="tier3-round15-kio-breeze-icons-init-state-diagnostic-definition","Round14 handoff")
e14=M.get("round14_evidence",{})
req(e14.get("workflow_run")==36163272251 and e14.get("job_id")==108164792241 and e14.get("artifact_id")==10876807762,"Round14 evidence identity")
req(e14.get("artifact_sha256")=="2dda498091873a1c99a649ddb15c795130592c91100a3d97a78a608b8f531b87","Round14 evidence digest")
req(e14.get("conclusion")=="libkf6iconthemes-bin-does-not-recover-both-kio-tests","Round14 conclusion")

link=M.get("round13_linkage_evidence",{})
req(link.get("workflow_run")==36146880757 and link.get("artifact_id")==10869413386,"Round13 linkage identity")
req(link.get("artifact_sha256")=="f96d4fdfebc5fcebe63633650ebf3998a51e37e5c84c12b50bc3d745097d7cd7","Round13 linkage digest")
req(len(link.get("proven",[]))==4,"Round13 linkage claims")

b=M.get("breeze_provider",{})
req(b.get("version")=="4:6.30.0-0supralinux1" and b.get("artifact_id")==10682012012,"Breeze provider identity")
req(b.get("artifact_sha256")=="daaa5abda5a8f824c6fa509142d7cd9132de213d782cb32e0561873f427aa577","Breeze artifact")
req(b.get("source_sha256")=="93866c19791838fc9757b305e010e23bb38cb5f201e4ecc96cc8ef5f1173ebe6","Breeze source")
k=M.get("kiconthemes_source",{})
req(k.get("artifact_id")==10731249726 and k.get("source_sha256")=="c0c684823d0e087f35168cd79f1053fd358bb8fb47b27996a11c7d7ee3da6f4d","KIconThemes source")
req("Q_COREAPP_STARTUP_FUNCTION(initThemeHelper)" in k.get("source_contract",[]),"KIconThemes startup contract")

invalid=M.get("invalid_attempts",[])
req(len(invalid) in {0,1},"Round15 invalid attempt ledger")
if invalid:
    a=invalid[0]
    req(a.get("attempt")==1 and a.get("workflow_run")==36207971890 and a.get("job_id")==108308432777,"Round15 invalid Attempt1 workflow")
    req(a.get("artifact_id")==10894787434 and a.get("artifact_sha256")=="7ac10f5ee01a1a28240db7391d748cbd292abaed923c155845d560307710f598","Round15 invalid Attempt1 artifact")
    req(a.get("result")=="DIAG_INVALID" and a.get("conclusion")=="baseline-drift-invalid" and a.get("canonical_effect")=="none","Round15 invalid Attempt1 classification")

scope=M.get("diagnostic_scope",{})
req(scope.get("sequences")==["normal","kdirmodel-testmode","knewfilemenu-sequence"],"Round15 sequences")
req(scope.get("modes")==["qt-baseline","qt-fallback-breeze","breeze-linked-no-init","breeze-init"],"Round15 modes")
req(scope.get("icons")==["unknown","inode-directory","folder-red"],"Round15 icons")
req(all(scope.get(x) is False for x in ("package_build","source_modification","package_revision_allocation","test_suppression")),"Round15 safety scope")

for token in ("KDE Frameworks Tier 3 KIO Round 15 diagnostic","ubuntu-26.04","run-kde-tier3-kio-round15-diagnostic.sh"):
    req(token in W,f"workflow token {token}")
for token in ("10869413386","10682012012","10731249726","BreezeIcons::initIcons()","libKF6IconThemes.so.6","libKF6BreezeIcons.so.6","qt-fallback-breeze","breeze-linked-no-init","breeze-init"):
    req(token in R,f"runner token {token}")
for forbidden in ("dpkg-buildpackage","sbuild --"):
    req(forbidden not in R,f"must not package: {forbidden}")
req("Round 14 rejected" in D and "BreezeIcons::initIcons()" in D and "No Debian package is built" in D,"Round15 documentation")

if M.get("status")=="definition-pending-diagnostic":
    req(L.get("next_gate")=="tier3-round15-kio-breeze-icons-init-state-diagnostic-definition","Round15 live definition gate")
    req(M.get("next_gate")=="tier3-round15-kio-breeze-icons-init-state-diagnostic-evidence","Round15 evidence gate")
else:
    req(M.get("next_gate","").startswith("tier3-round16-"),"Round15 closed handoff")
    req(L.get("next_gate")==M.get("next_gate"),"Round15 closed live gate")
    ev=M.get("diagnostic_evidence",{})
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round15 closure evidence")

req(M.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval gate")
print("KDE Tier 3 KIO Round 15 diagnostic definition: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7")
print("next_gate="+M["next_gate"])
