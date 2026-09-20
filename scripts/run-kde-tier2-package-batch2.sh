#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="${1:-}"
[[ -n "${NODE}" ]] || { echo "Usage: $0 <node>" >&2; exit 2; }

CAMPAIGN="${ROOT}/manifests/kde-tier2-package-campaign-batch2.json"
: "${MATERIALIZATION_ARTIFACT_DIR:?missing materialization artifact}"
: "${ECM_ARTIFACT_DIR:?missing ECM artifact}"
: "${PREDECESSOR_ARTIFACT_DIR:?missing predecessor artifact}"
: "${ROOTFS_ARTIFACT_DIR:?missing rootfs artifact}"

WORK="${ROOT}/.work/kde-tier2-package-batch2/${NODE}"
OUT="${WORK}/out"
EVIDENCE="${ROOT}/evidence/kde-tier2-package-batch2/${NODE}"
RESULT="${EVIDENCE}/result.json"
STATE=INFRA
STAGE=initialization
PACKAGE_ATTEMPTED=false
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}" "${OUT}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result(){
  local rc=$? finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT}" "${NODE}" "${STATE}" "${rc}" "${STAGE}" "${PACKAGE_ATTEMPTED}" "${STARTED_AT}" "${finished}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); data={}
if p.exists() and p.stat().st_size: data=json.loads(p.read_text())
data.update({
 "schema":1,"node":sys.argv[2],"state":sys.argv[3],"exit_code":int(sys.argv[4]),"stage":sys.argv[5],
 "package_attempted":sys.argv[6].lower()=="true","started_at":sys.argv[7],"finished_at":sys.argv[8],
 "claim":"hosted-clean-package-preflight","authoritative":False
})
p.write_text(json.dumps(data,indent=2)+"\n")
PY
}
trap write_result EXIT

STAGE=campaign-and-input-validation
python3 - "${CAMPAIGN}" "${NODE}" "${MATERIALIZATION_ARTIFACT_DIR}" "${ECM_ARTIFACT_DIR}" "${PREDECESSOR_ARTIFACT_DIR}" "${EVIDENCE}" <<'PY'
import hashlib,json,shlex,subprocess,sys
from pathlib import Path
campaign_path,node_id,mat_dir,ecm_dir,pred_dir,evidence_dir=sys.argv[1:]
c=json.load(open(campaign_path)); n=c["nodes"][node_id]
if n["state"] not in {"prepared-pending-build","remediation-pending-build"}:
    raise SystemExit(f"{node_id}: not runnable, state={n['state']}")
out=Path(evidence_dir)
mat=Path(mat_dir); ecm=Path(ecm_dir); pred=Path(pred_dir)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def one(pattern,root):
    found=list(root.rglob(pattern))
    if len(found)!=1: raise SystemExit(f"{node_id}: expected one {pattern} under {root}, got {len(found)}")
    return found[0]
def deb_meta(path):
    pkg=subprocess.check_output(["dpkg-deb","-f",str(path),"Package"],text=True).strip()
    ver=subprocess.check_output(["dpkg-deb","-f",str(path),"Version"],text=True).strip()
    return pkg,ver

m=n["materialization"]
mat_result=one("result.json",mat)
mr=json.loads(mat_result.read_text())
if mr.get("result")!="PASS" or mr.get("package_attempted") is not False:
    raise SystemExit(f"{node_id}: materialization result is not retained PASS")
if mr.get("tree_sha256")!=m["tree_sha256"] or mr.get("debian_tree_sha256")!=m["debian_tree_sha256"]:
    raise SystemExit(f"{node_id}: materialization content hash drift")
source_pkg=n["source_package"]; version=n["package_version"]; upstream=n["upstream_version"]
dsc=one(f"{source_pkg}_{version}.dsc",mat)
debtar=one(f"{source_pkg}_{version}.debian.tar.xz",mat)
orig=one(f"{source_pkg}_{upstream}.orig.tar.xz",mat)
for p,key in ((dsc,"dsc_sha256"),(debtar,"debian_tar_sha256"),(orig,"orig_tar_sha256")):
    if sha(p)!=m[key]: raise SystemExit(f"{node_id}: materialized {p.name} SHA mismatch")

ecm_cfg=c["shared_predecessors"]["extra_cmake_modules"]
ecm_deb=one("*.deb",ecm)
pkg,ver=deb_meta(ecm_deb)
if pkg!="extra-cmake-modules" or ver!=ecm_cfg["version"] or sha(ecm_deb)!=ecm_cfg["debs"][pkg]:
    raise SystemExit(f"{node_id}: ECM retained artifact mismatch")

pred_cfg=n["predecessor"]
actual={}
paths={}
for p in pred.rglob("*.deb"):
    pkg,ver=deb_meta(p)
    if pkg in actual: raise SystemExit(f"{node_id}: duplicate predecessor binary {pkg}")
    actual[pkg]=sha(p); paths[pkg]=str(p)
    if ver!=pred_cfg["version"]: raise SystemExit(f"{node_id}: predecessor {pkg} version {ver} != {pred_cfg['version']}")
if actual!=pred_cfg["debs"]:
    raise SystemExit(f"{node_id}: predecessor .deb set/hash mismatch\nexpected={pred_cfg['debs']}\nactual={actual}")
if pred_cfg["dev_package"] not in actual:
    raise SystemExit(f"{node_id}: predecessor dev package absent")

env={
 "SOURCE_PACKAGE":source_pkg,"PACKAGE_VERSION":version,"UPSTREAM_VERSION":upstream,
 "DSC":str(dsc),"ORIG":str(orig),"DEBIAN_TAR":str(debtar),"ECM_DEB":str(ecm_deb),
 "PREDECESSOR_VERSION":pred_cfg["version"],"PREDECESSOR_DEV_PACKAGE":pred_cfg["dev_package"],
 "RUNTIME_PACKAGE":n["runtime_package"],"DEV_PACKAGE":n["dev_package"],"SONAME":n["soname"],
 "CMAKE_PACKAGE":n["cmake_package"],"CMAKE_TARGET":n["cmake_target"],
 "PYTHON_MODULE":n.get("python_module") or "","QML_PACKAGE":n.get("qml_package") or "",
}
(out/"input-env.sh").write_text("\n".join(f"{k}={shlex.quote(v)}" for k,v in env.items())+"\n")
(out/"predecessor-debs.txt").write_text("\n".join(paths[p] for p in sorted(paths))+"\n")
(out/"expected-binaries.txt").write_text("\n".join(n["expected_binary_packages"])+"\n")
(out/"retained-inputs.json").write_text(json.dumps({
 "materialization":m,"ecm":ecm_cfg,"predecessor":pred_cfg,
},indent=2)+"\n")
PY
source "${EVIDENCE}/input-env.sh"
mapfile -t PREDECESSOR_DEBS < "${EVIDENCE}/predecessor-debs.txt"
mapfile -t EXPECTED_BINARIES < "${EVIDENCE}/expected-binaries.txt"

STAGE=host-validation
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends   binutils cmake devscripts dpkg-dev g++ lintian ninja-build pkg-config python3 sbuild uidmap ubuntu-keyring xz-utils
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true
{ cat /etc/os-release; uname -a; sbuild --version; lintian --version; } > "${EVIDENCE}/host.txt"

CHROOT_TARBALL="$(find "${ROOTFS_ARTIFACT_DIR}" -type f -name resolute-amd64.tar -print -quit)"
ROOTFS_SHA_FILE="$(find "${ROOTFS_ARTIFACT_DIR}" -type f -name rootfs.sha256 -print -quit)"
[[ -n "${CHROOT_TARBALL}" && -s "${CHROOT_TARBALL}" && -n "${ROOTFS_SHA_FILE}" ]]
expected_rootfs="$(awk '{print $1}' "${ROOTFS_SHA_FILE}")"
actual_rootfs="$(sha256sum "${CHROOT_TARBALL}" | awk '{print $1}')"
[[ "${expected_rootfs}" == "${actual_rootfs}" ]]
printf '%s\n' "${actual_rootfs}" > "${EVIDENCE}/rootfs.sha256"

STAGE=sbuild
PACKAGE_ATTEMPTED=true
STATE=FAIL
EXTRA_ARGS=(--extra-package="${ECM_DEB}")
for deb in "${PREDECESSOR_DEBS[@]}"; do EXTRA_ARGS+=(--extra-package="${deb}"); done
sbuild --verbose --chroot-mode=unshare --chroot="@{CHROOT_TARBALL}" --dist=resolute --arch=amd64 --arch-all   "${EXTRA_ARGS[@]}" --build-dir="${OUT}" "${DSC}" |& tee "${EVIDENCE}/sbuild.log"

grep -Eq '100% tests passed, 0 tests failed out of [1-9][0-9]*' "${EVIDENCE}/sbuild.log" || {
  echo "No positive non-zero CTest PASS summary found" >&2; exit 1;
}

mapfile -t DEBS < <(find "${OUT}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
(( ${#DEBS[@]} > 0 && ${#CHANGES[@]} == 1 && ${#BUILDINFO[@]} == 1 ))

STAGE=artifact-contract
python3 - "${OUT}" "${CAMPAIGN}" "${NODE}" "${EVIDENCE}" <<'PY'
import json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]); c=json.load(open(sys.argv[2])); node=sys.argv[3]; ev=Path(sys.argv[4])
n=c["nodes"][node]; debs={}
for p in out.glob("*.deb"):
    pkg=subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()
    ver=subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip()
    if pkg in debs: raise SystemExit(f"duplicate binary package {pkg}")
    if ver!=n["package_version"]: raise SystemExit(f"{pkg}: version {ver} != {n['package_version']}")
    debs[pkg]=str(p)
expected=set(n["expected_binary_packages"])
if set(debs)!=expected:
    raise SystemExit(f"{node}: binary set mismatch expected={sorted(expected)} actual={sorted(debs)}")
(ev/"built-debs.json").write_text(json.dumps(debs,indent=2)+"\n")
PY

grep -F "extra-cmake-modules (= ${campaign.shared_predecessors?.extra_cmake_modules?.version || ''})" /dev/null >/dev/null 2>&1 || true
ECM_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["shared_predecessors"]["extra_cmake_modules"]["version"])' "${CAMPAIGN}")"
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE}/ecm-buildinfo-proof.txt"
grep -F "${PREDECESSOR_DEV_PACKAGE} (= ${PREDECESSOR_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE}/predecessor-buildinfo-proof.txt"

STAGE=abi-contract
RUNTIME_DEB="$(python3 - "${EVIDENCE}/built-debs.json" "${RUNTIME_PACKAGE}" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))[sys.argv[2]])
PY
)"
RUNTIME_ROOT="${WORK}/runtime-root"; mkdir -p "${RUNTIME_ROOT}"; dpkg-deb -x "${RUNTIME_DEB}" "${RUNTIME_ROOT}"
python3 - "${RUNTIME_ROOT}" "${SONAME}" "${EVIDENCE}" <<'PY'
import re,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]); soname=sys.argv[2]; out=Path(sys.argv[3])
match=None
for p in root.rglob("*.so*"):
    if not p.is_file(): continue
    r=subprocess.run(["readelf","-d",str(p)],text=True,capture_output=True)
    if r.returncode==0 and f"Library soname: [{soname}]" in r.stdout:
        match=p; (out/"readelf-dynamic.txt").write_text(r.stdout); break
if match is None: raise SystemExit(f"SONAME {soname} not found in runtime package")
nm=subprocess.check_output(["nm","-D","--defined-only",str(match)],text=True)
exports=[x for x in nm.splitlines() if x.strip()]
if not exports: raise SystemExit("runtime library exports are empty")
(out/"abi-library.txt").write_text(str(match)+"\n")
(out/"abi-exports.txt").write_text("\n".join(exports)+"\n")
(out/"abi-export-count.txt").write_text(str(len(exports))+"\n")
PY

STAGE=artifact-capture
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG}" "${DEBIAN_TAR}" > "${EVIDENCE}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG}" "${DEBIAN_TAR}" "${EVIDENCE}/"

STAGE=lintian-source-binary
lintian --fail-on error "${DSC}" "${CHANGES[0]}" |& tee "${EVIDENCE}/lintian-source-binary.log"

STAGE=consumer-runtime-closure
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends   "${ECM_DEB}" "${PREDECESSOR_DEBS[@]}" "${DEBS[@]}" |& tee "${EVIDENCE}/consumer-runtime-install.log"
sudo apt-get check |& tee "${EVIDENCE}/consumer-runtime-check.log"
[[ "$(dpkg-query -W -f='${Version}' "${PREDECESSOR_DEV_PACKAGE}")" == "${PREDECESSOR_VERSION}" ]]
[[ "$(dpkg-query -W -f='${Version}' "${RUNTIME_PACKAGE}")" == "${PACKAGE_VERSION}" ]]

STAGE=consumer-smoke
CONSUMER="${WORK}/consumer"; mkdir -p "${CONSUMER}"
cat > "${CONSUMER}/main.cpp" <<'CPP'
int main() { return 0; }
CPP
cat > "${CONSUMER}/CMakeLists.txt" <<EOF
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXTier2Consumer LANGUAGES CXX)
find_package(${CMAKE_PACKAGE} 6.30 REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE ${CMAKE_TARGET})
EOF
cmake -S "${CONSUMER}" -B "${CONSUMER}/build" -GNinja -DCMAKE_BUILD_TYPE=Release |& tee "${EVIDENCE}/consumer-configure.log"
cmake --build "${CONSUMER}/build" --verbose |& tee "${EVIDENCE}/consumer-build.log"
"${CONSUMER}/build/consumer" |& tee "${EVIDENCE}/consumer-run.log"

if [[ -n "${PYTHON_MODULE}" ]]; then
  STAGE=python-import-smoke
  python3 -c "import ${PYTHON_MODULE}; print('python-import=PASS module=${PYTHON_MODULE}')" | tee "${EVIDENCE}/python-import.log"
fi

if [[ -n "${QML_PACKAGE}" ]]; then
  STAGE=qml-payload-smoke
  QML_DEB="$(python3 - "${EVIDENCE}/built-debs.json" "${QML_PACKAGE}" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))[sys.argv[2]])
PY
)"
  QML_ROOT="${WORK}/qml-root"; mkdir -p "${QML_ROOT}"; dpkg-deb -x "${QML_DEB}" "${QML_ROOT}"
  find "${QML_ROOT}" -type f -name qmldir -print | tee "${EVIDENCE}/qml-qmldir.txt"
  test -s "${EVIDENCE}/qml-qmldir.txt"
fi

STAGE=pass-evidence
python3 - "${RESULT}" "${EVIDENCE}" "${NODE}" "${PACKAGE_VERSION}" "${SONAME}" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
result_path=Path(sys.argv[1]); ev=Path(sys.argv[2]); node=sys.argv[3]
data={}
if result_path.exists() and result_path.stat().st_size: data=json.loads(result_path.read_text())
tests=re.search(r"100% tests passed, 0 tests failed out of ([1-9][0-9]*)",(ev/"sbuild.log").read_text())
data.update({
 "node":node,"package_version":sys.argv[4],"abi_soname":sys.argv[5],
 "tests":f"{tests.group(1)}/{tests.group(1)} PASS" if tests else "PASS",
 "abi_export_count":int((ev/"abi-export-count.txt").read_text().strip()),
 "lintian":"PASS-errors","apt_check":"PASS","consumer_smoke":"PASS",
})
if (ev/"python-import.log").exists(): data["python_import"]="PASS"
if (ev/"qml-qmldir.txt").exists(): data["qml_payload_smoke"]="PASS"
result_path.write_text(json.dumps(data,indent=2)+"\n")
PY
STATE=PASS
STAGE=complete
echo "KDE Tier 2 Batch 2 ${NODE}: PASS"
