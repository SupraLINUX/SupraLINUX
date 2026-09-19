#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAMPAIGN="${ROOT}/manifests/kde-tier1-package-campaign-batch7.json"
NODE="${1:-}"
[[ -n "${NODE}" ]] || { echo "Usage: $0 <node>" >&2; exit 2; }

eval "$(python3 - "${CAMPAIGN}" "${NODE}" <<'PY2'
import json, shlex, sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text()); n=d.get("nodes",{}).get(sys.argv[2])
if not isinstance(n,dict): raise SystemExit(f"Unknown Batch 7 node: {sys.argv[2]}")
s=d["shared_predecessors"]; y=n["symbols"]; c=n["copyright"]; k=n["signing_key"]
vals={
"UPSTREAM_VERSION":n["upstream_version"],"SOURCE_PACKAGE":n["source_package"],"DEBIAN_VERSION":n["package_version"],
"UPSTREAM_URL":n["source_url"],"UPSTREAM_SHA256":n["source_sha256"],"SYMBOLS_FILE":y["file"],
"SYMBOLS_REFERENCE_SHA256":y["sha256"],"SYMBOLS_REFERENCE_TREE":y["tree_provider"],
"COPYRIGHT_REFERENCE_SHA256":c["sha256"],"SIGNING_KEY_SHA256":k["sha256"],
"RUNTIME_PACKAGE":n["runtime_package"],"PYTHON_PACKAGE":n["python_package"],"PYTHON_MODULE":n["python_module"],
"SONAME":n["soname"],"ECM_VERSION":s["extra_cmake_modules"]["version"],
"ECM_DEB_SHA256":s["extra_cmake_modules"]["deb_sha256"],
"REFERENCE_SNAPSHOT_SHA256":s["packaging_trees"]["snapshot_json_sha256"]}
for key,value in vals.items(): print(f"{key}={shlex.quote(str(value))}")
PY2
)"

PACKAGE_META="${ROOT}/packages/kde/${NODE}/debian"
CONSUMER_META="${ROOT}/packages/kde/${NODE}/consumer"
WORK_DIR="${ROOT}/.work/kde-tier1-package-batch7/${NODE}"
SOURCE_WORK="${WORK_DIR}/source"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-package-batch7/${NODE}"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar"
MIRROR="${SBUILD_MIRROR:-http://azure.archive.ubuntu.com/ubuntu}"
: "${ECM_ARTIFACT_DIR:?ECM_ARTIFACT_DIR must point at retained ECM PASS artifact}"
: "${TIER1_REFERENCE_DIR:?TIER1_REFERENCE_DIR must point at retained Tier 1 packaging-tree artifact}"

STATE="FAIL"; STAGE="initialization"; STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${SOURCE_WORK}" "${OUT_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"
write_result() {
  local rc="$?" finished_at
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT_JSON}" "${NODE}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" "${UPSTREAM_VERSION}" "${DEBIAN_VERSION}" "${PYTHON_MODULE}" <<'PY2'
import json,sys
from pathlib import Path
p,node,state,rc,stage,started,finished,version,debver,pymod=sys.argv[1:]
Path(p).write_text(json.dumps({
 "node":node,"state":state,"exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
 "authoritative":False,"runner_class":"github-hosted-ubuntu-26.04","upstream_authority":"kde-upstream",
 "upstream_version":version,"debian_version":debver,"ecm_predecessor":"6.30.0-0supralinux3",
 "claim":"hosted-clean-package-preflight","python_module":pymod,
 "lintian_gate":"sbuild-summary-plus-dsc-plus-changes"
},indent=2)+"\n")
PY2
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "=== SupraLINUX KDE Tier 1 Batch 7: ${NODE} ${UPSTREAM_VERSION} (${DEBIAN_VERSION}) ==="

STAGE="campaign-validation"
python3 - "${CAMPAIGN}" "${NODE}" <<'PY2'
import json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text()); n=d["nodes"][sys.argv[2]]
if n["state"] not in {"prepared-pending-build","remediation-pending-build","PASS"}:
    raise SystemExit(f"Node state not attemptable: {n['state']}")
if d["authority"]!="kde-upstream" or d["frameworks_series"]!="6.30.0":
    raise SystemExit("Campaign authority/version mismatch")
if n["upstream_defaults"].get("BUILD_PYTHON_BINDINGS")!="ON" or n["upstream_defaults"].get("BUILD_TESTING")!="ON":
    raise SystemExit("Batch 7 requires Python bindings and tests")
PY2
test -d "${PACKAGE_META}"
test -s "${CONSUMER_META}/CMakeLists.txt"
test -s "${CONSUMER_META}/main.cpp"
test -s "${PACKAGE_META}/upstream/signing-key.asc"
grep -Fq 'DEB_PYTHON_INSTALL_LAYOUT = deb' "${PACKAGE_META}/rules"
grep -Fq -- '-DBUILD_PYTHON_BINDINGS=ON' "${PACKAGE_META}/rules"
grep -Fq -- '-DBUILD_TESTING=ON' "${PACKAGE_META}/rules"
printf '%s  %s\n' "${SIGNING_KEY_SHA256}" "${PACKAGE_META}/upstream/signing-key.asc" | sha256sum --check --strict

STAGE="retained-input-validation"
ECM_DEB="$(find "${ECM_ARTIFACT_DIR}" -maxdepth 2 -type f -name "extra-cmake-modules_${ECM_VERSION}_all.deb" -print -quit)"
[[ -n "${ECM_DEB}" && -s "${ECM_DEB}" ]] || { echo "Retained ECM PASS .deb missing" >&2; exit 1; }
printf '%s  %s\n' "${ECM_DEB_SHA256}" "${ECM_DEB}" | sha256sum --check --strict
[[ "$(dpkg-deb -f "${ECM_DEB}" Package)" == "extra-cmake-modules" ]]
[[ "$(dpkg-deb -f "${ECM_DEB}" Version)" == "${ECM_VERSION}" ]]
sha256sum "${ECM_DEB}" > "${EVIDENCE_DIR}/ecm-predecessor-sha256.txt"
REFERENCE_SNAPSHOT="${TIER1_REFERENCE_DIR}/snapshot.json"
test -s "${REFERENCE_SNAPSHOT}"
printf '%s  %s\n' "${REFERENCE_SNAPSHOT_SHA256}" "${REFERENCE_SNAPSHOT}" | sha256sum --check --strict
SYMBOLS_REFERENCE="${TIER1_REFERENCE_DIR}/trees/${SYMBOLS_REFERENCE_TREE}/${NODE}/debian/${SYMBOLS_FILE}"
COPYRIGHT_REFERENCE="${TIER1_REFERENCE_DIR}/trees/debian/${NODE}/debian/copyright"
test -s "${SYMBOLS_REFERENCE}"
test -s "${COPYRIGHT_REFERENCE}"
printf '%s  %s\n' "${SYMBOLS_REFERENCE_SHA256}" "${SYMBOLS_REFERENCE}" | sha256sum --check --strict
printf '%s  %s\n' "${COPYRIGHT_REFERENCE_SHA256}" "${COPYRIGHT_REFERENCE}" | sha256sum --check --strict
sha256sum "${SYMBOLS_REFERENCE}" > "${EVIDENCE_DIR}/symbols-reference-sha256.txt"
sha256sum "${COPYRIGHT_REFERENCE}" > "${EVIDENCE_DIR}/copyright-reference-sha256.txt"

STAGE="host-validation"
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  binutils ca-certificates cmake curl devscripts dpkg-dev g++ lintian mmdebstrap ninja-build \
  pkg-config python3 sbuild uidmap ubuntu-keyring xz-utils
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true
{ cat /etc/os-release; uname -a; python3 --version; sbuild --version; mmdebstrap --version; lintian --version; } > "${EVIDENCE_DIR}/host.txt"

STAGE="upstream-source"
ORIG_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 --output "${ORIG_TARBALL}" "${UPSTREAM_URL}"
printf '%s  %s\n' "${UPSTREAM_SHA256}" "${ORIG_TARBALL}" | sha256sum --check --strict
tar -xJf "${ORIG_TARBALL}" -C "${SOURCE_WORK}"
EXTRACTED="${SOURCE_WORK}/${NODE}-${UPSTREAM_VERSION}"
SOURCE_DIR="${SOURCE_WORK}/${SOURCE_PACKAGE}-${UPSTREAM_VERSION}"
test -d "${EXTRACTED}"
mv "${EXTRACTED}" "${SOURCE_DIR}"
cp -a "${PACKAGE_META}" "${SOURCE_DIR}/debian"
cp -a "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}"
cp -a "${COPYRIGHT_REFERENCE}" "${SOURCE_DIR}/debian/copyright"
python3 - "${SOURCE_DIR}/debian/copyright" <<'PY2'
import sys
from pathlib import Path
p=Path(sys.argv[1]); lines=p.read_text().splitlines()
start=next((i for i,x in enumerate(lines) if x.strip()=="Files: debian/*"),None)
if start is None: raise SystemExit("Reference copyright lacks Files: debian/* stanza")
lic=next((i for i in range(start+1,len(lines)) if lines[i].startswith("License:")),None)
if lic is None: raise SystemExit("Reference debian/* stanza lacks License field")
if not any("SupraLINUX Project" in x for x in lines[start:lic]):
    lines.insert(lic,"           2026, SupraLINUX Project")
p.write_text("\n".join(lines)+"\n")
PY2
chmod +x "${SOURCE_DIR}/debian/rules"

STAGE="source-package"
pushd "${SOURCE_WORK}" >/dev/null
dpkg-source -b "$(basename "${SOURCE_DIR}")"
popd >/dev/null
DSC="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.dsc"
DEBIAN_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.debian.tar.xz"
test -s "${DSC}"
test -s "${DEBIAN_TARBALL}"
sha256sum "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/source-package-sha256.txt"

STAGE="sbuild-rootfs"
rm -f "${CHROOT_TARBALL}"
mmdebstrap --mode=unshare --variant=buildd --architectures=amd64 --components=main,universe \
  --skip=output/mknod --format=tar resolute "${CHROOT_TARBALL}" "${MIRROR}" |& tee "${EVIDENCE_DIR}/rootfs.log"
test -s "${CHROOT_TARBALL}"
sha256sum "${CHROOT_TARBALL}" > "${EVIDENCE_DIR}/rootfs-sha256.txt"

STAGE="sbuild"
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --arch-all \
  --extra-package="${ECM_DEB}" --build-dir="${OUT_DIR}" "${DSC}" |& tee "${EVIDENCE_DIR}/sbuild.log"
if grep -Eq '^Lintian:[[:space:]]+fail[[:space:]]*$' "${EVIDENCE_DIR}/sbuild.log"; then
  echo "sbuild reported Lintian failure" >&2; exit 1
fi
grep -Eq '100% tests passed, 0 tests failed out of [1-9][0-9]*' "${EVIDENCE_DIR}/sbuild.log" || {
  echo "No positive non-zero CTest PASS summary found" >&2; exit 1;
}
mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
mapfile -t EXPECTED_PACKAGES < <(python3 - "${CAMPAIGN}" "${NODE}" <<'PY2'
import json,sys
from pathlib import Path
for x in json.loads(Path(sys.argv[1]).read_text())["nodes"][sys.argv[2]]["binary_contracts"]: print(x["name"])
PY2
)
(( ${#DEBS[@]} == ${#EXPECTED_PACKAGES[@]} && ${#CHANGES[@]} == 1 && ${#BUILDINFO[@]} == 1 )) || {
  echo "Unexpected build artifact counts: debs=${#DEBS[@]} expected=${#EXPECTED_PACKAGES[@]} changes=${#CHANGES[@]} buildinfo=${#BUILDINFO[@]}" >&2
  exit 1
}
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/ecm-buildinfo-proof.txt"

STAGE="artifact-contract"
declare -A DEB_BY_PACKAGE=()
for deb in "${DEBS[@]}"; do
  package="$(dpkg-deb -f "${deb}" Package)"
  DEB_BY_PACKAGE["${package}"]="${deb}"
  [[ "$(dpkg-deb -f "${deb}" Version)" == "${DEBIAN_VERSION}" ]]
done
for package in "${EXPECTED_PACKAGES[@]}"; do
  [[ -n "${DEB_BY_PACKAGE[$package]:-}" ]] || { echo "Expected binary missing: ${package}" >&2; exit 1; }
done
python3 - "${CAMPAIGN}" "${NODE}" "${OUT_DIR}" <<'PY2'
import json,subprocess,sys
from pathlib import Path
campaign,node_id,out_dir=sys.argv[1:]
node=json.loads(Path(campaign).read_text())["nodes"][node_id]
debs={}
for p in Path(out_dir).glob("*.deb"):
    debs[subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()]=p
def field(p,n):
    r=subprocess.run(["dpkg-deb","-f",str(p),n],text=True,capture_output=True)
    return r.stdout.strip() if r.returncode==0 else ""
def ma(p):
    v=field(p,"Multi-Arch")
    return None if v in {"","no"} else v
for c in node["binary_contracts"]:
    p=debs[c["name"]]
    if field(p,"Architecture")!=c["architecture"]: raise SystemExit(f"{c['name']}: Architecture mismatch")
    if ma(p)!=c["multi_arch"]: raise SystemExit(f"{c['name']}: Multi-Arch mismatch {ma(p)!r} != {c['multi_arch']!r}")
    for x in ("Provides","Breaks","Replaces","Conflicts"):
        if field(p,x): raise SystemExit(f"{c['name']}: unexpected {x}={field(p,x)}")
for pkg,tokens in node.get("dependency_contracts",{}).items():
    value=field(debs[pkg],"Depends")
    for token in tokens:
        if token not in value: raise SystemExit(f"{pkg}: missing Depends token {token!r}; got {value!r}")
for pkg,tokens in node.get("recommendation_contracts",{}).items():
    value=field(debs[pkg],"Recommends")
    for token in tokens:
        if token not in value: raise SystemExit(f"{pkg}: missing Recommends token {token!r}; got {value!r}")
PY2
RUNTIME_DEB="${DEB_BY_PACKAGE[$RUNTIME_PACKAGE]}"
RUNTIME_ROOT="${WORK_DIR}/runtime-root"
mkdir -p "${RUNTIME_ROOT}"
dpkg-deb -x "${RUNTIME_DEB}" "${RUNTIME_ROOT}"
LIB_PATH="$(find "${RUNTIME_ROOT}" -type f -name "${SONAME}.*" -print -quit)"
test -n "${LIB_PATH}"
readelf -d "${LIB_PATH}" > "${EVIDENCE_DIR}/readelf-dynamic.txt"
grep -Fq "Library soname: [${SONAME}]" "${EVIDENCE_DIR}/readelf-dynamic.txt"
PYTHON_DEB="${DEB_BY_PACKAGE[$PYTHON_PACKAGE]}"
dpkg-deb -c "${PYTHON_DEB}" > "${EVIDENCE_DIR}/python-package-files.txt"
grep -Eq "usr/lib/python3/dist-packages/${PYTHON_MODULE}\..*\.so$" "${EVIDENCE_DIR}/python-package-files.txt"

STAGE="artifact-capture"
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" "${EVIDENCE_DIR}/"

STAGE="lintian-source-binary"
lintian --fail-on error "${DSC}" "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian-source-binary.log"

STAGE="consumer-runtime-closure"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${DEBS[@]}" |& tee "${EVIDENCE_DIR}/consumer-runtime-install.log"
sudo apt-get check |& tee "${EVIDENCE_DIR}/consumer-runtime-check.log"
: > "${EVIDENCE_DIR}/consumer-runtime-packages.txt"
for package in "${EXPECTED_PACKAGES[@]}"; do
  installed_version="$(dpkg-query -W -f='${Version}' "${package}")"
  [[ "${installed_version}" == "${DEBIAN_VERSION}" ]] || {
    echo "Installed ${package} version ${installed_version} != built ${DEBIAN_VERSION}" >&2; exit 1;
  }
  printf '%s=%s\n' "${package}" "${installed_version}" >> "${EVIDENCE_DIR}/consumer-runtime-packages.txt"
done

STAGE="python-import-smoke"
python3 - "${PYTHON_MODULE}" "${PYTHON_PACKAGE}" <<'PY2' |& tee "${EVIDENCE_DIR}/python-import.log"
import importlib,subprocess,sys
name,pkg=sys.argv[1:]
m=importlib.import_module(name)
path=m.__file__
print(f"module={name}")
print(f"path={path}")
owned=subprocess.check_output(["dpkg-query","-L",pkg],text=True).splitlines()
if path not in owned:
    raise SystemExit(f"{path} is not owned by exact built package {pkg}")
print("python_import=PASS")
PY2

STAGE="consumer-smoke"
CONSUMER_ROOT="${WORK_DIR}/consumer-root"
CONSUMER_BUILD="${WORK_DIR}/consumer-build"
mkdir -p "${CONSUMER_ROOT}"
for deb in "${DEBS[@]}"; do dpkg-deb -x "${deb}" "${CONSUMER_ROOT}"; done
cmake -S "${CONSUMER_META}" -B "${CONSUMER_BUILD}" -GNinja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="${CONSUMER_ROOT}/usr" |& tee "${EVIDENCE_DIR}/consumer-configure.log"
cmake --build "${CONSUMER_BUILD}" --verbose |& tee "${EVIDENCE_DIR}/consumer-build.log"
CONSUMER_BINARY="${CONSUMER_BUILD}/${NODE}-consumer"
MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
LD_LIBRARY_PATH="${CONSUMER_ROOT}/usr/lib/${MULTIARCH}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" \
  "${CONSUMER_BINARY}" |& tee "${EVIDENCE_DIR}/consumer-run.log"

STAGE="dag-pass-evidence"
{
  echo "node=${NODE}"
  echo "state=PASS"
  echo "upstream_version=${UPSTREAM_VERSION}"
  echo "debian_version=${DEBIAN_VERSION}"
  echo "ecm_predecessor=${ECM_VERSION}"
  echo "source_sha256=${UPSTREAM_SHA256}"
  echo "tests=PASS-via-sbuild-nonzero-ctest"
  echo "lintian=PASS-source-and-binary"
  echo "abi_soname=${SONAME}"
  echo "consumer_smoke=PASS"
  echo "python_module=${PYTHON_MODULE}"
  echo "python_import=PASS"
  echo "apt_check=PASS"
  echo "downstream_eligible=yes"
} > "${EVIDENCE_DIR}/dag-node.txt"
STATE="PASS"
STAGE="complete"
echo "KDE Tier 1 Batch 7 node ${NODE}: PASS"
