#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SNAPSHOT="20260829T022000Z"
SLICE_ROOT="${AURORA_KSQ_LOCAL_SLICE_ROOT:-/opt/supralinux/archive/${SNAPSHOT}}"

[[ "$(id -u)" -eq 0 ]] || { echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: must run as root inside builder" >&2; exit 1; }
. /etc/os-release
[[ "${VERSION_CODENAME:-}" == "resolute" ]] || { echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: expected Resolute" >&2; exit 1; }
[[ "$(dpkg --print-architecture)" == "amd64" ]] || { echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: expected amd64" >&2; exit 1; }
[[ -f "${SLICE_ROOT}/COMPLETE" && -f "${SLICE_ROOT}/aurora-local.sources" ]] || { echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: snapshot slice incomplete" >&2; exit 1; }

grep -Eq '^supralinux-ksq-unshare( \(enforce\))?$' /proc/self/attr/current || {
  echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: scoped AppArmor profile not enforcing" >&2
  exit 1
}
cap_eff="$(awk '/^CapEff:/ {print $2}' /proc/self/status)"
cap_eff_val=$((16#${cap_eff}))
(( (cap_eff_val & (1 << 21)) == 0 )) || { echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: outer CAP_SYS_ADMIN present" >&2; exit 1; }
[[ "$(stat -f -c %T /proc)" == proc ]] || { echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: /proc is not procfs" >&2; exit 1; }
[[ "$(findmnt -R /proc -n -o TARGET | wc -l)" -eq 1 ]] || { echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: Docker /proc submounts remain" >&2; exit 1; }
if find /sys/class/net -mindepth 1 -maxdepth 1 ! -name lo -print -quit 2>/dev/null | grep -q .; then
  echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: non-loopback network interface exists" >&2
  exit 1
fi

rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*
cp "${SLICE_ROOT}/aurora-local.sources" /etc/apt/sources.list.d/aurora-local.sources
cat >/etc/apt/apt.conf.d/99supralinux-local-only <<'EOF_APT'
Acquire::http::Proxy "http://127.0.0.1:9/";
Acquire::https::Proxy "http://127.0.0.1:9/";
Acquire::Retries "0";
EOF_APT
if grep -RIE 'https?://' /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null; then
  echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: remote APT source active" >&2
  exit 1
fi

apt-get -o APT::Update::Error-Mode=any update
apt-get --no-install-recommends install -y \
  python3 sudo sbuild mmdebstrap uidmap zstd devscripts dpkg-dev apt-utils \
  ca-certificates ubuntu-keyring gzip xz-utils diffutils libcap2-bin build-essential

dpkg-query -W -f='${Package}\t${Version}\n' \
  sbuild libsbuild-perl mmdebstrap uidmap libcap2-bin util-linux dpkg-dev apt-utils ubuntu-keyring \
  | sort > "${ROOT}/build/ksq-1-build-tool-versions.tsv"

build_user=ubuntu
grep -q '^ubuntu:' /etc/subuid || echo 'ubuntu:100000:65536' >> /etc/subuid
grep -q '^ubuntu:' /etc/subgid || echo 'ubuntu:100000:65536' >> /etc/subgid
bash "${ROOT}/scripts/ci/configure-ksq-uidmap-filecaps.sh"
su -s /bin/bash "${build_user}" -c 'unshare --map-auto --map-user=65536 --map-group=65536 --keep-caps --mount --pid --uts --ipc --fork true'

python3 "${ROOT}/scripts/ci/restore-ksq-0-certified-evidence.py" \
  --slice-root "${SLICE_ROOT}" --workspace "${ROOT}"
bash "${ROOT}/scripts/ci/validate-kde-stack-source-manifests.sh"
python3 "${ROOT}/scripts/ci/validate-kde-stack-roots.py"
AURORA_KSQ_LOCAL_SLICE_ROOT="${SLICE_ROOT}" bash "${ROOT}/scripts/ci/prepare-ksq-1-local-apt-metadata.sh"
python3 "${ROOT}/scripts/ci/generate-kde-build-closure.py"

cmp -s "${ROOT}/build/ksq-0/build-order.tsv" "${ROOT}/build/ksq-0/canonical/build-order.tsv" || {
  echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: regenerated local build order differs from certified KSQ-0" >&2
  diff -u "${ROOT}/build/ksq-0/canonical/build-order.tsv" "${ROOT}/build/ksq-0/build-order.tsv" >&2 || true
  exit 1
}
cmp -s "${ROOT}/build/ksq-0/closure-status.env" "${ROOT}/build/ksq-0/canonical/closure-status.env" || {
  echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: regenerated closure status differs from certified KSQ-0" >&2
  diff -u "${ROOT}/build/ksq-0/canonical/closure-status.env" "${ROOT}/build/ksq-0/closure-status.env" >&2 || true
  exit 1
}

# The source-audit bytes were restored from the certified KSQ-0 artifact embedded
# in the immutable slice. Do not re-query Debian Snapshot or reopen KSQ-0 here.
[[ -f "${ROOT}/build/ksq-0/source-audit/downloads/wayland-protocols_1.48-1.dsc" ]] || {
  echo "AURORA_KSQ_1_LOCAL_RUNNER_FAILURE: certified Debian source audit missing" >&2
  exit 1
}

chmod -R a+rX,a+w "${ROOT}/build"
AURORA_KSQ_LOCAL_SLICE_ROOT="${SLICE_ROOT}" su -s /bin/bash "${build_user}" -c \
  "cd '${ROOT}' && AURORA_KSQ_LOCAL_SLICE_ROOT='${SLICE_ROOT}' bash scripts/ci/prepare-ksq-1-local-build-environment.sh"

{
  echo "AURORA_KSQ_1_LOCAL_RUNNER_SNAPSHOT=${SNAPSHOT}"
  echo "AURORA_KSQ_1_LOCAL_RUNNER_SLICE=${SLICE_ROOT}"
  echo "AURORA_KSQ_1_LOCAL_RUNNER_BUILD_ORDER_SHA256=$(sha256sum "${ROOT}/build/ksq-0/build-order.tsv" | awk '{print $1}')"
  echo "AURORA_KSQ_1_LOCAL_RUNNER_REMOTE_FALLBACK=forbidden"
  echo "AURORA_KSQ_1_LOCAL_RUNNER_SUCCESS"
} | tee "${ROOT}/build/ksq-1-local-runner-status.env"
