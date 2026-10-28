#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round26-diagnostic"
INPUTS="${WORK}/inputs"
ROOTFS_DIR="${WORK}/rootfs-artifact"
OUT="${WORK}/out"
CONFIG="${WORK}/sbuild-config.pl"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round26-diagnostic"
SBUILD_LOG="${EVIDENCE}/sbuild.log"
RESULT="${EVIDENCE}/result.json"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STAGE=initialization
DIAG_RESULT=DIAG_INFRA_FAIL
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${INPUTS}" "${ROOTFS_DIR}" "${OUT}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

# shellcheck disable=SC2329
finish() {
  local rc="$1" finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ ! -s "${RESULT}" ]]; then
    python3 - "${RESULT}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished}" <<'PY'
import json,sys
from pathlib import Path
p,result,rc,stage,started,finished=sys.argv[1:]
Path(p).write_text(json.dumps({
  "schema":1,"node":"kio","round":26,"diagnostic_result":result,
  "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
  "claim":"non-promoting-kio-kdirmodel-hidden-home-causality-and-combined-remediation-proof",
  "package_attempted":False,"diagnostic_build_path_invoked":stage not in {"initialization","contract","host-tools"},
  "package_state_effect":"none"
},indent=2,sort_keys=True)+"\n")
PY
  fi
}
trap 'finish "$?"' EXIT

download_artifact() {
  local id="$1" sha="$2" dest="$3" zip
  mkdir -p "${dest}"
  zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" \
    -o "${zip}"
  printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}

STAGE=contract
python3 scripts/validate_kde_tier3_kio_round26_remediation.py

STAGE=host-tools
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  curl dpkg-dev python3 sbuild uidmap unzip xz-utils
sbuild --version | tee "${EVIDENCE}/sbuild-version.txt"
grep -F "0.91.2ubuntu3" "${EVIDENCE}/sbuild-version.txt"
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true

STAGE=attempt8-rootfs-download
download_artifact 10904512642 d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe "${ROOTFS_DIR}"
ROOTFS_TAR="$(find "${ROOTFS_DIR}" -type f -name 'resolute-amd64.tar' -print -quit)"
ROOTFS_SHA="$(find "${ROOTFS_DIR}" -type f -name 'rootfs.sha256' -print -quit)"
[[ -n "${ROOTFS_TAR}" && -s "${ROOTFS_TAR}" && -n "${ROOTFS_SHA}" && -s "${ROOTFS_SHA}" ]]
expected="$(awk '{print $1}' "${ROOTFS_SHA}")"
actual="$(sha256sum "${ROOTFS_TAR}" | awk '{print $1}')"
[[ "${expected}" == "${actual}" ]]
[[ "${actual}" == "790139881455b78e00621f1b8ab02efaee899b7e6873f4d65ae0ff7fa295020e" ]]
printf '%s\n' "${actual}" > "${EVIDENCE}/rootfs-tar.sha256"
cp "${ROOTFS_DIR}/provenance.txt" "${EVIDENCE}/attempt8-rootfs-provenance.txt" 2>/dev/null || true
SBUILD_CACHE="${HOME}/.cache/sbuild"
mkdir -p "${SBUILD_CACHE}"
ln -sfn "${ROOTFS_TAR}" "${SBUILD_CACHE}/resolute-amd64.tar"
readlink -f "${SBUILD_CACHE}/resolute-amd64.tar" > "${EVIDENCE}/sbuild-rootfs-cache-target.txt"

STAGE=input-plan
python3 - "${LEVEL1}" "${EVIDENCE}/input-plan.json" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text()); n=m["nodes"]["kio"]
if n["package_version"]!="6.30.0-0supralinux8": raise SystemExit("unexpected KIO revision")
if n.get("sbuild_enable_network") is not True: raise SystemExit("Attempt8 KIO network contract drift")
specs=[]
def add(i,c,kind):
    specs.append({
      "id":i,"kind":kind,"workflow_run":c.get("workflow_run"),
      "artifact_id":c["artifact_id"],"artifact_sha256":c["artifact_sha256"],
      "version":c["version"],"expected_binary_packages":c["expected_binary_packages"],
      "dev_package":c.get("dev_package")
    })
add("extra-cmake-modules",m["shared_predecessors"]["extra-cmake-modules"],"shared")
for i in n["retained_input_ids"]: add(i,m["retained_predecessors"][i],"retained")
for i in n.get("support_input_ids",[]): add(i,m["support_predecessors"][i],"support")
if len({x["id"] for x in specs})!=len(specs): raise SystemExit("duplicate provider input")
plan={
  "node":"kio","package_version":n["package_version"],
  "materialization":n["materialization"],"inputs":specs,
  "sbuild_enable_network":True,
  "attempt8_workflow_run":36238357510,
  "attempt8_job_id":108394325161
}
Path(sys.argv[2]).write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
PY

STAGE=source-download
download_artifact 10898999142 c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d "${INPUTS}/materialization"

STAGE=source-validation
python3 - "${INPUTS}/materialization" "${EVIDENCE}" <<'PY'
import hashlib,json,shlex,sys
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2])
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
def one(pattern):
    xs=list(root.rglob(pattern))
    if len(xs)!=1: raise SystemExit(f"expected exactly one {pattern}, got {len(xs)}")
    return xs[0]
r=json.loads(one("result.json").read_text())
if r.get("result")!="PASS" or r.get("package_attempted") is not False: raise SystemExit("KIO materialization is not source-only PASS")
if r.get("node")!="kio" or r.get("package_version")!="6.30.0-0supralinux8": raise SystemExit("KIO materialization identity drift")
dsc=one("*.dsc"); orig=one("*.orig.tar.*"); debtar=one("*.debian.tar.*")
for p,key in ((dsc,"dsc_sha256"),(orig,"orig_tar_sha256"),(debtar,"debian_tar_sha256")):
    if sha(p)!=r.get(key): raise SystemExit(f"materialization hash mismatch: {p.name}")
(out/"materialization-result.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
(out/"source-env.sh").write_text(f"DSC={shlex.quote(str(dsc))}\n")
PY
source "${EVIDENCE}/source-env.sh"

STAGE=provider-download
python3 - "${EVIDENCE}/input-plan.json" <<'PY' > "${EVIDENCE}/artifact-inputs.tsv"
import json,sys
p=json.load(open(sys.argv[1]))
for x in p["inputs"]:
    print(f"{x['id']}\t{x['artifact_id']}\t{x['artifact_sha256']}")
PY
TAB="$(printf '\t')"
while IFS="${TAB}" read -r input_id artifact_id artifact_sha; do
  download_artifact "${artifact_id}" "${artifact_sha}" "${INPUTS}/${input_id}"
done < "${EVIDENCE}/artifact-inputs.tsv"

STAGE=provider-validation
python3 - "${EVIDENCE}/input-plan.json" "${INPUTS}" "${EVIDENCE}" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
plan=json.load(open(sys.argv[1])); root=Path(sys.argv[2]); out=Path(sys.argv[3])
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
def meta(p):
    return tuple(subprocess.check_output(["dpkg-deb","-f",str(p),f],text=True).strip() for f in ("Package","Version"))
all_debs=[]; records={}; owners={}
for spec in plan["inputs"]:
    idir=root/spec["id"]; actual={}; paths={}
    for p in sorted(idir.rglob("*.deb")):
        pkg,ver=meta(p)
        if pkg in actual: raise SystemExit(f"{spec['id']}: duplicate binary {pkg}")
        if ver!=spec["version"]: raise SystemExit(f"{spec['id']}: {pkg} version {ver} != {spec['version']}")
        if pkg in owners: raise SystemExit(f"duplicate provider binary {pkg}")
        owners[pkg]=spec["id"]; actual[pkg]=sha(p); paths[pkg]=str(p)
    if set(actual)!=set(spec["expected_binary_packages"]):
        raise SystemExit(f"{spec['id']}: binary set mismatch")
    all_debs.extend(paths[p] for p in sorted(paths))
    records[spec["id"]]={**spec,"files":actual}
(out/"retained-inputs.json").write_text(json.dumps(records,indent=2,sort_keys=True)+"\n")
(out/"predecessor-debs.txt").write_text("\n".join(all_debs)+"\n")
PY
mapfile -t PREDECESSOR_DEBS < "${EVIDENCE}/predecessor-debs.txt"
(( ${#PREDECESSOR_DEBS[@]} > 0 ))

STAGE=sbuild-config
python3 - "${CONFIG}" "${ROOT}/scripts/run-kde-tier3-kio-round26-hook.sh" <<'PY'
import shlex,sys
from pathlib import Path
path,hook=sys.argv[1:]
host_hook=shlex.quote(hook)
copy_command=f"cat {host_hook} | %SBUILD_CHROOT_EXEC sh -c 'cat > /tmp/supralinux-round26-hook.sh && chmod 0755 /tmp/supralinux-round26-hook.sh'"
text="""$chroot_mode = 'unshare';
$unshare_mmdebstrap_auto_create = 0;
$run_lintian = 0;
$run_autopkgtest = 0;
$run_piuparts = 0;
$log_external_command_output = 1;
$log_external_command_error = 1;
$external_commands = {
  'pre-build-commands' => [ __COPY_COMMAND__ ],
  'starting-build-commands' => [ [ '/bin/bash', '/tmp/supralinux-round26-hook.sh', '%p' ] ],
};
1;
"""
Path(path).write_text(text.replace("__COPY_COMMAND__",repr(copy_command)))
PY
cp "${CONFIG}" "${EVIDENCE}/sbuild-config.pl"
perl -c "${CONFIG}" |& tee "${EVIDENCE}/sbuild-config-check.txt"
bash -n "${ROOT}/scripts/run-kde-tier3-kio-round26-hook.sh"

STAGE=sbuild-historical-build-path
EXTRA_ARGS=()
for deb in "${PREDECESSOR_DEBS[@]}"; do EXTRA_ARGS+=(--extra-package="${deb}"); done
EXTRA_ARGS+=(--enable-network)
set +e
SBUILD_CONFIG="${CONFIG}" sbuild --verbose --chroot-mode=unshare --dist=resolute \
  --arch=amd64 --arch-all "${EXTRA_ARGS[@]}" --build-dir="${OUT}" "${DSC}" |& tee "${SBUILD_LOG}"
SBUILD_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${SBUILD_RC}" > "${EVIDENCE}/sbuild-exit-code.txt"

STAGE=historical-path-proof
(( SBUILD_RC != 0 ))
grep -Fq 'SUPRALINUX_ROUND26_PREPARED krecent-candidate-applied-hidden-home-test-ready' "${SBUILD_LOG}"
grep -Fq 'Command: dpkg-buildpackage --sanitize-env -us -uc -b' "${SBUILD_LOG}"
grep -Fq 'debian/rules binary' "${SBUILD_LOG}"
grep -Fq '/tmp/supralinux-round26-test-stage.sh' "${SBUILD_LOG}"
if find "${OUT}" -maxdepth 1 -type f \( -name '*.deb' -o -name '*.changes' -o -name '*.buildinfo' \) -print -quit | grep -q .; then
  echo "candidate package artifacts were produced; Round26 combined remediation proof invalid" >&2
  exit 84
fi
printf '%s\n' \
  'sbuild -> dpkg-buildpackage --sanitize-env -us -uc -b -> debian/rules binary reached' \
  'combined remediation proof aborted inside override_dh_auto_test before package artifacts' \
  > "${EVIDENCE}/historical-build-path-proof.txt"

STAGE=sbuild-evidence-recovery
python3 - "${SBUILD_LOG}" "${EVIDENCE}" <<'PY'
import base64,io,sys,tarfile
from pathlib import Path
log=Path(sys.argv[1]).read_text(errors="replace").splitlines(); out=Path(sys.argv[2])
begin="SUPRALINUX_ROUND26_EVIDENCE_BASE64_BEGIN"; end="SUPRALINUX_ROUND26_EVIDENCE_BASE64_END"
try:
    a=log.index(begin); b=log.index(end,a+1)
except ValueError as exc:
    raise SystemExit(f"Round26 evidence markers missing: {exc}")
payload="".join(line.strip() for line in log[a+1:b] if line.strip())
raw=base64.b64decode(payload,validate=True)
(out/"round26-evidence.tar.gz").write_bytes(raw)
with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as tf:
    for m in tf.getmembers():
        p=Path(m.name)
        if p.is_absolute() or ".." in p.parts: raise SystemExit(f"unsafe evidence member: {m.name}")
    tf.extractall(out)
PY

STAGE=matrix-classification
[[ -f "${EVIDENCE}/preparation-complete" ]]
[[ -f "${EVIDENCE}/matrix-complete" ]]
[[ -f "${EVIDENCE}/hook-complete" ]]
[[ -f "${EVIDENCE}/source-restored" ]]
[[ -f "${EVIDENCE}/test-homes-cleaned" ]]
[[ -s "${EVIDENCE}/candidate-remediation.patch" ]]
[[ -s "${EVIDENCE}/candidate-source.sha256" ]]
[[ -s "${EVIDENCE}/candidate-patch.sha256" ]]
[[ -s "${EVIDENCE}/kdirmodel-runs.tsv" ]]
[[ -s "${EVIDENCE}/full-suite-visible.log" ]]
[[ -s "${EVIDENCE}/full-suite-visible.rc" ]]
python3 - "${EVIDENCE}" "${RESULT}" "${STARTED_AT}" <<'PY'
import json,sys
from pathlib import Path

ev=Path(sys.argv[1]); result=Path(sys.argv[2]); started=sys.argv[3]
rows=[]
for line in (ev/"kdirmodel-runs.tsv").read_text().splitlines():
    if not line.strip():
        continue
    lane,run,rc,exact=line.split("\t")
    rows.append({"lane":lane,"run":int(run),"rc":int(rc),"exact_historical_signature":exact=="1"})

summary={}
for lane,expected in (("hidden-home",10),("visible-home",20)):
    xs=[x for x in rows if x["lane"]==lane]
    summary[lane]={
      "runs":len(xs),
      "expected_runs":expected,
      "nonzero_rc_runs":sum(x["rc"]!=0 for x in xs),
      "exact_historical_signature_runs":sum(x["exact_historical_signature"] for x in xs),
    }

full_log=(ev/"full-suite-visible.log").read_text(errors="replace")
full_rc=int((ev/"full-suite-visible.rc").read_text().strip())
full_69_pass=("100% tests passed, 0 tests failed out of 69" in full_log)
full_krecent_pass=("kiocore-krecentdocumenttest" in full_log and "Passed" in full_log)
full_kdirmodel_pass=("kiowidgets-kdirmodeltest" in full_log and "Passed" in full_log)
xbel=ev/"full-suite-visible.xbel"
order=Path(str(xbel)+".order")
full_order=order.read_text(errors="replace").splitlines() if order.is_file() else []
full_krecent_order_ok=full_order==["temp File 12","temp File 13","temp File 14"]

candidate_patch_sha=(ev/"candidate-patch.sha256").read_text().split()[0]
candidate_source_sha=(ev/"candidate-source.sha256").read_text().split()[0]
historical_candidate_patch_sha="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602"
candidate_reused=(candidate_patch_sha==historical_candidate_patch_sha)

test_before=(ev/"test-source-before.sha256").read_text().split()[0]
test_after=(ev/"test-source-after.sha256").read_text().split()[0]
core_before=(ev/"core-source-before.sha256").read_text().split()[0]
core_after=(ev/"core-source-after.sha256").read_text().split()[0]
rules_before=(ev/"rules-before.sha256").read_text().split()[0]
rules_after=(ev/"rules-after.sha256").read_text().split()[0]
source_restored=test_before==test_after and core_before==core_after
rules_restored=rules_before==rules_after

hidden=summary["hidden-home"]
visible=summary["visible-home"]
hidden_reproduced=(hidden["runs"]==10 and hidden["nonzero_rc_runs"]==10 and hidden["exact_historical_signature_runs"]==10)
visible_fixed=(visible["runs"]==20 and visible["nonzero_rc_runs"]==0 and visible["exact_historical_signature_runs"]==0)
combined_suite_pass=(full_rc==0 and full_69_pass and full_krecent_pass and full_kdirmodel_pass and full_krecent_order_ok)

valid=(
    len(rows)==30
    and hidden["runs"]==10
    and visible["runs"]==20
    and candidate_reused
    and source_restored
    and rules_restored
    and (ev/"test-homes-cleaned").is_file()
    and xbel.is_file()
    and order.is_file()
)

if not valid:
    conclusion="REMEDIATION_INVALID-evidence-or-historical-path-contract"
    diag="REMEDIATION_INVALID"
elif hidden_reproduced and visible_fixed and combined_suite_pass:
    conclusion="hidden-home-causality-and-combined-kio-remediation-PASS"
    diag="REMEDIATION_PASS"
elif not hidden_reproduced:
    conclusion="hidden-home-causality-inconclusive"
    diag="REMEDIATION_FAIL"
elif not visible_fixed:
    conclusion="visible-home-remediation-FAIL"
    diag="REMEDIATION_FAIL"
else:
    conclusion="combined-full-suite-remediation-FAIL"
    diag="REMEDIATION_FAIL"

payload={
  "schema":1,
  "node":"kio",
  "round":26,
  "diagnostic_result":diag,
  "claim":"non-promoting-kio-kdirmodel-hidden-home-causality-and-combined-remediation-proof",
  "package_attempted":False,
  "diagnostic_build_path_invoked":True,
  "package_state_effect":"none",
  "environment_valid":valid,
  "containment":"sbuild-0.91.2ubuntu3-unshare",
  "historical_build_path":"sbuild -> dpkg-buildpackage --sanitize-env -us -uc -b -> debian/rules binary -> override_dh_auto_test",
  "source_restored":source_restored,
  "rules_restored":rules_restored,
  "candidate_patch_sha256":candidate_patch_sha,
  "candidate_source_sha256":candidate_source_sha,
  "historical_candidate_patch_reused":candidate_reused,
  "kdirmodel_matrix":summary,
  "hidden_home_causality_reproduced":hidden_reproduced,
  "visible_home_remediation_pass":visible_fixed,
  "full_suite_visible":{
    "rc":full_rc,
    "all_69_tests_pass":full_69_pass,
    "krecent_pass":full_krecent_pass,
    "kdirmodel_pass":full_kdirmodel_pass,
    "krecent_final_order":full_order,
    "krecent_final_order_ok":full_krecent_order_ok
  },
  "combined_suite_pass":combined_suite_pass,
  "conclusion":conclusion,
  "started_at":started
}
result.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
print(json.dumps(payload,indent=2,sort_keys=True))
if diag!="REMEDIATION_PASS":
    raise SystemExit(85)
PY

DIAG_RESULT=REMEDIATION_PASS
STAGE=complete
exit 0

