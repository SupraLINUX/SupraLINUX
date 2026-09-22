#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="${1:-}"
[[ "${NODE}" == "kded" ]] || { echo "Usage: $0 kded" >&2; exit 2; }
CAMPAIGN="${ROOT}/manifests/kde-tier3-support-build-level1.json"
: "${MATERIALIZATION_ARTIFACT_DIR:?missing materialization artifact}"
: "${RETAINED_INPUTS_DIR:?missing retained inputs}"
: "${ROOTFS_ARTIFACT_DIR:?missing rootfs artifact}"
WORK="${ROOT}/.work/kde-tier3-support-build-level1/${NODE}"
OUT="${WORK}/out"
EVIDENCE="${ROOT}/evidence/kde-tier3-support-build-level1/${NODE}"
RESULT="${EVIDENCE}/result.json"
STATE=INFRA
STAGE=initialization
PACKAGE_ATTEMPTED=false
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rm -rf "${WORK}" "${EVIDENCE}"; mkdir -p "${WORK}" "${OUT}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1
write_result(){
  local rc=$? finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT}" "${NODE}" "${STATE}" "${rc}" "${STAGE}" "${PACKAGE_ATTEMPTED}" "${STARTED_AT}" "${finished}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); d={}
if p.exists() and p.stat().st_size:
    try: d=json.loads(p.read_text())
    except Exception: d={}
d.update({"schema":1,"node":sys.argv[2],"state":sys.argv[3],"exit_code":int(sys.argv[4]),"stage":sys.argv[5],"package_attempted":sys.argv[6].lower()=="true","started_at":sys.argv[7],"finished_at":sys.argv[8],"claim":"hosted-clean-package-preflight","authoritative":False})
p.write_text(json.dumps(d,indent=2)+"\n")
PY
}
trap write_result EXIT

STAGE="campaign-and-input-validation"
python3 - "${CAMPAIGN}" "${MATERIALIZATION_ARTIFACT_DIR}" "${RETAINED_INPUTS_DIR}" "${EVIDENCE}" <<'PY'
import hashlib,json,shlex,subprocess,sys
from pathlib import Path
campaign,mat_dir,ret_dir,evdir=sys.argv[1:]
c=json.load(open(campaign)); n=c["nodes"]["kded"]; mat=Path(mat_dir); ret=Path(ret_dir); ev=Path(evdir)
if n["state"] not in {"prepared-pending-build","remediation-pending-build"}: raise SystemExit(f"kded not runnable: {n['state']}")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(pattern,root):
    found=list(Path(root).rglob(pattern))
    if len(found)!=1: raise SystemExit(f"expected one {pattern} under {root}, got {len(found)}")
    return found[0]
def meta(p):
    return subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip(), subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip()
def validate(root,cfg,label):
    got={}; paths={}
    for p in Path(root).rglob("*.deb"):
        pkg,ver=meta(p)
        if pkg in got: raise SystemExit(f"{label}: duplicate {pkg}")
        if ver!=cfg["version"]: raise SystemExit(f"{label}: {pkg} version {ver} != {cfg['version']}")
        got[pkg]=sha(p); paths[pkg]=str(p)
    if got!=cfg["debs"]: raise SystemExit(f"{label}: .deb set/hash mismatch")
    return paths
mr=json.loads(one("result.json",mat).read_text()); m=n["materialization"]
if mr.get("result")!="PASS" or mr.get("package_attempted") is not False: raise SystemExit("KDED materialization is not retained PASS")
if mr.get("package_version")!=n["package_version"]: raise SystemExit("KDED materialized version drift")
for key in ("dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
    if mr.get(key)!=m[key]: raise SystemExit(f"KDED materialization {key} drift")
dsc=one("*.dsc",mat); debtar=one("*.debian.tar.*",mat); orig=one("*.orig.tar.*",mat)
for p,key in ((dsc,"dsc_sha256"),(debtar,"debian_tar_sha256"),(orig,"orig_tar_sha256")):
    if sha(p)!=m[key]: raise SystemExit(f"{p.name}: SHA mismatch")

all_paths=[]; direct=[]; closure=[]
ecm_cfg=c["shared_predecessors"]["extra_cmake_modules"]; ecm=validate(ret/"extra_cmake_modules",ecm_cfg,"extra_cmake_modules")["extra-cmake-modules"]
seen=set()
def consume(section,pred,contracts):
    cfg=c[section][pred]; paths=validate(ret/pred,cfg,pred)
    overlap=seen.intersection(paths)
    if overlap: raise SystemExit(f"duplicate package names across retained inputs: {sorted(overlap)}")
    seen.update(paths); all_paths.extend(paths[p] for p in sorted(paths))
    if cfg["dev_package"] not in paths: raise SystemExit(f"{pred}: dev package absent")
    contracts.append((pred,cfg["dev_package"],cfg["version"]))
for pred in n["direct_predecessors"]: consume("retained_predecessors",pred,direct)
for pred in n["package_dependency_closure"]: consume("package_dependency_closure",pred,closure)
env={"SOURCE_PACKAGE":n["source_package"],"PACKAGE_VERSION":n["package_version"],"UPSTREAM_VERSION":n["upstream_version"],"DSC":str(dsc),"ORIG":str(orig),"DEBIAN_TAR":str(debtar),"ECM_DEB":ecm,"CMAKE_PACKAGE":n["cmake_package"],"CMAKE_VARIABLE":n["cmake_variable"]}
(ev/"input-env.sh").write_text("\n".join(f"{k}={shlex.quote(v)}" for k,v in env.items())+"\n")
(ev/"retained-debs.txt").write_text("\n".join(all_paths)+"\n")
(ev/"direct-contracts.txt").write_text("\n".join("|".join(x) for x in direct)+"\n")
(ev/"closure-contracts.txt").write_text("\n".join("|".join(x) for x in closure)+"\n")
(ev/"expected-binaries.txt").write_text("\n".join(n["expected_binary_packages"])+"\n")
PY

source "${EVIDENCE}/input-env.sh"
mapfile -t RETAINED_DEBS < "${EVIDENCE}/retained-debs.txt"
STAGE="host-validation"
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends binutils cmake devscripts dpkg-dev g++ lintian ninja-build pkg-config sbuild uidmap ubuntu-keyring xz-utils
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true
{ cat /etc/os-release; uname -a; sbuild --version; lintian --version; } > "${EVIDENCE}/host.txt"
CHROOT_TARBALL="$(find "${ROOTFS_ARTIFACT_DIR}" -type f -name resolute-amd64.tar -print -quit)"
ROOTFS_SHA_FILE="$(find "${ROOTFS_ARTIFACT_DIR}" -type f -name rootfs.sha256 -print -quit)"
[[ -n "${CHROOT_TARBALL}" && -s "${CHROOT_TARBALL}" && -n "${ROOTFS_SHA_FILE}" ]]
expected_rootfs="$(awk '{print $1}' "${ROOTFS_SHA_FILE}")"; actual_rootfs="$(sha256sum "${CHROOT_TARBALL}" | awk '{print $1}')"; [[ "${expected_rootfs}" == "${actual_rootfs}" ]]
printf '%s\n' "${actual_rootfs}" > "${EVIDENCE}/rootfs.sha256"
mkdir -p "${HOME}/.cache/sbuild"; ln -sfn "${CHROOT_TARBALL}" "${HOME}/.cache/sbuild/resolute-amd64.tar"

STAGE="sbuild"
PACKAGE_ATTEMPTED=true; STATE=FAIL
EXTRA_ARGS=(--extra-package="${ECM_DEB}")
for deb in "${RETAINED_DEBS[@]}"; do EXTRA_ARGS+=(--extra-package="${deb}"); done
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --arch-all "${EXTRA_ARGS[@]}" --build-dir="${OUT}" "${DSC}" |& tee "${EVIDENCE}/sbuild.log"
test_summary="$(grep -Eo '100% tests passed, 0 tests failed out of [1-9][0-9]*' "${EVIDENCE}/sbuild.log" | tail -1 || true)"
[[ -n "${test_summary}" ]] || { echo "No positive non-zero upstream CTest PASS summary found" >&2; exit 1; }
printf '%s\n' "${test_summary}" > "${EVIDENCE}/tests-summary.txt"
mapfile -t DEBS < <(find "${OUT}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
(( ${#DEBS[@]} > 0 && ${#CHANGES[@]} == 1 && ${#BUILDINFO[@]} == 1 ))

STAGE="artifact-contract"
python3 - "${OUT}" "${CAMPAIGN}" "${EVIDENCE}" <<'PY'
import json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]); c=json.load(open(sys.argv[2])); ev=Path(sys.argv[3]); n=c["nodes"]["kded"]; got={}
for p in out.glob("*.deb"):
    pkg=subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()
    ver=subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip()
    if pkg in got: raise SystemExit(f"duplicate binary {pkg}")
    if ver!=n["package_version"]: raise SystemExit(f"{pkg}: version {ver} != {n['package_version']}")
    got[pkg]=str(p)
if set(got)!=set(n["expected_binary_packages"]): raise SystemExit(f"KDED binary set mismatch expected={n['expected_binary_packages']} actual={sorted(got)}")
(ev/"built-debs.json").write_text(json.dumps(got,indent=2)+"\n")
PY
ECM_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["shared_predecessors"]["extra_cmake_modules"]["version"])' "${CAMPAIGN}")"
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE}/ecm-buildinfo-proof.txt"
: > "${EVIDENCE}/direct-buildinfo-proof.txt"
while IFS='|' read -r pred dev ver; do [[ -z "${pred}" ]] && continue; grep -F "${dev} (= ${ver})" "${BUILDINFO[0]}" >> "${EVIDENCE}/direct-buildinfo-proof.txt"; done < "${EVIDENCE}/direct-contracts.txt"
: > "${EVIDENCE}/closure-buildinfo-proof.txt"
while IFS='|' read -r pred dev ver; do [[ -z "${pred}" ]] && continue; grep -F "${dev} (= ${ver})" "${BUILDINFO[0]}" >> "${EVIDENCE}/closure-buildinfo-proof.txt"; done < "${EVIDENCE}/closure-contracts.txt"

STAGE="payload-contract"
python3 - "${EVIDENCE}/built-debs.json" "${WORK}" "${EVIDENCE}" <<'PY'
import json,subprocess,sys,shutil,os
from pathlib import Path
built=json.load(open(sys.argv[1])); work=Path(sys.argv[2]); ev=Path(sys.argv[3])
def extract(pkg,label):
    root=work/label
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True); subprocess.check_call(["dpkg-deb","-x",built[pkg],str(root)]); return root
runtime=extract("kded6","kded-runtime")
required=[
 "usr/bin/kded6",
 "usr/lib/systemd/user/plasma-kded6.service",
 "usr/share/applications/org.kde.kded6.desktop",
 "usr/share/dbus-1/interfaces/org.kde.kded6.xml",
 "usr/share/dbus-1/services/org.kde.kded6.service",
]
for rel in required:
    if not (runtime/rel).is_file(): raise SystemExit(f"KDED payload missing: {rel}")
if not next(runtime.rglob("kded6.8.gz"),None): raise SystemExit("KDED compressed manpage missing; KDocTools documentation profile was not produced")
if not next(runtime.rglob("kded.categories"),None): raise SystemExit("KDED logging categories missing")
elf=runtime/"usr/bin/kded6"
r=subprocess.run(["readelf","-h",str(elf)],text=True,capture_output=True)
if r.returncode!=0 or "ELF" not in r.stdout: raise SystemExit("kded6 is not a valid ELF executable")
dev=extract("kded6-dev","kded-dev")
configs=list(dev.rglob("KF6KDEDConfig.cmake"))
versions=list(dev.rglob("KF6KDEDConfigVersion.cmake"))
if len(configs)!=1 or len(versions)!=1: raise SystemExit("KF6KDED CMake config payload incomplete")
if list(runtime.rglob("*.so*")) or list(dev.rglob("*.so*")): raise SystemExit("KDED unexpectedly ships a library; upstream contract says no library")
(ev/"readelf-kded6.txt").write_text(r.stdout)
(ev/"payload-summary.txt").write_text("kded6-elf=PASS\nsystemd=PASS\ndbus=PASS\nmanpage=PASS\ncmake-config=PASS\nno-library=PASS\n")
PY

STAGE="artifact-capture"
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG}" "${DEBIAN_TAR}" > "${EVIDENCE}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG}" "${DEBIAN_TAR}" "${EVIDENCE}/"
STAGE="lintian-source-binary"
lintian --fail-on error "${DSC}" "${CHANGES[0]}" |& tee "${EVIDENCE}/lintian-source-binary.log"

STAGE="consumer-runtime-closure"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${ECM_DEB}" "${RETAINED_DEBS[@]}" "${DEBS[@]}" |& tee "${EVIDENCE}/consumer-runtime-install.log"
sudo apt-get check |& tee "${EVIDENCE}/consumer-runtime-check.log"
[[ "$(dpkg-query -W -f='${Version}' kded6)" == "${PACKAGE_VERSION}" ]]
while IFS='|' read -r _pred dev ver; do [[ -z "${dev}" ]] && continue; [[ "$(dpkg-query -W -f='${Version}' "${dev}")" == "${ver}" ]]; done < "${EVIDENCE}/direct-contracts.txt"
while IFS='|' read -r _pred dev ver; do [[ -z "${dev}" ]] && continue; [[ "$(dpkg-query -W -f='${Version}' "${dev}")" == "${ver}" ]]; done < "${EVIDENCE}/closure-contracts.txt"

STAGE="executable-smoke"
command -v kded6 | tee "${EVIDENCE}/kded6-path.txt"
QT_QPA_PLATFORM=offscreen kded6 --version |& tee "${EVIDENCE}/kded6-version.txt"

STAGE="cmake-consumer"
CONSUMER="${WORK}/consumer"; mkdir -p "${CONSUMER}"
cat > "${CONSUMER}/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXKDEDConsumer NONE)
find_package(KF6KDED 6.30 REQUIRED)
if(NOT DEFINED KDED_DBUS_INTERFACE)
  message(FATAL_ERROR "KDED_DBUS_INTERFACE missing")
endif()
if(NOT EXISTS "${KDED_DBUS_INTERFACE}")
  message(FATAL_ERROR "KDED DBus interface missing: ${KDED_DBUS_INTERFACE}")
endif()
add_custom_target(consumer ALL COMMAND "${CMAKE_COMMAND}" -E echo "KDED_DBUS_INTERFACE=${KDED_DBUS_INTERFACE}")
EOF
cmake -S "${CONSUMER}" -B "${CONSUMER}/build" -GNinja |& tee "${EVIDENCE}/consumer-configure.log"
cmake --build "${CONSUMER}/build" --verbose |& tee "${EVIDENCE}/consumer-build.log"

STAGE="pass-evidence"
python3 - "${RESULT}" "${EVIDENCE}" "${PACKAGE_VERSION}" "${CAMPAIGN}" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
result=Path(sys.argv[1]); ev=Path(sys.argv[2]); version=sys.argv[3]; c=json.load(open(sys.argv[4]))
d=json.loads(result.read_text()) if result.exists() and result.stat().st_size else {}
tests=re.search(r"100% tests passed, 0 tests failed out of ([1-9][0-9]*)",(ev/"sbuild.log").read_text())
files={}
for p in ev.iterdir():
    if p.is_file() and p.suffix in {".deb",".ddeb",".changes",".buildinfo",".dsc",".xz"}: files[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
direct={}; closure={}
for name,target in (("direct-contracts.txt",direct),("closure-contracts.txt",closure)):
    for line in (ev/name).read_text().splitlines():
        if line.strip():
            pred,dev,ver=line.split("|"); target[pred]={"dev_package":dev,"version":ver}
d.update({
 "result":"PASS","state":"PASS","node":"kded","package_version":version,"package_attempted":True,"package_state_effect":"PASS","downstream_eligible":True,
 "tests":f"{tests.group(1)}/{tests.group(1)} PASS","lintian":"PASS-errors","apt_check":"PASS","executable_contract":"PASS","cmake_consumer":"PASS","payload_contract":"PASS",
 "ecm_predecessor":c["shared_predecessors"]["extra_cmake_modules"]["version"],"direct_predecessors":direct,"package_dependency_closure":closure,"files":files,
})
result.write_text(json.dumps(d,indent=2)+"\n")
PY
STATE=PASS; STAGE=complete
echo "KDE Tier 3 support build level 1 kded: PASS"
