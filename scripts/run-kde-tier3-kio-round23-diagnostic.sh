#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round23-diagnostic"
INPUTS="${WORK}/inputs"
ROOTFS_DIR="${WORK}/rootfs-artifact"
HOOK_SHARE="${WORK}/hook-share"
OUT="${WORK}/out"
CONFIG="${WORK}/sbuild-config.pl"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round23-diagnostic"
SBUILD_LOG="${EVIDENCE}/sbuild.log"
RESULT="${EVIDENCE}/result.json"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STAGE=initialization
DIAG_RESULT=DIAG_INFRA_FAIL
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${INPUTS}" "${ROOTFS_DIR}" "${HOOK_SHARE}" "${OUT}" "${EVIDENCE}/xbels"
chmod 0777 "${EVIDENCE}" "${EVIDENCE}/xbels"
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
Path(p).write_text(json.dumps({"schema":1,"node":"kio","round":23,"diagnostic_result":result,
 "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
 "claim":"non-promoting-krecent-attempt8-rootfs-diagnostic","package_attempted":False,
 "package_state_effect":"none"},indent=2,sort_keys=True)+"\n")
PY
  fi
}
trap 'finish "$?"' EXIT

download_artifact() {
  local id="$1" sha="$2" dest="$3" zip
  mkdir -p "${dest}"; zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" -o "${zip}"
  printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}

STAGE=contract
python3 scripts/validate_kde_tier3_kio_round23_diagnostic.py

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
printf '%s\n' "${actual}" > "${EVIDENCE}/rootfs-tar.sha256"
cp "${ROOTFS_DIR}/provenance.txt" "${EVIDENCE}/attempt8-rootfs-provenance.txt" 2>/dev/null || true
SBUILD_CACHE="${HOME}/.cache/sbuild"
mkdir -p "${SBUILD_CACHE}"
ln -sfn "${ROOTFS_TAR}" "${SBUILD_CACHE}/resolute-amd64.tar"
readlink -f "${SBUILD_CACHE}/resolute-amd64.tar" > "${EVIDENCE}/sbuild-rootfs-cache-target.txt"

python3 - "${ROOTFS_TAR}" "${EVIDENCE}/rootfs-mountpoints.json" <<'PY'
import json,sys,tarfile
from pathlib import Path
tar_path,out=sys.argv[1:]
required=("mnt","media")
with tarfile.open(tar_path) as tf:
    entries={}
    for member in tf.getmembers():
        name=member.name
        while name.startswith("./"):
            name=name[2:]
        name=name.rstrip("/")
        if name:
            entries[name]=member
report={}
for path in required:
    member=entries.get(path)
    children=sorted(name for name in entries if name.startswith(path+"/"))
    if member is None or not member.isdir():
        raise SystemExit(f"required rootfs mountpoint /{path} missing or not a directory")
    if children:
        raise SystemExit(f"required rootfs mountpoint /{path} is not empty: {children[:10]}")
    report[path]={"exists":True,"directory":True,"empty":True}
Path(out).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
PY

STAGE=input-plan
python3 - "${LEVEL1}" "${EVIDENCE}/input-plan.tsv" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text()); n=m["nodes"]["kio"]
if n["package_version"]!="6.30.0-0supralinux8": raise SystemExit("unexpected KIO revision")
rows=[]
def add(i,c): rows.append((i,str(c["artifact_id"]),c["artifact_sha256"],c["version"]))
add("extra-cmake-modules",m["shared_predecessors"]["extra-cmake-modules"])
for i in n["retained_input_ids"]: add(i,m["retained_predecessors"][i])
for i in n.get("support_input_ids",[]): add(i,m["support_predecessors"][i])
if len({r[0] for r in rows})!=len(rows): raise SystemExit("duplicate provider input")
Path(sys.argv[2]).write_text("\n".join("\t".join(r) for r in rows)+"\n")
PY

STAGE=source-download
download_artifact 10898999142 c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d "${INPUTS}/materialization"
DSC="$(find "${INPUTS}/materialization" -type f -name '*.dsc' -print -quit)"
[[ -n "${DSC}" && -s "${DSC}" ]]

STAGE=provider-download
TAB="$(printf '\t')"
while IFS="${TAB}" read -r input_id artifact_id artifact_sha version; do
  printf '%s\t%s\t%s\n' "${input_id}" "${version}" "${artifact_id}" >> "${EVIDENCE}/provider-plan.tsv"
  download_artifact "${artifact_id}" "${artifact_sha}" "${INPUTS}/${input_id}"
done < "${EVIDENCE}/input-plan.tsv"

mapfile -t PREDECESSOR_DEBS < <(find "${INPUTS}" -mindepth 2 -type f -name '*.deb' -print | sort)
(( ${#PREDECESSOR_DEBS[@]} > 0 ))
printf '%s\n' "${PREDECESSOR_DEBS[@]}" > "${EVIDENCE}/predecessor-debs.txt"
cp "${ROOT}/scripts/run-kde-tier3-kio-round23-hook.sh" "${HOOK_SHARE}/hook.sh"
chmod 0755 "${HOOK_SHARE}/hook.sh"

STAGE=sbuild-config
python3 - "${CONFIG}" "${HOOK_SHARE}" "${EVIDENCE}" <<'PY'
import sys
from pathlib import Path
path,hook,evidence=sys.argv[1:]
def q(s): return "'" + s.replace("\\","\\\\").replace("'","\\'") + "'"
text="""$chroot_mode = 'unshare';
$unshare_mmdebstrap_auto_create = 0;
$unshare_bind_mounts = [
  { directory => __HOOK__, mountpoint => '/mnt' },
  { directory => __EVIDENCE__, mountpoint => '/media' },
];
$run_lintian = 0;
$run_autopkgtest = 0;
$run_piuparts = 0;
$external_commands = {
  'starting-build-commands' => [ [ '/bin/bash', '/mnt/hook.sh', '%p' ] ],
};
1;
"""
text=text.replace("__HOOK__",q(hook)).replace("__EVIDENCE__",q(evidence))
Path(path).write_text(text)
PY
cp "${CONFIG}" "${EVIDENCE}/sbuild-config.pl"

STAGE=sbuild-unshare-diagnostic
EXTRA_ARGS=()
for deb in "${PREDECESSOR_DEBS[@]}"; do EXTRA_ARGS+=(--extra-package="${deb}"); done
set +e
SBUILD_CONFIG="${CONFIG}" sbuild --verbose --chroot-mode=unshare --dist=resolute \
  --arch=amd64 --arch-all --no-run-lintian --no-run-autopkgtest --no-run-piuparts \
  "${EXTRA_ARGS[@]}" --build-dir="${OUT}" "${DSC}" |& tee "${SBUILD_LOG}"
SBUILD_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${SBUILD_RC}" > "${EVIDENCE}/sbuild-exit-code.txt"

STAGE=sbuild-sentinel-validation
(( SBUILD_RC != 0 ))
[[ -f "${EVIDENCE}/hook-complete" && -s "${RESULT}" ]]
python3 - "${RESULT}" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
if r.get("diagnostic_result")!="DIAG_COMPLETE": raise SystemExit("Round23 hook did not complete")
if r.get("package_attempted") is not False: raise SystemExit("Round23 unexpectedly reports package attempt")
PY
if grep -Fq "Command: dpkg-buildpackage" "${SBUILD_LOG}"; then echo "dpkg-buildpackage was reached; Round23 invalid" >&2; exit 83; fi
if find "${OUT}" -type f \( -name '*.deb' -o -name '*.changes' -o -name '*.buildinfo' \) -print -quit | grep -q .; then echo "package artifacts were produced; Round23 invalid" >&2; exit 84; fi
printf '%s\n' "sbuild stopped by Round23 hook before dpkg-buildpackage" > "${EVIDENCE}/package-build-prevention.txt"
DIAG_RESULT=DIAG_COMPLETE
STAGE=complete
exit 0
