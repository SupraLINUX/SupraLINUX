#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def req(v,m):
    if not v:
        errors.append(m)

def load(p):
    return json.loads((ROOT/p).read_text())

# Attempt 8 is closed historical evidence.  This validator intentionally reads
# only append-only/closed evidence and must not require the live Tier 3 lifecycle
# to remain at the Round 19 handoff.
A=load("manifests/kde-tier3-build-level1-attempts.json")
R=load("manifests/kde-tier3-kio-round18-remediation.json")

RUN=36238357510
COMMIT="77129c31006ac746d0d5d1d249ed7d1aaf6cf530"
ROOTFS_ID=10904512642
ROOTFS_SHA="d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe"
KIO_JOB=108394325161
KIO_ART=10905267300
KIO_SHA="9f95e2b8e3330ee4f1b275eb059736b87fa57d7752602aa598cb313659cae53f"
KXML_JOB=108394325149
KXML_ART=10905212105
KXML_SHA="297d8d91e52f82cd6713c30072a8f2deff80d73647b9c93c1b89263e5f21d441"
NEXT="tier3-round19-kio-diagnostic-definition"
SNAPSHOT="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED"

# Closed Round 18 / Attempt 8 record.
req(R.get("schema")==1 and R.get("node")=="kio" and R.get("diagnostic_round")==18,
    "Round18 remediation identity")
req(R.get("global_remediation_round")==11,"Round18 global remediation round")
req(R.get("authority")=="kde-upstream" and R.get("packaging_authority")=="supralinux",
    "Round18 authority/provider separation")
req(R.get("status")=="attempt8-closed-mixed" and R.get("execution_authorized") is False,
    "Round18 Attempt8 closed")
req(R.get("canonical_snapshot")==SNAPSHOT,"Round18 historical canonical snapshot")
req(R.get("candidate_package_version")=="6.30.0-0supralinux8",
    "Round18 KIO candidate revision")
accepted=R.get("accepted_contract",{})
req(accepted.get("field")=="Build-Depends" and accepted.get("action")=="ensure" and
    accepted.get("relation")=="qt6-svg-plugins <!nocheck>" and
    accepted.get("classification")=="upstream-test-environment-provider",
    "Round18 accepted Qt SVG test-provider contract")
req(accepted.get("runtime_binary_relation")=="none",
    "Round18 provider remains test/build-only")

rr=R.get("attempt8_result",{})
req(rr.get("workflow_run")==RUN and rr.get("commit")==COMMIT and rr.get("result")=="MIXED",
    "Round18 Attempt8 result identity")
req(rr.get("rootfs",{}).get("artifact_id")==ROOTFS_ID and
    rr.get("rootfs",{}).get("artifact_sha256")==ROOTFS_SHA,
    "Round18 Attempt8 rootfs evidence")
rk=rr.get("kio",{})
req(rk.get("job_id")==KIO_JOB and rk.get("artifact_id")==KIO_ART and
    rk.get("artifact_sha256")==KIO_SHA,
    "Round18 KIO artifact evidence")
req(rk.get("tests")=={"total":69,"pass":67,"fail":2},"Round18 KIO 67/69")
req(rk.get("remaining_failures",{}).get("krecentdocument"),
    "KRecentDocument failure retained")
req(rk.get("remaining_failures",{}).get("kdirmodel"),
    "KDirModel failure retained")
rx=rr.get("kxmlgui",{})
req(rx.get("job_id")==KXML_JOB and rx.get("artifact_id")==KXML_ART and
    rx.get("artifact_sha256")==KXML_SHA,
    "Round18 KXMLGui artifact evidence")
req(rx.get("tests")=={"total":7,"pass":7,"fail":0},"Round18 KXMLGui 7/7")
req(rx.get("python_import")=="PASS","Round18 KXMLGui Python import")
req(R.get("next_gate")==NEXT,"Round18 historical Round19 handoff")
req(R.get("stable_promotion_requires_explicit_user_approval") is True,
    "Round18 stable promotion policy")

# Append-only Attempt ledger independently corroborates the closed result.
hist=A.get("campaign_history",[])
req(hist and hist[-1].get("attempt")==8 and hist[-1].get("workflow_run")==RUN and
    hist[-1].get("result")=="MIXED",
    "Attempt8 ledger campaign")
req(hist and hist[-1].get("workflow_jobs")=={"success":1,"fail":1} and
    hist[-1].get("canonical_promotions")==0,
    "Attempt8 mixed/no promotion")
ki=A.get("nodes",{}).get("kio",[])
kx=A.get("nodes",{}).get("kxmlgui",[])
req(ki and ki[-1].get("attempt")==8 and ki[-1].get("result")=="FAIL" and
    ki[-1].get("job_id")==KIO_JOB and ki[-1].get("artifact_id")==KIO_ART and
    ki[-1].get("artifact_sha256")==KIO_SHA,
    "KIO ledger Attempt8 evidence")
req(ki and ki[-1].get("tests")=={"total":69,"pass":67,"fail":2},
    "KIO ledger tests")
req(kx and kx[-1].get("attempt")==8 and kx[-1].get("result")=="PASS" and
    kx[-1].get("job_id")==KXML_JOB and kx[-1].get("artifact_id")==KXML_ART and
    kx[-1].get("artifact_sha256")==KXML_SHA,
    "KXMLGui ledger Attempt8 evidence")
req(kx and kx[-1].get("tests")=={"total":7,"pass":7,"fail":0} and
    kx[-1].get("python_import")=="PASS",
    "KXMLGui ledger tests/import")

if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 Level 1 Attempt 8 historical closure evidence: PASS")
print(SNAPSHOT)
print("KIO=FAIL 6.30.0-0supralinux8 67/69; KXMLGui=PASS 6.30.0-0supralinux5 7/7")
print("historical_next_gate="+NEXT)
