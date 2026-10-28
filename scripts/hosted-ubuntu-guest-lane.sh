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
  if [[ "${SUPRALINUX_CACHE_HIT:-false}" == true ]]; then
    python3 "$SCRIPT" verify "$IMAGE" "$META"
    echo "Verified milestone cache hit" > "$EVID/snapshot-admission.txt"
  else
    test ! -e "$IMAGE" && test ! -e "$META"
    test "$(df -Pk "$WORK" | awk 'END{print $4}')" -ge 9000000
    # vmdb2 and dpkg/grub chroots must not inherit a host-only TMPDIR path.
    # Keep the base-image output on the runner disk and let chroot use /tmp.
    if ! timeout -k 30s 45m sudo env -u TMPDIR autopkgtest-build-qemu \
       --mirror=http://archive.ubuntu.com/ubuntu \
       --keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg \
       --architecture=amd64 --size=8G --boot=bios --apt-proxy=DIRECT \
       resolute "$IMAGE" > "$WORK/tmp/base-build.raw.log" 2>&1; then
      # vmdb2 verbose DEBUG ENV can contain credentials from hosted runners.
      # Keep raw logs off uploaded artifacts, emit only allowlisted diagnostics.
      grep -E '^(E: |W: |dpkg: error|run-parts:|ERROR:|.* (ERROR|error):|.*exited with return code|.*returned non-zero exit status)'         "$WORK/tmp/base-build.raw.log" | tail -n 70 > "$EVID/base-build-failure.txt" || true
      cat "$EVID/base-build-failure.txt" >&2
      exit 1
    fi
    rm -f "$WORK/tmp/base-build.raw.log"
    sudo chown "$(id -u):$(id -g)" "$IMAGE"
    python3 "$SCRIPT" create "$IMAGE" "$META"
    echo "New unsigned-for-release base; awaiting guest test" > "$EVID/snapshot-admission.txt"
  fi
  ;;
test)
  python3 "$SCRIPT" inspect "$IMAGE" "$META"
  FIXTURE="$ROOT/tests/fixtures/hosted-ubuntu-guest"
  # Validate the real versioned Debian source fixture before launching QEMU.
  test -r "$FIXTURE/debian/changelog"
  test -x "$FIXTURE/debian/tests/guest-smoke"
  test "$(dpkg-parsechangelog -l "$FIXTURE/debian/changelog" -S Source)" = supralinux-guest-probe
  test "$(dpkg-parsechangelog -l "$FIXTURE/debian/changelog" -S Version)" = 1.0-1
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
