#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(value, message):
    if not value:
        errors.append(message)

def load(path):
    return json.loads((ROOT / path).read_text())

# Historical validator: validate only frozen Attempt 10 evidence.
# Never constrain current Tier 3, DAG, Level 1, contract, or materialization live state.
A = load("manifests/kde-tier3-build-level1-attempts.json")
R = load("manifests/kde-tier3-kio-attempt10-remediation.json")

RUN = 36425867815
COMMIT = "dc7cedb37689eb6eb27b6034b58584c33985a5b0"
NEXT = "tier3-build-level2-planning"
ROOTFS = {
    "artifact_id": 10971154003,
    "artifact_sha256": "963ca24b1ef3e5b97cb0a52d767ae22696f21d16921315690b08266756ee1103",
}
KIO_JOB = 108939890139
KIO_ART = 10972557457
KIO_SHA = "700a7abebfaca99ae76e36cfb8f54798694732f248b0002224025cfc80d94056"
KIO_VERSION = "6.30.0-0supralinux10"
KXML_JOB = 108939889724
KXML_ART = 10971509790
KXML_SHA = "a4a5bac1ca996792cc9d44e20d68d451ac61ea0a30811781260299bf87a04c00"
KXML_VERSION = "6.30.0-0supralinux5"

hist = [e for e in A.get("campaign_history", []) if e.get("attempt") == 10]
req(
    len(hist) == 1
    and hist[0].get("workflow_run") == RUN
    and hist[0].get("commit") == COMMIT
    and hist[0].get("result") == "PASS"
    and hist[0].get("workflow_jobs") == {"success": 2, "fail": 0}
    and hist[0].get("pass_nodes") == ["kio", "kxmlgui"]
    and hist[0].get("failed_nodes") == []
    and hist[0].get("blocked_nodes") == []
    and hist[0].get("canonical_promotions") == 1
    and hist[0].get("canonical_pass_nodes") == ["kio"]
    and hist[0].get("revalidation_nodes") == ["kxmlgui"]
    and hist[0].get("next_gate") == NEXT,
    "Attempt10 campaign ledger",
)

ki = [e for e in A.get("nodes", {}).get("kio", []) if e.get("attempt") == 10]
req(len(ki) == 1, "Attempt10 KIO ledger cardinality")
if ki:
    e = ki[0]
    req(
        e.get("result") == "PASS"
        and e.get("workflow_run") == RUN
        and e.get("job_id") == KIO_JOB
        and e.get("commit") == COMMIT
        and e.get("artifact_id") == KIO_ART
        and e.get("artifact_sha256") == KIO_SHA
        and e.get("package_version") == KIO_VERSION
        and e.get("package_attempted") is True
        and e.get("stage") == "complete"
        and e.get("tests") == "69/69 PASS"
        and e.get("lintian") == "PASS-errors"
        and e.get("apt_check") == "PASS"
        and e.get("abi_contract") == "PASS"
        and e.get("cmake_consumer") == "PASS"
        and e.get("provider_closure_artifact_validation") == "PASS"
        and e.get("declared_runtime_input_proof") == "PASS"
        and e.get("buildinfo_predecessor_proof") == "PASS"
        and e.get("downstream_eligible") is True
        and e.get("package_state_effect") == "PASS",
        "Attempt10 KIO ledger evidence",
    )

kx = [e for e in A.get("nodes", {}).get("kxmlgui", []) if e.get("attempt") == 10]
req(len(kx) == 1, "Attempt10 KXMLGui ledger cardinality")
if kx:
    e = kx[0]
    req(
        e.get("result") == "PASS"
        and e.get("workflow_run") == RUN
        and e.get("job_id") == KXML_JOB
        and e.get("commit") == COMMIT
        and e.get("artifact_id") == KXML_ART
        and e.get("artifact_sha256") == KXML_SHA
        and e.get("package_version") == KXML_VERSION
        and e.get("package_attempted") is True
        and e.get("stage") == "complete"
        and e.get("tests") == "7/7 PASS"
        and e.get("python_import") == "PASS"
        and e.get("package_state_effect") == "PASS-revalidation"
        and e.get("package_version_unchanged") is True,
        "Attempt10 KXMLGui ledger evidence",
    )

req(
    R.get("schema") == 1
    and R.get("attempt") == 10
    and R.get("node") == "kio"
    and R.get("authority") == "kde-upstream"
    and R.get("frameworks_series") == "6.30.0",
    "Attempt10 historical identity",
)
req(
    R.get("status") == "attempt10-closed-PASS"
    and R.get("candidate_package_version") == KIO_VERSION
    and R.get("execution_authorized") is False
    and R.get("package_execution_authorized") is False
    and R.get("level1_execution_authorized") is False,
    "Attempt10 historical closure",
)

mat = R.get("materialization_evidence", {})
req(
    mat.get("workflow_run") == 36424068585
    and mat.get("job_id") == 108933677695
    and mat.get("commit") == "a77f6e1f247792ccb486720010d969e2cbc41680"
    and mat.get("artifact_id") == 10970466420
    and mat.get("artifact_sha256") == "f25ae14e1f393d24f95b1118680d7967f6bef449c8790981b170cfb78a1f3d22"
    and mat.get("package_version") == KIO_VERSION
    and mat.get("result") == "PASS"
    and mat.get("package_attempted") is False
    and mat.get("package_state_effect") == "none",
    "Attempt10 materialization evidence",
)

rr = R.get("attempt10_result", {})
req(
    rr.get("workflow_run") == RUN
    and rr.get("commit") == COMMIT
    and rr.get("result") == "PASS"
    and rr.get("rootfs") == ROOTFS
    and rr.get("canonical_snapshot") == "13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED"
    and rr.get("canonical_promotions") == 1
    and rr.get("next_gate") == NEXT,
    "Attempt10 result identity",
)
req(
    rr.get("kio", {}).get("job_id") == KIO_JOB
    and rr.get("kio", {}).get("artifact_id") == KIO_ART
    and rr.get("kio", {}).get("artifact_sha256") == KIO_SHA
    and rr.get("kio", {}).get("package_version") == KIO_VERSION
    and rr.get("kio", {}).get("tests") == "69/69 PASS"
    and rr.get("kio", {}).get("lintian") == "PASS-errors"
    and rr.get("kio", {}).get("apt_check") == "PASS"
    and rr.get("kio", {}).get("abi_contract") == "PASS"
    and rr.get("kio", {}).get("cmake_consumer") == "PASS"
    and rr.get("kio", {}).get("downstream_eligible") is True,
    "Attempt10 KIO result",
)
req(
    rr.get("kxmlgui", {}).get("job_id") == KXML_JOB
    and rr.get("kxmlgui", {}).get("artifact_id") == KXML_ART
    and rr.get("kxmlgui", {}).get("artifact_sha256") == KXML_SHA
    and rr.get("kxmlgui", {}).get("package_version") == KXML_VERSION
    and rr.get("kxmlgui", {}).get("tests") == "7/7 PASS"
    and rr.get("kxmlgui", {}).get("python_import") == "PASS"
    and rr.get("kxmlgui", {}).get("package_state_effect") == "PASS-revalidation",
    "Attempt10 KXMLGui result",
)
req(R.get("stable_promotion_requires_explicit_user_approval") is True, "Attempt10 stable policy")

if errors:
    for error in errors:
        print("ERROR:", error, file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 Level 1 Attempt 10 historical closure: PASS")
print("KIO 6.30.0-0supralinux10 = PASS; 69/69 tests; package gates PASS")
print("KXMLGui 6.30.0-0supralinux5 = PASS revalidation")
print("historical_snapshot=13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED")
print("historical_next_gate=" + NEXT)
