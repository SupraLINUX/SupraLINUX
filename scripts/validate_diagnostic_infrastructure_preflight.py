#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT/path).read_text())

def req(value,message):
    if not value:
        print("ERROR:",message,file=sys.stderr)
        raise SystemExit(1)

M=load("manifests/diagnostic-infrastructure-preflight.json")
T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
MAT=load("manifests/kde-tier3-materialization.json")
R23=load("manifests/kde-tier3-kio-round23-diagnostic.json")
W=(ROOT/".github/workflows/diagnostic-infrastructure-preflight.yml").read_text()
RUNNER=(ROOT/"scripts/run-diagnostic-infrastructure-preflight.sh").read_text()
DOC=(ROOT/"docs/decisions/diagnostic-infrastructure-preflight-2026-09-26.md").read_text()

req(M.get("schema")==1 and M.get("scope")=="diagnostic-infrastructure-preflight","preflight identity")
req(M.get("authority")=="supralinux-ci-architecture","preflight authority")
req(M.get("status")=="definition-pending-ci" and M.get("execution_authorized") is True,"preflight live authorization")
req(M.get("package_execution_authorized") is False and M.get("canonical_state_effect")=="none","preflight package safety")
rootfs=M.get("rootfs_reference",{})
req(rootfs.get("artifact_id")==10904512642,"preflight rootfs artifact")
req(rootfs.get("artifact_sha256")=="d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe","preflight rootfs digest")
s=M.get("sbuild_contract",{})
req(s.get("version")=="0.91.2ubuntu3" and s.get("chroot_mode")=="unshare","preflight sbuild contract")
req(s.get("host_to_chroot")=="pre-build-commands + %SBUILD_CHROOT_EXEC stdin","preflight host/chroot transport")
req(s.get("chroot_to_host")=="external-command stdout evidence stream","preflight evidence return")
p=M.get("retry_policy",{})
req(p.get("max_consecutive_infra_invalid_before_methodology_review")==2,"preflight retry cutoff")
req(p.get("target_package_must_not_be_first_infrastructure_probe") is True,"preflight cheap-first policy")

gate="diagnostic-infrastructure-preflight-evidence"
policy=T.get("discovery_policy",{})
req(policy.get("phase")=="diagnostic-infrastructure-preflight","live phase")
req(policy.get("package_builds")=="diagnostic-infrastructure-preflight-pending","live package gate")
req(policy.get("remediation")=="round23-blocked-pending-diagnostic-infrastructure-preflight","live remediation")
for obj,name in ((T.get("active_remediation",{}),"canonical"),(L.get("active_remediation",{}),"level1"),(C.get("active_remediation",{}),"contracts"),(MAT.get("active_remediation",{}),"materialization")):
    req(obj.get("next_gate")==gate,name+" next gate")
req(T.get("active_remediation",{}).get("execution_authorized") is False,"package execution remains unauthorized")
req(L.get("execution_authorized") is False and L.get("current_attempt")==8,"Attempt9 remains unauthorized")
req(R23.get("status")=="BLOCKED-pending-diagnostic-infrastructure-preflight","Round23 blocked status")
req(R23.get("execution_authorized") is False and R23.get("package_execution_authorized") is False,"Round23 blocked authorization")

req("workflow_call" in W and "workflow_dispatch" in W and "pull_request:" not in W,"preflight workflow reusable/manual only")
for token in ("10904512642","0.91.2ubuntu3","%SBUILD_CHROOT_EXEC","pre-build-commands","starting-build-commands",
              "SUPRALINUX_DIAGNOSTIC_PREFLIGHT_EVIDENCE_BEGIN","Command: dpkg-buildpackage","perl -c"):
    req(token in RUNNER,"preflight runner token "+token)
req("kf6-kio" not in RUNNER and "krecent" not in RUNNER.lower(),"preflight must not exercise KIO")
req("max_consecutive_infra_invalid_before_methodology_review" in DOC and "cheap synthetic" in DOC.lower(),"preflight decision docs")
req(M.get("next_gate")==gate,"preflight next gate")
print("Diagnostic infrastructure preflight definition: PASS")
print("Round23=BLOCKED")
print("Attempt9=NOT-AUTHORIZED")
