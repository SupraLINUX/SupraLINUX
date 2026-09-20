#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAMPAIGN="${ROOT}/manifests/kde-tier2-package-campaign-batch1.json"

eval "$(python3 - "${CAMPAIGN}" <<'PY'
import json,shlex,sys
d=json.load(open(sys.argv[1])); n=d["nodes"]["kauth"]; s=d["shared_predecessors"]; r=d["technical_references"]["debian_6_30"]
vals={
"UPSTREAM_VERSION":n["upstream_version"],"SOURCE_PACKAGE":n["source_package"],"DEBIAN_VERSION":n["package_version"],
"UPSTREAM_URL":n["source_url"],"UPSTREAM_SHA256":n["source_sha256"],"SIGNING_KEY_SHA256":n["signing_key"]["sha256"],
"RUNTIME_PACKAGE":n["runtime_package"],"SONAME":n["soname"],
"ECM_VERSION":s["extra_cmake_modules"]["version"],"ECM_DEB_SHA256":s["extra_cmake_modules"]["deb_sha256"],
"KCORE_VERSION":s["kcoreaddons"]["version"],"KCORE_DATA_SHA":s["kcoreaddons"]["files"]["data"],"KCORE_DEV_SHA":s["kcoreaddons"]["files"]["dev"],"KCORE_RUNTIME_SHA":s["kcoreaddons"]["files"]["runtime"],
"KWINDOW_VERSION":s["kwindowsystem"]["version"],"KWINDOW_DATA_SHA":s["kwindowsystem"]["files"]["data"],"KWINDOW_DEV_SHA":s["kwindowsystem"]["files"]["dev"],"KWINDOW_RUNTIME_SHA":s["kwindowsystem"]["files"]["runtime"],
"DEBIAN_REF_URL":r["debian_tar_url"],"DEBIAN_REF_SHA":r["debian_tar_sha256"]}
for k,v in vals.items(): print(f"{k}={shlex.quote(str(v))}")
PY
)"

PACKAGE_META="${ROOT}/packages/kde/kauth/debian"
CONSUMER_META="${ROOT}/packages/kde/kauth/consumer"
WORK_DIR="${ROOT}/.work/kde-tier2-package-batch1/kauth"
SOURCE_WORK="${WORK_DIR}/source"
OUT_DIR="${WORK_DIR}/out"
REFERENCE_DIR="${WORK_DIR}/debian-reference"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier2-package-batch1/kauth"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar"
MIRROR="${SBUILD_MIRROR:-http://azure.archive.ubuntu.com/ubuntu}"
: "${ECM_ARTIFACT_DIR:?ECM_ARTIFACT_DIR must point at retained ECM PASS artifact}"
: "${KCOREADDONS_ARTIFACT_DIR:?KCOREADDONS_ARTIFACT_DIR must point at retained KCoreAddons PASS artifact}"
: "${KWINDOWSYSTEM_ARTIFACT_DIR:?KWINDOWSYSTEM_ARTIFACT_DIR must point at retained KWindowSystem PASS artifact}"

STATE="FAIL"; STAGE="initialization"; STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${SOURCE_WORK}" "${OUT_DIR}" "${REFERENCE_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"
write_result() {
  local rc="$?" finished_at
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT_JSON}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" "${UPSTREAM_VERSION}" "${DEBIAN_VERSION}" <<'PY'
import json,sys
from pathlib import Path
p,state,rc,stage,started,finished,version,debver=sys.argv[1:]
Path(p).write_text(json.dumps({
 "node":"kauth","tier":2,"state":state,"exit_code":int(rc),"stage":stage,
 "started_at":started,"finished_at":finished,"authoritative":False,
 "runner_class":"github-hosted-ubuntu-26.04","upstream_authority":"kde-upstream",
 "upstream_version":version,"debian_version":debver,
 "backend":"POLKITQT6-1","helper_backend":"DBUS",
 "claim":"hosted-clean-package-preflight"
},indent=2)+"\n")
PY
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1
echo "=== SupraLINUX KDE Tier 2 Batch 1: KAuth ${UPSTREAM_VERSION} (${DEBIAN_VERSION}) ==="

STAGE="campaign-validation"
python3 - "${CAMPAIGN}" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); n=d["nodes"]["kauth"]
assert d["schema"]==2 and d["batch"]=="tier2-batch-1"
assert d["authority"]=="kde-upstream" and d["frameworks_series"]=="6.30.0"
assert n["state"] in {"prepared-pending-build","remediation-pending-build","PASS"}
assert n["kde_framework_build_dependencies"]==["KCoreAddons","KWindowSystem"]
assert n["backend_profile"]=={"KAUTH_BACKEND_NAME":"POLKITQT6-1","KAUTH_HELPER_BACKEND_NAME":"DBUS","fake_backend_allowed":False}
PY
test -s "${PACKAGE_META}/control"; test -x "${PACKAGE_META}/rules"
test -s "${CONSUMER_META}/CMakeLists.txt"; test -s "${CONSUMER_META}/main.cpp"
printf '%s  %s\n' "${SIGNING_KEY_SHA256}" "${PACKAGE_META}/upstream/signing-key.asc" | sha256sum --check --strict
grep -Fq -- '-DKAUTH_BACKEND_NAME=POLKITQT6-1' "${PACKAGE_META}/rules"
grep -Fq -- '-DKAUTH_HELPER_BACKEND_NAME=DBUS' "${PACKAGE_META}/rules"
grep -Fq 'libkf6coreaddons-dev (>= 6.30.0~)' "${PACKAGE_META}/control"
grep -Fq 'libkf6windowsystem-dev (>= 6.30.0~)' "${PACKAGE_META}/control"
grep -Fq 'libpolkit-qt6-1-dev (>= 0.200.0-2~)' "${PACKAGE_META}/control"

STAGE="retained-input-validation"
ECM_DEB="$(find "${ECM_ARTIFACT_DIR}" -maxdepth 2 -type f -name "extra-cmake-modules_${ECM_VERSION}_all.deb" -print -quit)"
[[ -n "${ECM_DEB}" && -s "${ECM_DEB}" ]]
printf '%s  %s\n' "${ECM_DEB_SHA256}" "${ECM_DEB}" | sha256sum --check --strict

mapfile -t KCORE_DEBS < <(find "${KCOREADDONS_ARTIFACT_DIR}" -maxdepth 2 -type f -name '*.deb' -print | sort)
mapfile -t KWINDOW_DEBS < <(find "${KWINDOWSYSTEM_ARTIFACT_DIR}" -maxdepth 2 -type f -name '*.deb' -print | sort)
(( ${#KCORE_DEBS[@]} >= 4 && ${#KWINDOW_DEBS[@]} >= 4 ))

find_pkg() {
  local dir="$1" pattern="$2"
  find "${dir}" -maxdepth 2 -type f -name "${pattern}" -print -quit
}
KCORE_DATA="$(find_pkg "${KCOREADDONS_ARTIFACT_DIR}" "libkf6coreaddons-data_${KCORE_VERSION}_all.deb")"
KCORE_DEV="$(find_pkg "${KCOREADDONS_ARTIFACT_DIR}" "libkf6coreaddons-dev_${KCORE_VERSION}_amd64.deb")"
KCORE_RUNTIME="$(find_pkg "${KCOREADDONS_ARTIFACT_DIR}" "libkf6coreaddons6_${KCORE_VERSION}_amd64.deb")"
KWINDOW_DATA="$(find_pkg "${KWINDOWSYSTEM_ARTIFACT_DIR}" "libkf6windowsystem-data_${KWINDOW_VERSION}_all.deb")"
KWINDOW_DEV="$(find_pkg "${KWINDOWSYSTEM_ARTIFACT_DIR}" "libkf6windowsystem-dev_${KWINDOW_VERSION}_amd64.deb")"
KWINDOW_RUNTIME="$(find_pkg "${KWINDOWSYSTEM_ARTIFACT_DIR}" "libkf6windowsystem6_${KWINDOW_VERSION}_amd64.deb")"
for f in "${KCORE_DATA}" "${KCORE_DEV}" "${KCORE_RUNTIME}" "${KWINDOW_DATA}" "${KWINDOW_DEV}" "${KWINDOW_RUNTIME}"; do [[ -n "${f}" && -s "${f}" ]]; done
printf '%s  %s\n' "${KCORE_DATA_SHA}" "${KCORE_DATA}" | sha256sum --check --strict
printf '%s  %s\n' "${KCORE_DEV_SHA}" "${KCORE_DEV}" | sha256sum --check --strict
printf '%s  %s\n' "${KCORE_RUNTIME_SHA}" "${KCORE_RUNTIME}" | sha256sum --check --strict
printf '%s  %s\n' "${KWINDOW_DATA_SHA}" "${KWINDOW_DATA}" | sha256sum --check --strict
printf '%s  %s\n' "${KWINDOW_DEV_SHA}" "${KWINDOW_DEV}" | sha256sum --check --strict
printf '%s  %s\n' "${KWINDOW_RUNTIME_SHA}" "${KWINDOW_RUNTIME}" | sha256sum --check --strict
[[ "$(dpkg-deb -f "${KCORE_DEV}" Version)" == "${KCORE_VERSION}" ]]
[[ "$(dpkg-deb -f "${KWINDOW_DEV}" Version)" == "${KWINDOW_VERSION}" ]]
sha256sum "${ECM_DEB}" "${KCORE_DEBS[@]}" "${KWINDOW_DEBS[@]}" > "${EVIDENCE_DIR}/retained-predecessor-sha256.txt"

STAGE="host-validation"
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  binutils ca-certificates cmake curl devscripts dpkg-dev g++ lintian mmdebstrap ninja-build \
  pkg-config python3 sbuild uidmap ubuntu-keyring xz-utils
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true
{ cat /etc/os-release; uname -a; sbuild --version; mmdebstrap --version; lintian --version; } > "${EVIDENCE_DIR}/host.txt"

STAGE="technical-reference"
DEBIAN_REF_TAR="${REFERENCE_DIR}/kf6-kauth_6.30.0-1.debian.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 -o "${DEBIAN_REF_TAR}" "${DEBIAN_REF_URL}"
printf '%s  %s\n' "${DEBIAN_REF_SHA}" "${DEBIAN_REF_TAR}" | sha256sum --check --strict
tar -xJf "${DEBIAN_REF_TAR}" -C "${REFERENCE_DIR}"
SYMBOLS_REFERENCE="${REFERENCE_DIR}/debian/libkf6authcore6.symbols"
test -s "${SYMBOLS_REFERENCE}"
sha256sum "${DEBIAN_REF_TAR}" "${SYMBOLS_REFERENCE}" > "${EVIDENCE_DIR}/technical-reference-sha256.txt"

STAGE="upstream-source"
ORIG_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 -o "${ORIG_TARBALL}" "${UPSTREAM_URL}"
printf '%s  %s\n' "${UPSTREAM_SHA256}" "${ORIG_TARBALL}" | sha256sum --check --strict
tar -xJf "${ORIG_TARBALL}" -C "${SOURCE_WORK}"
EXTRACTED="${SOURCE_WORK}/kauth-${UPSTREAM_VERSION}"
SOURCE_DIR="${SOURCE_WORK}/${SOURCE_PACKAGE}-${UPSTREAM_VERSION}"
test -d "${EXTRACTED}"; mv "${EXTRACTED}" "${SOURCE_DIR}"
cp -a "${PACKAGE_META}" "${SOURCE_DIR}/debian"
cp -a "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/libkf6authcore6.symbols"
chmod +x "${SOURCE_DIR}/debian/rules"

STAGE="development-contract-source"
python3 "${ROOT}/scripts/audit-kde-development-contract.py" source --node kauth --campaign "${CAMPAIGN}" --source-dir "${SOURCE_DIR}" --control "${SOURCE_DIR}/debian/control" --output "${EVIDENCE_DIR}/development-contract-source.json"

STAGE="source-package"
pushd "${SOURCE_WORK}" >/dev/null
dpkg-source -b "$(basename "${SOURCE_DIR}")"
popd >/dev/null
DSC="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.dsc"
DEBIAN_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.debian.tar.xz"
test -s "${DSC}"; test -s "${DEBIAN_TARBALL}"
sha256sum "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/source-package-sha256.txt"

STAGE="sbuild-rootfs"
rm -f "${CHROOT_TARBALL}"
mmdebstrap --mode=unshare --variant=buildd --architectures=amd64 --components=main,universe \
  --skip=output/mknod --format=tar resolute "${CHROOT_TARBALL}" "${MIRROR}" |& tee "${EVIDENCE_DIR}/rootfs.log"
sha256sum "${CHROOT_TARBALL}" > "${EVIDENCE_DIR}/rootfs-sha256.txt"

STAGE="sbuild"
EXTRA_ARGS=(--extra-package="${ECM_DEB}")
for deb in "${KCORE_DEBS[@]}" "${KWINDOW_DEBS[@]}"; do EXTRA_ARGS+=(--extra-package="${deb}"); done
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --arch-all \
  "${EXTRA_ARGS[@]}" --build-dir="${OUT_DIR}" "${DSC}" |& tee "${EVIDENCE_DIR}/sbuild.log"
if grep -Eq '^Lintian:[[:space:]]+fail[[:space:]]*$' "${EVIDENCE_DIR}/sbuild.log"; then echo "sbuild reported Lintian failure" >&2; exit 1; fi
grep -Eq '100% tests passed, 0 tests failed out of [1-9][0-9]*' "${EVIDENCE_DIR}/sbuild.log" || { echo "No positive non-zero CTest PASS summary found" >&2; exit 1; }

mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
(( ${#DEBS[@]} == 5 && ${#CHANGES[@]} == 1 && ${#BUILDINFO[@]} == 1 ))
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/ecm-buildinfo-proof.txt"
grep -F "libkf6coreaddons-dev (= ${KCORE_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/kcoreaddons-buildinfo-proof.txt"
grep -F "libkf6windowsystem-dev (= ${KWINDOW_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/kwindowsystem-buildinfo-proof.txt"

STAGE="artifact-contract"
declare -A DEB_BY_PACKAGE=()
for deb in "${DEBS[@]}"; do
  package="$(dpkg-deb -f "${deb}" Package)"
  DEB_BY_PACKAGE["${package}"]="${deb}"
  [[ "$(dpkg-deb -f "${deb}" Version)" == "${DEBIAN_VERSION}" ]]
done
for package in libkf6auth-data libkf6auth-dev libkf6auth-dev-bin libkf6auth-doc libkf6authcore6; do
  [[ -n "${DEB_BY_PACKAGE[${package}]:-}" ]] || { echo "Expected binary missing: ${package}" >&2; exit 1; }
done
python3 - "${CAMPAIGN}" "${OUT_DIR}" <<'PY'
import json,subprocess,sys
from pathlib import Path
n=json.load(open(sys.argv[1]))["nodes"]["kauth"]; out=Path(sys.argv[2]); debs={}
for p in out.glob("*.deb"):
    debs[subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()]=p
def field(p,n):
    r=subprocess.run(["dpkg-deb","-f",str(p),n],text=True,capture_output=True)
    return r.stdout.strip() if r.returncode==0 else ""
def ma(p):
    v=field(p,"Multi-Arch"); return None if v in {"","no"} else v
for c in n["binary_contracts"]:
    p=debs[c["name"]]
    if field(p,"Architecture")!=c["architecture"]: raise SystemExit(f"{c['name']}: Architecture mismatch")
    if ma(p)!=c["multi_arch"]: raise SystemExit(f"{c['name']}: Multi-Arch mismatch")
    for x in ("Provides","Breaks","Replaces","Conflicts"):
        if field(p,x): raise SystemExit(f"{c['name']}: unexpected {x}={field(p,x)}")
for pkg,tokens in n["dependency_contracts"].items():
    v=field(debs[pkg],"Depends")
    for token in tokens:
        if token not in v: raise SystemExit(f"{pkg}: missing Depends token {token!r}; got {v!r}")
PY

RUNTIME_DEB="${DEB_BY_PACKAGE[libkf6authcore6]}"
DEV_DEB="${DEB_BY_PACKAGE[libkf6auth-dev]}"
DEV_BIN_DEB="${DEB_BY_PACKAGE[libkf6auth-dev-bin]}"
RUNTIME_ROOT="${WORK_DIR}/runtime-root"; DEV_ROOT="${WORK_DIR}/dev-root"
mkdir -p "${RUNTIME_ROOT}" "${DEV_ROOT}"
dpkg-deb -x "${RUNTIME_DEB}" "${RUNTIME_ROOT}"
dpkg-deb -x "${DEV_DEB}" "${DEV_ROOT}"
dpkg-deb -x "${DEV_BIN_DEB}" "${DEV_ROOT}"
LIB_PATH="$(find "${RUNTIME_ROOT}" -type f -name "${SONAME}.*" -print -quit)"
test -n "${LIB_PATH}"
readelf -d "${LIB_PATH}" > "${EVIDENCE_DIR}/readelf-dynamic.txt"
grep -Fq "Library soname: [${SONAME}]" "${EVIDENCE_DIR}/readelf-dynamic.txt"
nm -D --defined-only "${LIB_PATH}" | sort > "${EVIDENCE_DIR}/abi-exports.txt"
EXPORT_COUNT="$(wc -l < "${EVIDENCE_DIR}/abi-exports.txt")"
(( EXPORT_COUNT > 20 ))
find "${RUNTIME_ROOT}" -type f -path '*/qt6/plugins/kf6/kauth/backend/*.so' -print -quit | grep -q .
find "${RUNTIME_ROOT}" -type f -path '*/qt6/plugins/kf6/kauth/helper/*.so' -print -quit | grep -q .
find "${DEV_ROOT}" -type f -name kauth-policy-gen -print -quit | grep -q .
AUTH_CONFIG="$(find "${DEV_ROOT}" -type f -name KF6AuthConfig.cmake -print -quit)"
test -s "${AUTH_CONFIG}"
grep -Fq 'set(KAUTH_BACKEND_NAME "POLKITQT6-1")' "${AUTH_CONFIG}"
grep -Fq 'set(KAUTH_HELPER_BACKEND_NAME "DBUS")' "${AUTH_CONFIG}"

STAGE="development-contract-artifact"
python3 "${ROOT}/scripts/audit-kde-development-contract.py" artifact --node kauth --campaign "${CAMPAIGN}" --debs-dir "${OUT_DIR}" --consumer-cmake "${CONSUMER_META}/CMakeLists.txt" --output "${EVIDENCE_DIR}/development-contract-artifact.json"

STAGE="artifact-capture"
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" "${EVIDENCE_DIR}/"

STAGE="lintian-source-binary"
lintian --fail-on error "${DSC}" "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian-source-binary.log"

STAGE="consumer-runtime-closure"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  "${KCORE_DEBS[@]}" "${KWINDOW_DEBS[@]}" "${DEBS[@]}" |& tee "${EVIDENCE_DIR}/consumer-runtime-install.log"
sudo apt-get check |& tee "${EVIDENCE_DIR}/consumer-runtime-check.log"
for pair in "libkf6coreaddons-dev:${KCORE_VERSION}" "libkf6windowsystem-dev:${KWINDOW_VERSION}" "libkf6authcore6:${DEBIAN_VERSION}"; do
  pkg="${pair%%:*}"; expected="${pair#*:}"
  [[ "$(dpkg-query -W -f='${Version}' "${pkg}")" == "${expected}" ]]
done

STAGE="consumer-smoke"
CONSUMER_ROOT="${WORK_DIR}/consumer-root"; CONSUMER_BUILD="${WORK_DIR}/consumer-build"
mkdir -p "${CONSUMER_ROOT}"
for deb in "${KCORE_DEBS[@]}" "${KWINDOW_DEBS[@]}" "${DEBS[@]}"; do dpkg-deb -x "${deb}" "${CONSUMER_ROOT}"; done
cmake -S "${CONSUMER_META}" -B "${CONSUMER_BUILD}" -GNinja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="${CONSUMER_ROOT}/usr" |& tee "${EVIDENCE_DIR}/consumer-configure.log"
cmake --build "${CONSUMER_BUILD}" --verbose |& tee "${EVIDENCE_DIR}/consumer-build.log"
MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
LD_LIBRARY_PATH="${CONSUMER_ROOT}/usr/lib/${MULTIARCH}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" "${CONSUMER_BUILD}/kauth-consumer" |& tee "${EVIDENCE_DIR}/consumer-run.log"

STAGE="dag-pass-evidence"
{
 echo "node=kauth"; echo "tier=2"; echo "state=PASS"; echo "upstream_version=${UPSTREAM_VERSION}"; echo "debian_version=${DEBIAN_VERSION}"
 echo "ecm_predecessor=${ECM_VERSION}"; echo "kcoreaddons_predecessor=${KCORE_VERSION}"; echo "kwindowsystem_predecessor=${KWINDOW_VERSION}"
 echo "backend=POLKITQT6-1"; echo "helper_backend=DBUS"; echo "source_sha256=${UPSTREAM_SHA256}"
 echo "tests=PASS-via-sbuild-nonzero-ctest"; echo "lintian=PASS-source-and-binary"; echo "abi_soname=${SONAME}"
 echo "abi_export_count=${EXPORT_COUNT}"; echo "symbols_reference=debian-6.30.0-1-pinned"; echo "consumer_smoke=PASS"; echo "apt_check=PASS"; echo "development_contract=PASS"; echo "downstream_eligible=yes"
} > "${EVIDENCE_DIR}/dag-node.txt"
STATE="PASS"; STAGE="complete"
echo "KDE Tier 2 Batch 1 node KAuth: PASS"
