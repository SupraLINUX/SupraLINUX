#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round24-diagnostic"
INPUTS="${WORK}/inputs"
ROOTFS_DIR="${WORK}/rootfs-artifact"
OUT="${WORK}/out"
CONFIG="${WORK}/sbuild-config.pl"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round24-diagnostic"
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
  "schema":1,"node":"kio","round":24,"diagnostic_result":result,
  "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
  "claim":"non-promoting-krecent-timestamp-tie-causality-diagnostic",
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
python3 scripts/validate_kde_tier3_kio_round24_diagnostic.py

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
python3 - "${CONFIG}" "${ROOT}/scripts/run-kde-tier3-kio-round24-hook.sh" <<'PY'
import shlex,sys
from pathlib import Path
path,hook=sys.argv[1:]
host_hook=shlex.quote(hook)
copy_command=f"cat {host_hook} | %SBUILD_CHROOT_EXEC sh -c 'cat > /tmp/supralinux-round24-hook.sh && chmod 0755 /tmp/supralinux-round24-hook.sh'"
text="""$chroot_mode = 'unshare';
$unshare_mmdebstrap_auto_create = 0;
$run_lintian = 0;
$run_autopkgtest = 0;
$run_piuparts = 0;
$log_external_command_output = 1;
$log_external_command_error = 1;
$external_commands = {
  'pre-build-commands' => [ __COPY_COMMAND__ ],
  'starting-build-commands' => [ [ '/bin/bash', '/tmp/supralinux-round24-hook.sh', '%p' ] ],
};
1;
"""
Path(path).write_text(text.replace("__COPY_COMMAND__",repr(copy_command)))
PY
cp "${CONFIG}" "${EVIDENCE}/sbuild-config.pl"
perl -c "${CONFIG}" |& tee "${EVIDENCE}/sbuild-config-check.txt"
bash -n "${ROOT}/scripts/run-kde-tier3-kio-round24-hook.sh"

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
grep -Fq 'Command: dpkg-buildpackage --sanitize-env -us -uc -b' "${SBUILD_LOG}"
grep -Fq 'debian/rules binary' "${SBUILD_LOG}"
grep -Fq '/tmp/supralinux-round24-test-stage.sh' "${SBUILD_LOG}"
if find "${OUT}" -maxdepth 1 -type f \( -name '*.deb' -o -name '*.changes' -o -name '*.buildinfo' \) -print -quit | grep -q .; then
  echo "candidate package artifacts were produced; Round24 invalid" >&2
  exit 84
fi
printf '%s\n' \
  'sbuild -> dpkg-buildpackage --sanitize-env -us -uc -b -> debian/rules binary reached' \
  'diagnostic aborted inside override_dh_auto_test before package artifacts' \
  > "${EVIDENCE}/historical-build-path-proof.txt"

STAGE=sbuild-evidence-recovery
python3 - "${SBUILD_LOG}" "${EVIDENCE}" <<'PY'
import base64,io,sys,tarfile
from pathlib import Path
log=Path(sys.argv[1]).read_text(errors="replace").splitlines(); out=Path(sys.argv[2])
begin="SUPRALINUX_ROUND24_EVIDENCE_BASE64_BEGIN"; end="SUPRALINUX_ROUND24_EVIDENCE_BASE64_END"
try:
    a=log.index(begin); b=log.index(end,a+1)
except ValueError as exc:
    raise SystemExit(f"Round24 evidence markers missing: {exc}")
payload="".join(line.strip() for line in log[a+1:b] if line.strip())
raw=base64.b64decode(payload,validate=True)
(out/"round24-evidence.tar.gz").write_bytes(raw)
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
python3 - "${EVIDENCE}" "${RESULT}" "${STARTED_AT}" <<'PY'
import collections,json,sys,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path

ev=Path(sys.argv[1]); result=Path(sys.argv[2]); started=sys.argv[3]
rows=[]
for line in (ev/"runs.tsv").read_text().splitlines():
    if not line.strip():
        continue
    lane,run,rc,sig,failed,capture=line.split("\t")
    exists,order_lines=capture.split(":")
    cap=ev/"xbels"/f"{lane}-{run}.xbel"
    order=Path(str(cap)+".order")
    names=order.read_text(errors="replace").splitlines() if order.is_file() else []
    bookmarks=[]
    modified=[]
    if cap.is_file():
        root=ET.parse(cap).getroot()
        for e in root.iter():
            if str(e.tag).endswith("bookmark") and "href" in e.attrib:
                bookmarks.append(urllib.parse.unquote(e.attrib["href"]).rstrip("/").split("/")[-1])
                modified.append(e.attrib.get("modified",""))
    rows.append({
      "lane":lane,"run":int(run),"rc":int(rc),
      "attempt8_signature":sig=="1","krecent_failed":failed=="1",
      "capture_exists":exists=="1","order":names,"xbel_bookmarks":bookmarks,
      "modified_timestamps":modified,"timestamp_cardinality":len(set(modified)),
      "valid_capture":exists=="1" and int(order_lines)==3 and len(names)==3 and len(bookmarks)==3 and len(modified)==3 and all(modified)
    })

expected={"native":40,"monotonic":40,"fixed":20}
summary={}
valid=True
for lane,n in expected.items():
    xs=[x for x in rows if x["lane"]==lane]
    orders=collections.Counter(tuple(x["order"]) for x in xs if x["order"])
    cardinalities=collections.Counter(x["timestamp_cardinality"] for x in xs)
    summary[lane]={
      "runs":len(xs),"expected_runs":n,
      "valid_captures":sum(x["valid_capture"] for x in xs),
      "failed_runs":sum(x["krecent_failed"] for x in xs),
      "attempt8_signature_failures":sum(x["attempt8_signature"] for x in xs),
      "timestamp_cardinality_counts":{str(k):v for k,v in sorted(cardinalities.items())},
      "observed_orders":{" | ".join(k):v for k,v in sorted(orders.items())}
    }
    valid &= len(xs)==n and all(x["valid_capture"] for x in xs)

native=[x for x in rows if x["lane"]=="native"]
monotonic=[x for x in rows if x["lane"]=="monotonic"]
fixed=[x for x in rows if x["lane"]=="fixed"]
controlled_modes_verified=all(x["timestamp_cardinality"]==3 for x in monotonic) and all(x["timestamp_cardinality"]==1 for x in fixed)
valid &= controlled_modes_verified

test_before=(ev/"test-source-before.sha256").read_text().split()[0]
test_after=(ev/"test-source-after.sha256").read_text().split()[0]
core_before=(ev/"core-source-before.sha256").read_text().split()[0]
core_after=(ev/"core-source-after.sha256").read_text().split()[0]
rules_before=(ev/"rules-before.sha256").read_text().split()[0]
rules_after=(ev/"rules-after.sha256").read_text().split()[0]
source_restored=test_before==test_after and core_before==core_after
rules_restored=rules_before==rules_after
valid &= source_restored and rules_restored

nf=summary["native"]["failed_runs"]
mf=summary["monotonic"]["failed_runs"]
ff=summary["fixed"]["failed_runs"]
if not valid:
    conclusion="DIAG_INVALID-timestamp-control-or-historical-build-path-evidence"
    diag="DIAG_INVALID"
elif nf>0 and mf==0 and ff>0:
    conclusion="timestamp-tie-causality-confirmed"
    diag="DIAG_COMPLETE"
elif mf>0:
    conclusion="timestamp-tie-causality-refuted-or-insufficient-no-tie-still-fails"
    diag="DIAG_COMPLETE"
elif nf>0 and ff==0:
    conclusion="timestamp-tie-causality-inconclusive-fixed-tie-control-passed"
    diag="DIAG_COMPLETE"
else:
    conclusion="timestamp-tie-causality-inconclusive-native-control-did-not-reproduce"
    diag="DIAG_COMPLETE"

payload={
  "schema":1,"node":"kio","round":24,"diagnostic_result":diag,
  "claim":"non-promoting-krecent-timestamp-tie-causality-diagnostic",
  "package_attempted":False,"diagnostic_build_path_invoked":True,
  "package_state_effect":"none","environment_valid":valid,
  "containment":"sbuild-0.91.2ubuntu3-unshare",
  "historical_build_path":"sbuild -> dpkg-buildpackage --sanitize-env -us -uc -b -> debian/rules binary -> override_dh_auto_test",
  "source_restored":source_restored,"rules_restored":rules_restored,
  "controlled_timestamp_modes_verified":controlled_modes_verified,
  "matrix":summary,"conclusion":conclusion,"started_at":started
}
result.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
print(json.dumps(payload,indent=2,sort_keys=True))
if diag!="DIAG_COMPLETE":
    raise SystemExit(85)
PY

DIAG_RESULT=DIAG_COMPLETE
STAGE=complete
exit 0
