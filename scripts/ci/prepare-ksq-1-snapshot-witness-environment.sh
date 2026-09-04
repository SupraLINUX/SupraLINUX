#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-${ROOT}/build/ksq-1/snapshot-witness/environment-evidence}"
SNAPSHOT_ENV="${ROOT}/tests/kde-stack/apt-metadata-snapshot.env"

fail() {
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_ENV_FAILURE: $*" >&2
    exit 1
}

. /etc/os-release
[[ "${VERSION_CODENAME:-}" == "resolute" ]] || fail "runner is not Resolute"
[[ "$(dpkg --print-architecture)" == "amd64" ]] || fail "runner is not amd64"
[[ -f "${SNAPSHOT_ENV}" ]] || fail "snapshot manifest missing"
# shellcheck disable=SC1090
. "${SNAPSHOT_ENV}"
SNAPSHOT="${AURORA_KSQ_0_APT_SNAPSHOT:?missing snapshot identity}"
[[ "${SNAPSHOT}" == "20260829T022000Z" ]] || fail "unexpected snapshot ${SNAPSHOT}"

for cmd in sbuild mmdebstrap newuidmap newgidmap zstd dpkg-buildpackage; do
    command -v "${cmd}" >/dev/null || fail "missing ${cmd}"
done

mkdir -p "${OUT}"
dpkg-query -W -f='${Package}\t${Version}\n' \
    apt sbuild libsbuild-perl mmdebstrap uidmap util-linux apparmor ubuntu-keyring \
    | sort > "${OUT}/toolchain.tsv"
grep -q $'^apt\t3.2.0$' "${OUT}/toolchain.tsv"
grep -q $'^sbuild\t0.91.2ubuntu3$' "${OUT}/toolchain.tsv"
grep -q $'^libsbuild-perl\t0.91.2ubuntu3$' "${OUT}/toolchain.tsv"
grep -q $'^mmdebstrap\t1.5.7-3$' "${OUT}/toolchain.tsv"
grep -q $'^uidmap\t1:4.17.4-2ubuntu3$' "${OUT}/toolchain.tsv"

# Selected native architecture: stock Resolute uidmap/AppArmor, no local file-capability rewrite.
[[ "$(stat -c '%a' /usr/bin/newuidmap)" == "4755" ]] || fail "newuidmap mode drifted"
[[ "$(stat -c '%a' /usr/bin/newgidmap)" == "4755" ]] || fail "newgidmap mode drifted"
[[ -z "$(getcap /usr/bin/newuidmap /usr/bin/newgidmap || true)" ]] || fail "uidmap file capabilities unexpectedly present"

sbuild_profile="$(dpkg -L apparmor | grep -E '/etc/apparmor\.d/(usr\.bin\.)?sbuild$' | head -n1)"
mmdebstrap_profile="$(dpkg -L apparmor | grep -E '/etc/apparmor\.d/(usr\.bin\.)?mmdebstrap$' | head -n1)"
[[ -s "${sbuild_profile}" ]] || fail "official sbuild AppArmor profile missing"
[[ -s "${mmdebstrap_profile}" ]] || fail "official mmdebstrap AppArmor profile missing"
grep -q 'userns,' "${sbuild_profile}" || fail "sbuild profile lacks userns rule"
grep -q 'userns,' "${mmdebstrap_profile}" || fail "mmdebstrap profile lacks userns rule"

bash "${ROOT}/scripts/ci/validate-kde-stack-source-manifests.sh"
python3 "${ROOT}/scripts/ci/validate-kde-stack-roots.py"
bash "${ROOT}/scripts/ci/prepare-kde-stack-apt-metadata.sh" \
    2>&1 | tee "${OUT}/apt-metadata.log"
python3 "${ROOT}/scripts/ci/generate-kde-build-closure.py"
bash "${ROOT}/scripts/ci/audit-kde-stack-source-selections.sh"

# The certified order and snapshot identity must not drift merely because this is a witness run.
[[ "$(sha256sum "${ROOT}/build/ksq-0/build-order.tsv" | awk '{print $1}')" == \
   "9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88" ]] \
    || fail "build order identity drifted"
# shellcheck disable=SC1091
. "${ROOT}/build/ksq-0/closure-status.env"
[[ "${AURORA_KSQ_0_CLOSURE_STATUS}" == "COMPLETE" ]] || fail "KSQ-0 closure is not complete"
[[ "${AURORA_KSQ_0_CLOSURE_UNRESOLVED}" == "0" ]] || fail "KSQ-0 closure has unresolved nodes"
[[ "${AURORA_KSQ_0_CLOSURE_SOURCES}" == "101" ]] || fail "unexpected source count"
[[ "${AURORA_KSQ_0_CLOSURE_BUILD_ORDERED}" == "101" ]] || fail "unexpected ordered source count"
[[ "${AURORA_KSQ_0_APT_SNAPSHOT}" == "${SNAPSHOT}" ]] || fail "closure snapshot drifted"

bash "${ROOT}/scripts/ci/prepare-ksq-1-build-environment.sh" \
    2>&1 | tee "${OUT}/build-environment.log"
# shellcheck disable=SC1091
. "${ROOT}/build/ksq-1/environment/build-environment.env"
[[ "${AURORA_KSQ_1_BUILD_ENV_SNAPSHOT}" == "${SNAPSHOT}" ]] || fail "build environment snapshot drifted"
[[ "${AURORA_KSQ_1_BUILD_ENV_ARCH}" == "amd64" ]] || fail "build environment architecture drifted"
[[ "${AURORA_KSQ_1_BUILD_ENV_BACKEND}" == "unshare" ]] || fail "build environment backend drifted"
[[ -s "${AURORA_KSQ_1_BUILD_ENV_TARBALL}" ]] || fail "buildd tarball missing"

# Materialize the full tar listing before searching it. A grep -q consumer in a
# tar pipeline under pipefail can close early and make tar report SIGPIPE even
# though the sought path exists.
tar_paths="${OUT}/buildd-tar-paths.txt"
tar --zstd -tf "${AURORA_KSQ_1_BUILD_ENV_TARBALL}" > "${tar_paths}"
grep -q '^\./etc/apt/' "${tar_paths}" || fail "buildd rootfs has no apt configuration"
inspect="${OUT}/inspect"
rm -rf "${inspect}"
mkdir -p "${inspect}"
tar --zstd -xf "${AURORA_KSQ_1_BUILD_ENV_TARBALL}" -C "${inspect}" ./etc/apt

grep -RqsF "https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}/" "${inspect}/etc/apt" \
    || fail "timestamped Ubuntu snapshot URI absent from buildd rootfs"
if grep -RqsE '(^|[/.:])(archive\.ubuntu\.com|security\.ubuntu\.com)([/:]|$)' "${inspect}/etc/apt"; then
    grep -RnsE 'archive\.ubuntu\.com|security\.ubuntu\.com' "${inspect}/etc/apt" >&2 || true
    fail "live Ubuntu archive leaked into witness buildd rootfs"
fi

sha256sum "${AURORA_KSQ_1_BUILD_ENV_TARBALL}" > "${OUT}/buildd.sha256"
{
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_ENV_STATUS=PASS"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_SNAPSHOT=${SNAPSHOT}"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_APT=3.2.0"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_SBUILD=0.91.2ubuntu3"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_MMDEBSTRAP=1.5.7-3"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_ARCH=amd64"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_ARCH_VARIANTS=disabled"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_INSTALL_RECOMMENDS=default"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_BUILD_NETWORK=disabled-by-sbuild"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_DEPENDENCY_TRANSPORT=timestamped-snapshot"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_UIDMAP_MODE=stock-setuid"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_CUSTOM_APPARMOR=0"
    echo "AURORA_KSQ_1_SNAPSHOT_WITNESS_DOCKER=0"
} > "${OUT}/status.env"

cat "${OUT}/status.env"
echo AURORA_KSQ_1_SNAPSHOT_WITNESS_ENV_SUCCESS
