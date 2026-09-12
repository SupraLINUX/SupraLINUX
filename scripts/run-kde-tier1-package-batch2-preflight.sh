#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAMPAIGN="${ROOT}/manifests/kde-tier1-package-campaign-batch2.json"
NODE="${1:-}"
if [[ -z "${NODE}" ]]; then
    echo "Usage: $0 <node>" >&2
    exit 2
fi

eval "$(
python3 - "${CAMPAIGN}" "${NODE}" <<'PY'
import json
import shlex
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
node_id = sys.argv[2]
node = data.get("nodes", {}).get(node_id)
if not isinstance(node, dict):
    raise SystemExit(f"Unknown campaign node: {node_id}")
symbols = node["symbols"]
shared = data["shared_predecessors"]
signing = data["shared_packaging_inputs"]["signing_key"]
values = {
    "UPSTREAM_VERSION": node["upstream_version"],
    "SOURCE_PACKAGE": node["source_package"],
    "DEBIAN_VERSION": node["package_version"],
    "UPSTREAM_URL": node["source_url"],
    "UPSTREAM_SHA256": node["source_sha256"],
    "SYMBOLS_FILE": symbols["file"],
    "SYMBOLS_REFERENCE_SHA256": symbols["sha256"],
    "SYMBOLS_REFERENCE_TREE": symbols["tree_provider"],
    "SYMBOLS_REVIEW_PATCH": symbols.get("review_patch", ""),
    "SYMBOLS_REVIEW_PATCH_SHA256": symbols.get("review_patch_sha256", ""),
    "SYMBOLS_REVIEWED_SHA256": symbols.get("reviewed_sha256", ""),
    "COPYRIGHT_REFERENCE_SHA256": node["copyright"]["sha256"],
    "SIGNING_KEY_SHA256": signing["sha256"],
    "RUNTIME_PACKAGE": node["runtime_package"],
    "SONAME": node["soname"],
    "CONSUMER_RUN": node["consumer_run"],
    "ECM_VERSION": shared["extra_cmake_modules"]["version"],
    "ECM_DEB_SHA256": shared["extra_cmake_modules"]["deb_sha256"],
    "REFERENCE_SNAPSHOT_SHA256": shared["packaging_trees"]["snapshot_json_sha256"],
}
for key, value in values.items():
    print(f"{key}={shlex.quote(str(value))}")
PY
)"

PACKAGE_META="${ROOT}/packages/kde/${NODE}/debian"
CONSUMER_META="${ROOT}/packages/kde/${NODE}/consumer"
WORK_DIR="${ROOT}/.work/kde-tier1-package-preflight/${NODE}"
SOURCE_WORK="${WORK_DIR}/source"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-package-preflight/${NODE}"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar"
MIRROR="${SBUILD_MIRROR:-http://azure.archive.ubuntu.com/ubuntu}"

: "${ECM_ARTIFACT_DIR:?ECM_ARTIFACT_DIR must point at the retained ECM PASS artifact}"
: "${TIER1_REFERENCE_DIR:?TIER1_REFERENCE_DIR must point at retained generic packaging-tree evidence}"

STATE="FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${SOURCE_WORK}" "${OUT_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"

write_result() {
    local rc="$?"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT_JSON}" "${NODE}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" "${UPSTREAM_VERSION}" "${DEBIAN_VERSION}" <<'PY'
import json
import sys
from pathlib import Path

path, node, state, rc, stage, started, finished, version, debian_version = sys.argv[1:]
Path(path).write_text(json.dumps({
    "node": node,
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": False,
    "runner_class": "github-hosted-ubuntu-26.04",
    "upstream_authority": "kde-upstream",
    "upstream_version": version,
    "debian_version": debian_version,
    "ecm_predecessor": "6.30.0-0supralinux3",
    "claim": "hosted-clean-package-preflight",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "=== SupraLINUX KDE Tier 1 batch: ${NODE} ${UPSTREAM_VERSION} (${DEBIAN_VERSION}) ==="

STAGE="campaign-validation"
python3 - "${CAMPAIGN}" "${NODE}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
node = data["nodes"][sys.argv[2]]
if node["state"] not in {"prepared-pending-build", "remediation-pending-build"}:
    raise SystemExit(f"Node must be prepared/remediation-pending-build before attempt, got {node['state']}")
if data["authority"] != "kde-upstream" or data["frameworks_series"] != "6.30.0":
    raise SystemExit("Campaign authority/version mismatch")
PY
test -d "${PACKAGE_META}"
test -s "${CONSUMER_META}/CMakeLists.txt"
test -s "${CONSUMER_META}/main.cpp"
test -s "${PACKAGE_META}/upstream/signing-key.asc"
printf '%s  %s\n' "${SIGNING_KEY_SHA256}" "${PACKAGE_META}/upstream/signing-key.asc" | sha256sum --check --strict

STAGE="retained-input-validation"
ECM_DEB="$(find "${ECM_ARTIFACT_DIR}" -maxdepth 2 -type f -name "extra-cmake-modules_${ECM_VERSION}_all.deb" -print -quit)"
if [[ -z "${ECM_DEB}" || ! -s "${ECM_DEB}" ]]; then
    echo "Retained ECM PASS .deb not found under ${ECM_ARTIFACT_DIR}" >&2
    exit 1
fi
printf '%s  %s\n' "${ECM_DEB_SHA256}" "${ECM_DEB}" | sha256sum --check --strict
[[ "$(dpkg-deb -f "${ECM_DEB}" Package)" == "extra-cmake-modules" ]]
[[ "$(dpkg-deb -f "${ECM_DEB}" Version)" == "${ECM_VERSION}" ]]
sha256sum "${ECM_DEB}" > "${EVIDENCE_DIR}/ecm-predecessor-sha256.txt"

REFERENCE_SNAPSHOT="${TIER1_REFERENCE_DIR}/snapshot.json"
test -s "${REFERENCE_SNAPSHOT}"
printf '%s  %s\n' "${REFERENCE_SNAPSHOT_SHA256}" "${REFERENCE_SNAPSHOT}" | sha256sum --check --strict
python3 - "${REFERENCE_SNAPSHOT}" "${NODE}" "${SYMBOLS_REFERENCE_TREE}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
node = sys.argv[2]
provider = sys.argv[3]
if data.get("authority") is not False or data.get("role") != "packaging-reference-trees-only":
    raise SystemExit("Generic packaging-tree artifact has wrong authority/role")
if node not in data.get("nodes", {}):
    raise SystemExit(f"Generic packaging-tree artifact lacks node {node}")
if provider not in data["nodes"][node]:
    raise SystemExit(f"Generic packaging-tree artifact lacks provider {provider} for {node}")
PY

SYMBOLS_REFERENCE="${TIER1_REFERENCE_DIR}/trees/${SYMBOLS_REFERENCE_TREE}/${NODE}/debian/${SYMBOLS_FILE}"
test -s "${SYMBOLS_REFERENCE}"
printf '%s  %s\n' "${SYMBOLS_REFERENCE_SHA256}" "${SYMBOLS_REFERENCE}" | sha256sum --check --strict
sha256sum "${SYMBOLS_REFERENCE}" > "${EVIDENCE_DIR}/symbols-reference-sha256.txt"
printf 'provider=%s\n' "${SYMBOLS_REFERENCE_TREE}" > "${EVIDENCE_DIR}/symbols-reference-provider.txt"

COPYRIGHT_REFERENCE="${TIER1_REFERENCE_DIR}/trees/debian/${NODE}/debian/copyright"
test -s "${COPYRIGHT_REFERENCE}"
printf '%s  %s\n' "${COPYRIGHT_REFERENCE_SHA256}" "${COPYRIGHT_REFERENCE}" | sha256sum --check --strict
sha256sum "${COPYRIGHT_REFERENCE}" > "${EVIDENCE_DIR}/copyright-reference-sha256.txt"
sha256sum "${PACKAGE_META}/upstream/signing-key.asc" > "${EVIDENCE_DIR}/signing-key-sha256.txt"

STAGE="host-validation"
. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    echo "Expected Ubuntu 26.04; got ${PRETTY_NAME}" >&2
    exit 1
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    binutils \
    ca-certificates \
    cmake \
    curl \
    dbus-daemon \
    devscripts \
    dpkg-dev \
    g++ \
    lintian \
    mmdebstrap \
    ninja-build \
    pkg-config \
    patch \
    qt6-base-dev \
    sbuild \
    uidmap \
    ubuntu-keyring \
    xz-utils

if ! grep -q "^${USER}:" /etc/subuid; then
    sudo usermod --add-subuids 100000-165535 "${USER}"
fi
if ! grep -q "^${USER}:" /etc/subgid; then
    sudo usermod --add-subgids 100000-165535 "${USER}"
fi
unshare --user --map-auto true

{
    cat /etc/os-release
    echo
    uname -a
    echo
    sbuild --version
    mmdebstrap --version
    cmake --version | head -1
    dpkg-query -W -f='${Package}\t${Version}\n' qt6-base-dev sbuild mmdebstrap lintian
} > "${EVIDENCE_DIR}/host.txt"

STAGE="upstream-source"
ORIG_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 --output "${ORIG_TARBALL}" "${UPSTREAM_URL}"
printf '%s  %s\n' "${UPSTREAM_SHA256}" "${ORIG_TARBALL}" | sha256sum --check --strict
sha256sum "${ORIG_TARBALL}" > "${EVIDENCE_DIR}/upstream-source-sha256.txt"

tar -xJf "${ORIG_TARBALL}" -C "${SOURCE_WORK}"
EXTRACTED="${SOURCE_WORK}/${NODE}-${UPSTREAM_VERSION}"
SOURCE_DIR="${SOURCE_WORK}/${SOURCE_PACKAGE}-${UPSTREAM_VERSION}"
test -d "${EXTRACTED}"
mv "${EXTRACTED}" "${SOURCE_DIR}"
cp -a "${PACKAGE_META}" "${SOURCE_DIR}/debian"
cp -a "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}"
if [[ -n "${SYMBOLS_REVIEW_PATCH}" ]]; then
    REVIEW_PATCH="${PACKAGE_META}/${SYMBOLS_REVIEW_PATCH}"
    test -s "${REVIEW_PATCH}"
    printf '%s  %s\n' "${SYMBOLS_REVIEW_PATCH_SHA256}" "${REVIEW_PATCH}" | sha256sum --check --strict
    patch --batch --forward "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" "${REVIEW_PATCH}"
    printf '%s  %s\n' "${SYMBOLS_REVIEWED_SHA256}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" | sha256sum --check --strict
    sha256sum "${REVIEW_PATCH}" > "${EVIDENCE_DIR}/symbols-review-patch-sha256.txt"
    sha256sum "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" > "${EVIDENCE_DIR}/reviewed-symbols-sha256.txt"
fi
cp -a "${COPYRIGHT_REFERENCE}" "${SOURCE_DIR}/debian/copyright"
python3 - "${SOURCE_DIR}/debian/copyright" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
start = next((i for i, line in enumerate(lines) if line.strip() == "Files: debian/*"), None)
if start is None:
    raise SystemExit("Reference copyright lacks Files: debian/* stanza")
license_line = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("License:")), None)
if license_line is None:
    raise SystemExit("Reference debian/* stanza lacks License field")
if not any("SupraLINUX Project" in line for line in lines[start:license_line]):
    lines.insert(license_line, "           2026, SupraLINUX Project")
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
chmod +x "${SOURCE_DIR}/debian/rules"

sha256sum "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" > "${EVIDENCE_DIR}/injected-symbols-sha256.txt"
sha256sum "${SOURCE_DIR}/debian/copyright" > "${EVIDENCE_DIR}/injected-copyright-sha256.txt"
if [[ -z "${SYMBOLS_REVIEW_PATCH}" ]]; then
    cmp -s "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}"
else
    [[ "$(sha256sum "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" | awk '{print $1}')" == "${SYMBOLS_REVIEWED_SHA256}" ]]
fi
grep -Fq "2026, SupraLINUX Project" "${SOURCE_DIR}/debian/copyright"

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
mmdebstrap \
    --mode=unshare \
    --variant=buildd \
    --architectures=amd64 \
    --components=main,universe \
    --skip=output/mknod \
    --format=tar \
    resolute \
    "${CHROOT_TARBALL}" \
    "${MIRROR}" |& tee "${EVIDENCE_DIR}/rootfs.log"

test -s "${CHROOT_TARBALL}"
sha256sum "${CHROOT_TARBALL}" > "${EVIDENCE_DIR}/rootfs-sha256.txt"

STAGE="sbuild"
sbuild \
    --verbose \
    --chroot-mode=unshare \
    --dist=resolute \
    --arch=amd64 \
    --arch-all \
    --extra-package="${ECM_DEB}" \
    --build-dir="${OUT_DIR}" \
    "${DSC}" |& tee "${EVIDENCE_DIR}/sbuild.log"

mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)

mapfile -t EXPECTED_PACKAGES < <(python3 - "${CAMPAIGN}" "${NODE}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for item in data["nodes"][sys.argv[2]]["binary_contracts"]:
    print(item["name"])
PY
)

if (( ${#DEBS[@]} != ${#EXPECTED_PACKAGES[@]} || ${#CHANGES[@]} == 0 || ${#BUILDINFO[@]} == 0 )); then
    printf 'Unexpected build artifact count: deb=%d expected=%d changes=%d buildinfo=%d\n' \
        "${#DEBS[@]}" "${#EXPECTED_PACKAGES[@]}" "${#CHANGES[@]}" "${#BUILDINFO[@]}" >&2
    exit 1
fi

if ! grep -Fq "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}"; then
    echo "Buildinfo does not prove retained ECM ${ECM_VERSION}" >&2
    exit 1
fi
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/ecm-buildinfo-proof.txt"

STAGE="artifact-contract"
declare -A DEB_BY_PACKAGE=()
for deb in "${DEBS[@]}"; do
    package="$(dpkg-deb -f "${deb}" Package)"
    DEB_BY_PACKAGE["${package}"]="${deb}"
    if [[ "$(dpkg-deb -f "${deb}" Version)" != "${DEBIAN_VERSION}" ]]; then
        echo "Unexpected ${package} version: $(dpkg-deb -f "${deb}" Version)" >&2
        exit 1
    fi
done
for package in "${EXPECTED_PACKAGES[@]}"; do
    if [[ -z "${DEB_BY_PACKAGE[$package]:-}" ]]; then
        echo "Expected binary package missing: ${package}" >&2
        exit 1
    fi
done

python3 - "${CAMPAIGN}" "${NODE}" "${OUT_DIR}" "${DEBIAN_VERSION}" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

campaign, node_id, out_dir, version = sys.argv[1:]
data = json.loads(Path(campaign).read_text(encoding="utf-8"))
node = data["nodes"][node_id]
debs = {}
for deb in Path(out_dir).glob("*.deb"):
    name = subprocess.check_output(["dpkg-deb", "-f", str(deb), "Package"], text=True).strip()
    debs[name] = deb

def field(path: Path, name: str) -> str:
    proc = subprocess.run(["dpkg-deb", "-f", str(path), name], text=True, capture_output=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""

def normalized_multi_arch(path: Path):
    value = field(path, "Multi-Arch")
    return None if value in {"", "no"} else value

for contract in node["binary_contracts"]:
    name = contract["name"]
    path = debs.get(name)
    if path is None:
        raise SystemExit(f"Missing binary {name}")
    architecture = field(path, "Architecture")
    if architecture != contract["architecture"]:
        raise SystemExit(f"{name}: architecture {architecture!r} != {contract['architecture']!r}")
    multi = normalized_multi_arch(path)
    if multi != contract["multi_arch"]:
        raise SystemExit(f"{name}: normalized Multi-Arch {multi!r} != {contract['multi_arch']!r}")
    for compatibility_field in ("Provides", "Breaks", "Replaces", "Conflicts"):
        if field(path, compatibility_field):
            raise SystemExit(f"{name}: unexpected {compatibility_field}={field(path, compatibility_field)}")

dev = debs[node["development_package"]]
depends = field(dev, "Depends")
recommends = field(dev, "Recommends")
if f"{node['runtime_package']} (= {version})" not in depends:
    raise SystemExit("Development package does not pin exact runtime version")
if "qt6-base-dev (>= 6.9.0~)" not in depends:
    raise SystemExit("Development package lost Qt >=6.9 contract")
if f"{node['documentation_package']} (= {version})" not in recommends:
    raise SystemExit("Development package does not recommend exact documentation version")
PY

RUNTIME_DEB="${DEB_BY_PACKAGE[$RUNTIME_PACKAGE]}"

{
    for deb in "${DEBS[@]}"; do
        echo "### $(basename "${deb}")"
        dpkg-deb -I "${deb}"
        echo
    done
} > "${EVIDENCE_DIR}/binary-control.txt"
{
    for deb in "${DEBS[@]}"; do
        echo "### $(basename "${deb}")"
        dpkg-deb -c "${deb}"
        echo
    done
} > "${EVIDENCE_DIR}/binary-filelists.txt"

STAGE="abi-check"
RUNTIME_ROOT="${WORK_DIR}/runtime-root"
mkdir -p "${RUNTIME_ROOT}"
dpkg-deb -x "${RUNTIME_DEB}" "${RUNTIME_ROOT}"
LIB_PATH="$(find "${RUNTIME_ROOT}" -type f -name "${SONAME}.*" -print -quit)"
test -n "${LIB_PATH}"
readelf -d "${LIB_PATH}" > "${EVIDENCE_DIR}/readelf-dynamic.txt"
grep -Fq "Library soname: [${SONAME}]" "${EVIDENCE_DIR}/readelf-dynamic.txt"

STAGE="artifact-capture"
sha256sum "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${EVIDENCE_DIR}/"
cp -a "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" "${EVIDENCE_DIR}/"

STAGE="lintian"
lintian --fail-on error "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian.log"

STAGE="consumer-smoke"
CONSUMER_ROOT="${WORK_DIR}/consumer-root"
CONSUMER_BUILD="${WORK_DIR}/consumer-build"
mkdir -p "${CONSUMER_ROOT}"
for deb in "${DEBS[@]}"; do
    dpkg-deb -x "${deb}" "${CONSUMER_ROOT}"
done
cmake -S "${CONSUMER_META}" -B "${CONSUMER_BUILD}" -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="${CONSUMER_ROOT}/usr" |& tee "${EVIDENCE_DIR}/consumer-configure.log"
cmake --build "${CONSUMER_BUILD}" --verbose |& tee "${EVIDENCE_DIR}/consumer-build.log"

CONSUMER_BINARY="${CONSUMER_BUILD}/${NODE}-consumer"
MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
if [[ "${CONSUMER_RUN}" == "dbus-session" ]]; then
    LD_LIBRARY_PATH="${CONSUMER_ROOT}/usr/lib/${MULTIARCH}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" \
        dbus-run-session -- "${CONSUMER_BINARY}" |& tee "${EVIDENCE_DIR}/consumer-run.log"
else
    LD_LIBRARY_PATH="${CONSUMER_ROOT}/usr/lib/${MULTIARCH}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" \
        "${CONSUMER_BINARY}" |& tee "${EVIDENCE_DIR}/consumer-run.log"
fi

STAGE="dag-pass-evidence"
{
    echo "node=${NODE}"
    echo "state=PASS"
    echo "upstream_version=${UPSTREAM_VERSION}"
    echo "debian_version=${DEBIAN_VERSION}"
    echo "ecm_predecessor=${ECM_VERSION}"
    echo "source_sha256=${UPSTREAM_SHA256}"
    echo "symbols_reference_tree=${SYMBOLS_REFERENCE_TREE}"
    echo "symbols_baseline_sha256=${SYMBOLS_REFERENCE_SHA256}"
    echo "signing_key_sha256=${SIGNING_KEY_SHA256}"
    echo "tests=PASS-via-sbuild"
    echo "lintian=PASS-errors"
    echo "abi_soname=${SONAME}"
    echo "consumer_smoke=PASS"
    echo "downstream_eligible=yes"
} > "${EVIDENCE_DIR}/dag-node.txt"

STATE="PASS"
STAGE="complete"
echo "KDE Tier 1 node ${NODE}: PASS"
