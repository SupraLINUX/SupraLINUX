#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT/.work/hosted-ubuntu-guest"
BASE="$WORK/base"
IMAGE="$BASE/resolute-amd64.qcow2"
META="$BASE/snapshot.json"
EVID="$WORK/evidence"
ACTION="$1"
SCRIPT="$ROOT/scripts/hosted-ubuntu-guest-snapshot.py"

test "$RUNNER_ENVIRONMENT" = github-hosted
test "$(git -C "$ROOT" rev-parse HEAD)" = "$SUPRALINUX_EXPECTED_HEAD"
test "$(uname -m)" = x86_64
test "$( . /etc/os-release; echo "$ID:$VERSION_ID" )" = ubuntu:26.04
test -r /dev/kvm && test -w /dev/kvm
case "$ACTION" in prepare|test|seal) ;; *) exit 2 ;; esac
mkdir -p "$BASE" "$EVID" "$WORK/tmp" "$WORK/overlays"
export TMPDIR="$WORK/tmp"

case "$ACTION" in
prepare)
  if [[ "$SUPRALINUX_CACHE_HIT" == true ]]; then
    python3 "$SCRIPT" verify "$IMAGE" "$META"
    echo "Verified milestone cache hit" > "$EVID/snapshot-admission.txt"
  else
    test ! -e "$IMAGE" && test ! -e "$META"
    test "$(df -Pk "$WORK" | awk 'END{print $4}')" -ge 9000000
    if ! timeout -k 30s 45m sudo env TMPDIR="$WORK/tmp" autopkgtest-build-qemu \
       --mirror=http://archive.ubuntu.com/ubuntu \
       --keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg \
       --architecture=amd64 --size=8G --boot=bios --apt-proxy=DIRECT \
       resolute "$IMAGE" > "$EVID/base-build.log" 2>&1; then
      tail -n 80 "$EVID/base-build.log" >&2
      exit 1
    fi
    sudo chown "$(id -u):$(id -g)" "$IMAGE"
    python3 "$SCRIPT" create "$IMAGE" "$META"
    echo "New unsigned-for-release base; awaiting guest test" > "$EVID/snapshot-admission.txt"
  fi
  ;;
test)
  python3 "$SCRIPT" inspect "$IMAGE" "$META"
  FIXTURE="$WORK/source"
  mkdir -p "$FIXTURE/debian/tests"
  cat > "$FIXTURE/debian/control" <<'EOF'
Source: supralinux-guest-probe
Section: misc
Priority: optional
Maintainer: SupraLINUX QA <qa@supralinux.invalid>
Standards-Version: 4.7.0

Package: supralinux-guest-probe
Architecture: all
Description: Disposable integration probe, not a distributed package
 Tests only isolated hosted Ubuntu QEMU infrastructure.
EOF
  cat > "$FIXTURE/debian/tests/control" <<'EOF'
Tests: guest-smoke
Depends: python3, ubuntu-keyring
Restrictions: isolation-machine
EOF
  cat > "$FIXTURE/debian/tests/guest-smoke" <<'EOF'
#!/bin/sh
set -eu
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_ID" = 26.04
test "$VERSION_CODENAME" = resolute
test "$(dpkg --print-architecture)" = amd64
test "$(uname -m)" = x86_64
dpkg-query -W ubuntu-keyring >/dev/null
test -r /usr/share/keyrings/ubuntu-archive-keyring.gpg
printf '%s\n' SUPRALINUX_UBUNTU26_KVM_DEP8_GUEST_OK
EOF
  chmod +x "$FIXTURE/debian/tests/guest-smoke"
  test ! -e "$WORK/autopkgtest"
  if ! timeout -k 30s 22m autopkgtest --no-built-binaries --apt-upgrade \
     --output-dir="$WORK/autopkgtest" "$FIXTURE" \
     -- qemu --cpus=2 --ram-size=2048 --overlay-dir="$WORK/overlays" "$IMAGE" \
     > "$EVID/autopkgtest-console.log" 2>&1; then
    tail -n 90 "$EVID/autopkgtest-console.log" >&2
    exit 1
  fi
  python3 "$SCRIPT" test "$IMAGE" "$META" "$WORK/autopkgtest/summary"
  echo "Genuine hosted Ubuntu 26.04 DEP-8 smoke PASS; no KDE package Attempt" > "$EVID/probe-result.txt"
  ;;
seal)
  test "${SUPRALINUX_CACHE_HIT:-false}" != true
  python3 "$SCRIPT" seal "$IMAGE" "$META" "$WORK/autopkgtest/summary"
  ;;
esac
