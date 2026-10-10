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
W=(ROOT/".github/workflows/diagnostic-infrastructure-preflight.yml").read_text()
RUNNER=(ROOT/"scripts/run-diagnostic-infrastructure-preflight.sh").read_text()
DOC=(ROOT/"docs/decisions/diagnostic-infrastructure-preflight-2026-09-26.md").read_text()

req(M.get("schema")==1 and M.get("scope")=="diagnostic-infrastructure-preflight","preflight identity")
req(M.get("authority")=="supralinux-ci-architecture","preflight authority")
req(M.get("status")=="PASS" and M.get("execution_authorized") is False,"preflight closed PASS lifecycle")
req(M.get("package_execution_authorized") is False and M.get("canonical_state_effect")=="none","preflight package safety")
req(M.get("authoritative") is False,"hosted preflight is not release authority")

rootfs=M.get("rootfs_reference",{})
req(rootfs.get("workflow_run")==36238357510 and rootfs.get("artifact_id")==10904512642,"preflight rootfs identity")
req(rootfs.get("artifact_sha256")=="d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe","preflight rootfs artifact digest")
req(rootfs.get("tar_sha256")=="790139881455b78e00621f1b8ab02efaee899b7e6873f4d65ae0ff7fa295020e","preflight rootfs tar digest")

s=M.get("sbuild_contract",{})
req(s.get("version")=="0.91.2ubuntu3" and s.get("chroot_mode")=="unshare","preflight sbuild contract")
req(s.get("host_to_chroot")=="pre-build-commands + %SBUILD_CHROOT_EXEC stdin","preflight host/chroot transport")
req(s.get("chroot_to_host")=="external-command stdout evidence stream","preflight evidence return")
req(s.get("package_build_prevention")=="starting-build hook exits sentinel before dpkg-buildpackage","preflight stop-before-build contract")

p=M.get("retry_policy",{})
req(p.get("max_consecutive_infra_invalid_before_methodology_review")==2,"preflight retry cutoff")
req(p.get("target_package_must_not_be_first_infrastructure_probe") is True,"preflight cheap-first policy")
req(p.get("infra_preflight_required_for_new_diagnostic_mechanism") is True,"preflight requirement policy")

ev=M.get("evidence",{})
req(ev.get("workflow_run")==36286096599 and ev.get("job_id")==108527097646,"preflight PASS run/job")
req(ev.get("commit")=="340da99451a86b65513efcbfcae6b6b7145a2a96","preflight PASS commit")
req(ev.get("artifact_id")==10920194622,"preflight PASS artifact")
req(ev.get("artifact_sha256")=="ee6adecf77aa5110db735220bca0ebecd2a4a41b4a2b8dacc6692816866c1d39","preflight PASS artifact digest")
req(ev.get("result")=="PASS" and ev.get("stage")=="complete","preflight PASS result")
req(ev.get("rootfs_tar_sha256")==rootfs.get("tar_sha256"),"preflight evidence rootfs parity")
req(ev.get("sbuild_exit_code")==1,"preflight sentinel sbuild exit")
req(ev.get("package_attempted") is False and ev.get("canonical_state_effect")=="none","preflight evidence package safety")

req("workflow_call" in W and "workflow_dispatch" in W and "pull_request:" not in W,"preflight workflow reusable/manual only")
for token in ("10904512642","0.91.2ubuntu3","%SBUILD_CHROOT_EXEC","pre-build-commands","starting-build-commands",
              "SUPRALINUX_DIAGNOSTIC_PREFLIGHT_EVIDENCE_BEGIN","Command: dpkg-buildpackage","perl -c"):
    req(token in RUNNER,"preflight runner token "+token)
req("kf6-kio" not in RUNNER and "krecent" not in RUNNER.lower(),"preflight must not exercise KIO")
req("max_consecutive_infra_invalid_before_methodology_review" in DOC and "PASS" in DOC,"preflight decision docs")
req(M.get("next_gate")=="tier3-round23-krecent-attempt8-full-build-path-diagnostic-evidence","preflight closed handoff")

print("Diagnostic infrastructure preflight historical evidence: PASS")
print("workflow_run=36286096599")
print("artifact_id=10920194622")
print("canonical_state_effect=none")
