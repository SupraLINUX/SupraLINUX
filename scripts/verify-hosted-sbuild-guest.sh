#!/usr/bin/env bash
# Disposable guest mechanism check. Base QCOW2 and certified source fixture are read-only.
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT/.work/hosted-sbuild-guest"
BASE="$ROOT/.work/hosted-ubuntu-guest/base"
IMAGE="$BASE/resolute-amd64.qcow2"
META="$BASE/snapshot.json"
EVID="$WORK/evidence"
FIXTURE="$ROOT/tests/fixtures/hosted-ubuntu-guest"
CHECK="$ROOT/scripts/hosted-ubuntu-guest-snapshot.py"
test "${RUNNER_ENVIRONMENT:-}" = github-hosted
test "$(git -C "$ROOT" rev-parse HEAD)" = "$SUPRALINUX_EXPECTED_HEAD"
test -r /dev/kvm && test -w /dev/kvm
test -f "$IMAGE" && test -f "$META"
mkdir -p "$EVID" "$WORK/overlays"
python3 "$CHECK" verify "$IMAGE" "$META"
scratch=$(mktemp -d "$WORK/fixture.XXXXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
cp -a "$FIXTURE/." "$scratch/"
cp "$ROOT/scripts/probe-hosted-sbuild-backend.sh" "$scratch/debian/tests/backend-probe"
chmod 0755 "$scratch/debian/tests/backend-probe"
cat > "$scratch/debian/tests/control" <<'EOF'
Tests: guest-smoke
Depends: python3, ubuntu-keyring, sbuild, mmdebstrap, dpkg-dev, debhelper-compat (= 13), uidmap
Restrictions: isolation-machine, needs-internet
EOF
cat >> "$scratch/debian/tests/guest-smoke" <<'EOF'
test "$(id -u)" -ne 0
echo SUPRALINUX_SBUILD_GUEST_NONROOT_EXECUTION
bash "$(dirname "$0")/backend-probe" /var/tmp/supralinux-sbuild-guest-diagnostic guest
grep -Fxq 'rootfs=PASS' /var/tmp/supralinux-sbuild-guest-diagnostic/result.txt
grep -Fxq 'host_sbuild=PASS' /var/tmp/supralinux-sbuild-guest-diagnostic/result.txt
echo SUPRALINUX_SBUILD_GUEST_MECHANISM_PASS
EOF
test "$(dpkg-parsechangelog -l "$scratch/debian/changelog" -S Source)" = supralinux-guest-probe
printf 'scope=guest-sbuild-mechanism-only\nsource_sha=%s\nkde_attempt=false\n' \
  "$SUPRALINUX_EXPECTED_HEAD" > "$EVID/scope.txt"

if ! timeout --signal=TERM --kill-after=30s 32m autopkgtest --no-built-binaries --apt-upgrade \
  --output-dir="$WORK/autopkgtest" "$scratch" \
  -- qemu --cpus=2 --ram-size=2048 --overlay-dir="$WORK/overlays" "$IMAGE" \
  > "$EVID/autopkgtest-console.log" 2>&1; then
  echo 'INFRA_INVALID: hosted guest sbuild backend test failed' > "$EVID/result.txt"
  tail -n 100 "$EVID/autopkgtest-console.log" >&2
  python3 "$CHECK" verify "$IMAGE" "$META"
  exit 1
fi
grep -Eq '^guest-smoke[[:space:]]+PASS$' "$WORK/autopkgtest/summary"
grep -Fq 'SUPRALINUX_SBUILD_GUEST_MECHANISM_PASS' "$EVID/autopkgtest-console.log"
python3 "$CHECK" verify "$IMAGE" "$META"
echo 'GUEST_SBUILD_UNSHARE_MECHANISM_PASS; NO_KDE_PACKAGE_PASS' > "$EVID/result.txt"
cat "$EVID/result.txt"
