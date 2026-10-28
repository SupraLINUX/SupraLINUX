#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="${1:-}"
[[ -n "${NODE}" ]] || { echo "Usage: $0 <node>" >&2; exit 2; }

CAMPAIGN="${ROOT}/manifests/kde-tier3-support-build-level0.json"
: "${MATERIALIZATION_ARTIFACT_DIR:?missing materialization artifact}"
: "${RETAINED_INPUTS_DIR:?missing retained inputs}"
: "${ROOTFS_ARTIFACT_DIR:?missing rootfs artifact}"

WORK="${ROOT}/.work/kde-tier3-support-build-level0/${NODE}"
OUT="${WORK}/out"
EVIDENCE="${ROOT}/evidence/kde-tier3-support-build-level0/${NODE}"
RESULT="${EVIDENCE}/result.json"
STATE=INFRA
STAGE=initialization
PACKAGE_ATTEMPTED=false
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}" "${OUT}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result() {
  local rc=$? finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT}" "${NODE}" "${STATE}" "${rc}" "${STAGE}" "${PACKAGE_ATTEMPTED}" "${STARTED_AT}" "${finished}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); d={}
if p.exists() and p.stat().st_size:
    try: d=json.loads(p.read_text())
    except Exception: d={}
d.update({
 "schema":1,"node":sys.argv[2],"state":sys.argv[3],"exit_code":int(sys.argv[4]),"stage":sys.argv[5],
 "package_attempted":sys.argv[6].lower()=="true","started_at":sys.argv[7],"finished_at":sys.argv[8],
 "claim":"hosted-clean-package-preflight","authoritative":False,
})
p.write_text(json.dumps(d,indent=2)+"\n")
PY
}
trap write_result EXIT

STAGE="campaign-and-input-validation"
python3 - "${CAMPAIGN}" "${NODE}" "${MATERIALIZATION_ARTIFACT_DIR}" "${RETAINED_INPUTS_DIR}" "${EVIDENCE}" <<'PY'
import hashlib,json,shlex,subprocess,sys
from pathlib import Path
campaign_path,node_id,mat_dir,retained_dir,evidence_dir=sys.argv[1:]
c=json.load(open(campaign_path)); n=c["nodes"].get(node_id)
if not n: raise SystemExit(f"unknown node {node_id}")
if n["state"] not in {"prepared-pending-build","remediation-pending-build"}:
    raise SystemExit(f"{node_id}: not runnable, state={n['state']}")
mat=Path(mat_dir); retained=Path(retained_dir); out=Path(evidence_dir)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(pattern,root):
    found=list(Path(root).rglob(pattern))
    if len(found)!=1: raise SystemExit(f"{node_id}: expected one {pattern}, got {len(found)}")
    return found[0]
def debmeta(p):
    return (subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip(),
            subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip())
def validated_debs(root,cfg,label):
    got={}; paths={}
    for p in Path(root).rglob("*.deb"):
        pkg,ver=debmeta(p)
        if pkg in got: raise SystemExit(f"{label}: duplicate {pkg}")
        if ver!=cfg["version"]: raise SystemExit(f"{label}: {pkg} version {ver} != {cfg['version']}")
        got[pkg]=sha(p); paths[pkg]=str(p)
    if got!=cfg["debs"]: raise SystemExit(f"{label}: .deb hash/set mismatch")
    return paths

mr=json.loads(one("result.json",mat).read_text())
m=n["materialization"]
if mr.get("result")!="PASS" or mr.get("package_attempted") is not False:
    raise SystemExit(f"{node_id}: materialization is not retained PASS")
if mr.get("package_version")!=n["package_version"]:
    raise SystemExit(f"{node_id}: materialized package version drift")
for key in ("dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
    if mr.get(key)!=m[key]: raise SystemExit(f"{node_id}: materialization {key} drift")
dsc=one("*.dsc",mat); debtar=one("*.debian.tar.*",mat); orig=one("*.orig.tar.*",mat)
for p,key in ((dsc,"dsc_sha256"),(debtar,"debian_tar_sha256"),(orig,"orig_tar_sha256")):
    if sha(p)!=m[key]: raise SystemExit(f"{node_id}: {p.name} SHA mismatch")

ecm_cfg=c["shared_predecessors"]["extra_cmake_modules"]
ecm_paths=validated_debs(Path(retained_dir)/"extra_cmake_modules",ecm_cfg,"extra_cmake_modules")
ecm_deb=ecm_paths["extra-cmake-modules"]
all_debs=[]; contracts=[]
for pred in n["predecessors"]:
    cfg=c["retained_predecessors"][pred]
    paths=validated_debs(Path(retained_dir)/pred,cfg,pred)
    if cfg["dev_package"] not in paths: raise SystemExit(f"{pred}: dev package absent")
    all_debs.extend(paths[p] for p in sorted(paths))
    contracts.append((pred,cfg["dev_package"],cfg["version"]))
env={
 "SOURCE_PACKAGE":n["source_package"],"PACKAGE_VERSION":n["package_version"],"UPSTREAM_VERSION":n["upstream_version"],
 "DSC":str(dsc),"ORIG":str(orig),"DEBIAN_TAR":str(debtar),"ECM_DEB":ecm_deb,
 "RUNTIME_PACKAGE":n["runtime_package"],"DEV_PACKAGE":n["dev_package"],"SONAME":n["soname"],
 "CMAKE_PACKAGE":n["cmake_package"],"CMAKE_TARGET":n["cmake_target"],"PAYLOAD_CONTRACT":n["payload_contract"],
}
(out/"input-env.sh").write_text("\n".join(f"{k}={shlex.quote(v)}" for k,v in env.items())+"\n")
(out/"predecessor-debs.txt").write_text("\n".join(all_debs)+"\n")
(out/"predecessor-contracts.txt").write_text("\n".join("|".join(x) for x in contracts)+"\n")
(out/"expected-binaries.txt").write_text("\n".join(n["expected_binary_packages"])+"\n")
PY

source "${EVIDENCE}/input-env.sh"
mapfile -t PREDECESSOR_DEBS < "${EVIDENCE}/predecessor-debs.txt"

STAGE="host-validation"
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
mkdir -p "${HOME}/.cache/sbuild"
ln -sfn "${CHROOT_TARBALL}" "${HOME}/.cache/sbuild/resolute-amd64.tar"

STAGE="sbuild"
PACKAGE_ATTEMPTED=true
STATE=FAIL
EXTRA_ARGS=(--extra-package="${ECM_DEB}")
for deb in "${PREDECESSOR_DEBS[@]}"; do EXTRA_ARGS+=(--extra-package="${deb}"); done
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --arch-all   "${EXTRA_ARGS[@]}" --build-dir="${OUT}" "${DSC}" |& tee "${EVIDENCE}/sbuild.log"

test_summary="$(grep -Eo '100% tests passed, 0 tests failed out of [1-9][0-9]*' "${EVIDENCE}/sbuild.log" | tail -1 || true)"
[[ -n "${test_summary}" ]] || { echo "No positive non-zero upstream CTest PASS summary found" >&2; exit 1; }
printf '%s\n' "${test_summary}" > "${EVIDENCE}/tests-summary.txt"

mapfile -t DEBS < <(find "${OUT}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
(( ${#DEBS[@]} > 0 && ${#CHANGES[@]} == 1 && ${#BUILDINFO[@]} == 1 ))

STAGE="artifact-contract"
python3 - "${OUT}" "${CAMPAIGN}" "${NODE}" "${EVIDENCE}" <<'PY'
import json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]); c=json.load(open(sys.argv[2])); node=sys.argv[3]; ev=Path(sys.argv[4]); n=c["nodes"][node]
debs={}
for p in out.glob("*.deb"):
    pkg=subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()
    ver=subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip()
    if pkg in debs: raise SystemExit(f"duplicate binary {pkg}")
    if ver!=n["package_version"]: raise SystemExit(f"{pkg}: version {ver} != {n['package_version']}")
    debs[pkg]=str(p)
if set(debs)!=set(n["expected_binary_packages"]):
    raise SystemExit(f"{node}: binary set mismatch expected={sorted(n['expected_binary_packages'])} actual={sorted(debs)}")
(ev/"built-debs.json").write_text(json.dumps(debs,indent=2)+"\n")
PY

ECM_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["shared_predecessors"]["extra_cmake_modules"]["version"])' "${CAMPAIGN}")"
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE}/ecm-buildinfo-proof.txt"
: > "${EVIDENCE}/predecessor-buildinfo-proof.txt"
while IFS='|' read -r pred dev ver; do
  [[ -z "${pred}" ]] && continue
  grep -F "${dev} (= ${ver})" "${BUILDINFO[0]}" >> "${EVIDENCE}/predecessor-buildinfo-proof.txt"
done < "${EVIDENCE}/predecessor-contracts.txt"

STAGE="abi-contract"
RUNTIME_DEB="$(python3 - "${EVIDENCE}/built-debs.json" "${RUNTIME_PACKAGE}" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))[sys.argv[2]])
PY
)"
RUNTIME_ROOT="${WORK}/runtime-root"; mkdir -p "${RUNTIME_ROOT}"; dpkg-deb -x "${RUNTIME_DEB}" "${RUNTIME_ROOT}"
python3 - "${RUNTIME_ROOT}" "${SONAME}" "${EVIDENCE}" <<'PY'
import subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]); soname=sys.argv[2]; ev=Path(sys.argv[3]); matches=[]
for p in root.rglob("*.so*"):
    if p.is_symlink() or not p.is_file(): continue
    r=subprocess.run(["readelf","-d",str(p)],text=True,capture_output=True)
    if r.returncode==0 and f"Library soname: [{soname}]" in r.stdout:
        matches.append((p,r.stdout))
if len(matches)!=1: raise SystemExit(f"expected one ELF with SONAME {soname}, got {[str(x[0]) for x in matches]}")
p,dynamic=matches[0]
nm=subprocess.check_output(["nm","-D","--defined-only",str(p)],text=True)
exports=[x for x in nm.splitlines() if x.strip()]
if not exports: raise SystemExit("ABI export set is empty")
(ev/"abi-library.txt").write_text(str(p)+"\n")
(ev/"readelf-dynamic.txt").write_text(dynamic)
(ev/"abi-exports.txt").write_text("\n".join(exports)+"\n")
(ev/"abi-export-count.txt").write_text(str(len(exports))+"\n")
PY

STAGE="payload-contract"
python3 - "${EVIDENCE}/built-debs.json" "${NODE}" "${PACKAGE_VERSION}" "${WORK}" "${EVIDENCE}" <<'PY'
import json,subprocess,sys,shutil
from pathlib import Path
built=json.load(open(sys.argv[1])); node=sys.argv[2]; version=sys.argv[3]; work=Path(sys.argv[4]); ev=Path(sys.argv[5])
def field(pkg,name):
    return subprocess.check_output(["dpkg-deb","-f",built[pkg],name],text=True).strip()
def extract(pkg,label):
    root=work/label
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True)
    subprocess.check_call(["dpkg-deb","-x",built[pkg],str(root)])
    return root
if node=="breeze-icons":
    checks={
      "breeze-icon-theme":{"Breaks":"kf6-breeze-icon-theme (<< 6.28.0-3~)","Replaces":"kf6-breeze-icon-theme (<< 6.28.0-3~)"},
      "breeze-icon-theme-rcc":{"Breaks":"kf6-breeze-icon-theme-rcc (<< 6.28.0-3~)","Replaces":"kf6-breeze-icon-theme-rcc (<< 6.28.0-3~)"},
    }
    for pkg,fs in checks.items():
        for k,want in fs.items():
            if field(pkg,k)!=want: raise SystemExit(f"{pkg}: {k} mismatch: {field(pkg,k)!r}")
    for pkg,target in (("kf6-breeze-icon-theme","breeze-icon-theme"),("kf6-breeze-icon-theme-rcc","breeze-icon-theme-rcc")):
        dep=field(pkg,"Depends")
        want=f"{target} (>= {version})"
        if want not in dep: raise SystemExit(f"{pkg}: transitional dependency missing {want!r}: {dep!r}")
        root=extract(pkg,"transition-"+pkg)
        if list(root.rglob("*.svg")) or list(root.rglob("*.rcc")): raise SystemExit(f"{pkg}: transitional package owns icon payload")
    icons=extract("breeze-icon-theme","breeze-icons")
    if not (icons/"usr/share/icons/breeze/index.theme").is_file(): raise SystemExit("Breeze index.theme missing")
    if not (icons/"usr/share/icons/breeze-dark/index.theme").is_file(): raise SystemExit("Breeze Dark index.theme missing")
    if not next(icons.rglob("*.svg"),None): raise SystemExit("Breeze SVG payload missing")
    rcc=extract("breeze-icon-theme-rcc","breeze-rcc")
    if not next(rcc.rglob("*.rcc"),None): raise SystemExit("Breeze RCC payload missing")
    (ev/"payload-summary.txt").write_text("breeze-primary=PASS\nbreeze-rcc=PASS\nubuntu-transitionals=PASS\n")
elif node=="kdoctools":
    root=extract("kdoctools6","kdoctools-runtime")
    for rel in ("usr/bin/meinproc6","usr/bin/checkXML6"):
        if not (root/rel).is_file(): raise SystemExit(f"KDocTools tool missing: {rel}")
    custom=root/"usr/share/kf6/kdoctools/customization"
    if not custom.is_dir(): raise SystemExit("KDocTools customization payload missing")
    if not next(custom.rglob("*.xsl"),None): raise SystemExit("KDocTools XSL payload missing")
    (ev/"payload-summary.txt").write_text("meinproc6=PASS\ncheckXML6=PASS\ndocbook-customization=PASS\n")
else:
    raise SystemExit(f"unknown payload contract node {node}")
PY

STAGE="artifact-capture"
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG}" "${DEBIAN_TAR}" > "${EVIDENCE}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG}" "${DEBIAN_TAR}" "${EVIDENCE}/"

STAGE="lintian-source-binary"
lintian --fail-on error "${DSC}" "${CHANGES[0]}" |& tee "${EVIDENCE}/lintian-source-binary.log"

STAGE="consumer-runtime-closure"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends   "${ECM_DEB}" "${PREDECESSOR_DEBS[@]}" "${DEBS[@]}" |& tee "${EVIDENCE}/consumer-runtime-install.log"
sudo apt-get check |& tee "${EVIDENCE}/consumer-runtime-check.log"
[[ "$(dpkg-query -W -f='${Version}' "${RUNTIME_PACKAGE}")" == "${PACKAGE_VERSION}" ]]
while IFS='|' read -r _pred dev ver; do
  [[ -z "${dev}" ]] && continue
  [[ "$(dpkg-query -W -f='${Version}' "${dev}")" == "${ver}" ]]
done < "${EVIDENCE}/predecessor-contracts.txt"

STAGE="consumer-smoke"
CONSUMER="${WORK}/consumer"; mkdir -p "${CONSUMER}"
cat > "${CONSUMER}/main.cpp" <<'CPP'
int main() { return 0; }
CPP
cat > "${CONSUMER}/CMakeLists.txt" <<EOF
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXTier3SupportConsumer LANGUAGES CXX)
find_package(${CMAKE_PACKAGE} 6.30 REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE ${CMAKE_TARGET})
EOF
cmake -S "${CONSUMER}" -B "${CONSUMER}/build" -GNinja -DCMAKE_BUILD_TYPE=Release |& tee "${EVIDENCE}/consumer-configure.log"
cmake --build "${CONSUMER}/build" --verbose |& tee "${EVIDENCE}/consumer-build.log"
"${CONSUMER}/build/consumer" |& tee "${EVIDENCE}/consumer-run.log"

STAGE="pass-evidence"
python3 - "${RESULT}" "${EVIDENCE}" "${NODE}" "${PACKAGE_VERSION}" "${SONAME}" "${CAMPAIGN}" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
result=Path(sys.argv[1]); ev=Path(sys.argv[2]); node=sys.argv[3]; version=sys.argv[4]; soname=sys.argv[5]; c=json.load(open(sys.argv[6]))
d=json.loads(result.read_text()) if result.exists() and result.stat().st_size else {}
tests=re.search(r"100% tests passed, 0 tests failed out of ([1-9][0-9]*)",(ev/"sbuild.log").read_text())
files={}
for p in ev.iterdir():
    if p.is_file() and p.suffix in {".deb",".ddeb",".changes",".buildinfo",".dsc",".xz"}:
        files[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
preds={}
for line in (ev/"predecessor-contracts.txt").read_text().splitlines():
    if line.strip():
        pred,dev,ver=line.split("|"); preds[pred]={"dev_package":dev,"version":ver}
d.update({
 "result":"PASS","state":"PASS","node":node,"package_version":version,"package_attempted":True,
 "package_state_effect":"PASS","downstream_eligible":True,
 "tests":f"{tests.group(1)}/{tests.group(1)} PASS","lintian":"PASS-errors","apt_check":"PASS",
 "consumer_smoke":"PASS","payload_contract":"PASS","abi_soname":soname,
 "abi_export_count":int((ev/"abi-export-count.txt").read_text().strip()),
 "ecm_predecessor":c["shared_predecessors"]["extra_cmake_modules"]["version"],
 "retained_predecessors":preds,"files":files,
})
result.write_text(json.dumps(d,indent=2)+"\n")
PY

STATE=PASS
STAGE=complete
echo "KDE Tier 3 support build level 0 ${NODE}: PASS"
