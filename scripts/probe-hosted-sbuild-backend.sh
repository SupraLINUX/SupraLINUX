#!/usr/bin/env bash
# Small, disposable unprivileged sbuild debug experiment on GitHub-hosted Ubuntu.
# This is a host-only backend diagnostic, not a KDE package Attempt or KVM proof.
set -Eeuo pipefail
umask 077

[[ $# -eq 1 ]] || { echo "Usage: $0 OUTPUT_DIRECTORY" >&2; exit 2; }
[[ "${RUNNER_ENVIRONMENT:-}" == github-hosted ]]
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 && "$VERSION_CODENAME" == resolute ]]
[[ "$(dpkg --print-architecture)" == amd64 && "$(id -u)" -ne 0 ]]
for tool in timeout sbuild mmdebstrap dpkg-source dpkg-parsechangelog sha256sum; do
  command -v "$tool" >/dev/null
done
OUTPUT_DIR=$1
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR=$(realpath "$OUTPUT_DIR")
WORK=$(mktemp -d /var/tmp/supralinux-backend-smoke.XXXXXXXX)
trap 'rm -rf -- "$WORK" 2>/dev/null || true' EXIT
mkdir -p "$WORK/source/debian/source" "$WORK/out"
REPORT="$OUTPUT_DIR/result.txt"
ROOTFS_LOG="$OUTPUT_DIR/mmdebstrap.log"
SBUILD_LOG="$OUTPUT_DIR/sbuild-debug.log"
printf 'scope=hosted-ubuntu26-native-host-debug-only\nkvm_guest_certified=false\nkde_package_attempt_consumed=false\nsource_sha=%s\nactor=unprivileged-runner\n' "${GITHUB_SHA:-not-provided}" > "$REPORT"

cat > "$WORK/source/debian/changelog" <<'EOF'
supralinux-sbuild-backend-probe (0.1) resolute; urgency=low

  * Exercise a disposable hosted clean build mechanism.

 -- SupraLINUX QA <qa@supralinux.invalid>  Thu, 15 Oct 2026 00:00:00 +0000
EOF
cat > "$WORK/source/debian/control" <<'EOF'
Source: supralinux-sbuild-backend-probe
Section: misc
Priority: optional
Maintainer: SupraLINUX QA <qa@supralinux.invalid>
Build-Depends: debhelper-compat (= 13)
Standards-Version: 4.7.0
Rules-Requires-Root: no

Package: supralinux-sbuild-backend-probe
Architecture: any
Depends: ${misc:Depends}
Description: Disposable host-only mechanism check
 This package is never distributed or admitted as SupraLINUX evidence.
EOF
cat > "$WORK/source/debian/rules" <<'EOF'
#!/usr/bin/make -f
%:
	dh $@
EOF
chmod 0755 "$WORK/source/debian/rules"
printf '3.0 (native)\n' > "$WORK/source/debian/source/format"
printf 'disposable backend test\n' > "$WORK/source/sample.txt"
printf 'sample.txt usr/share/supralinux-qa/\n' > "$WORK/source/debian/install"
[[ "$(dpkg-parsechangelog -l "$WORK/source/debian/changelog" -S Version)" == 0.1 ]]
(cd "$WORK" && dpkg-source -b source)
DSC="$WORK/supralinux-sbuild-backend-probe_0.1.dsc"
[[ -s "$DSC" ]]
printf 'source_dsc_sha256=%s\n' "$(sha256sum "$DSC" | awk '{print $1}')" >> "$REPORT"

# Use the documented unprivileged backend outside KVM to contrast the failed root-mode smoke.
if timeout --signal=TERM --kill-after=20s 270s env -i \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME="$HOME" USER="$(id -un)" LOGNAME="$(id -un)" LANG=C.UTF-8 \
  DEBIAN_FRONTEND=noninteractive \
  mmdebstrap --mode=unshare --variant=buildd --architectures=amd64 \
  --components=main,universe --format=tar --keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg \
  resolute "$WORK/resolute-amd64.tar" \
  "deb http://archive.ubuntu.com/ubuntu resolute main universe" \
  "deb http://archive.ubuntu.com/ubuntu resolute-updates main universe" \
  "deb http://security.ubuntu.com/ubuntu resolute-security main universe" \
  > "$ROOTFS_LOG" 2>&1; then
  printf 'rootfs=PASS\n' >> "$REPORT"
else
  printf 'rootfs=FAIL\nhost_sbuild=NOT_RUN\n' >> "$REPORT"
  tail -n 25 "$ROOTFS_LOG"
  cat "$REPORT"
  exit 0
fi
[[ -s "$WORK/resolute-amd64.tar" ]]

# Run as the normal hosted user with subordinate IDs; do not alter the kernel.
# Sanitize the environment to keep Actions credentials out of debug output.
if timeout --signal=TERM --kill-after=20s 360s env -i \
  PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME="$HOME" USER="$(id -un)" LOGNAME="$(id -un)" LANG=C.UTF-8 \
  DEBIAN_FRONTEND=noninteractive \
  sbuild --debug --chroot-mode=unshare --chroot="$WORK/resolute-amd64.tar" \
  --dist=resolute --arch=amd64 --no-run-lintian --no-run-autopkgtest \
  --build-dir="$WORK/out" "$DSC" \
  > "$SBUILD_LOG" 2>&1; then
  # An exit status of zero alone does not count without the expected products.
  shopt -s nullglob
  debs=("$WORK"/out/*.deb)
  changes=("$WORK"/out/*.changes)
  buildinfos=("$WORK"/out/*.buildinfo)
  if [[ "${#debs[@]}" -eq 1 && "${#changes[@]}" -eq 1 && "${#buildinfos[@]}" -eq 1 ]] &&
     [[ "$(dpkg-deb -f "${debs[0]}" Package)" == supralinux-sbuild-backend-probe ]] &&
     [[ "$(dpkg-deb -f "${debs[0]}" Version)" == 0.1 ]] &&
     [[ "$(dpkg-deb -f "${debs[0]}" Architecture)" == amd64 ]]; then
    printf 'host_sbuild=PASS\n' >> "$REPORT"
    sha256sum "${debs[0]}" "${changes[0]}" "${buildinfos[0]}" >> "$REPORT"
  else
    printf 'host_sbuild=FAIL_ARTIFACT_CHECK\n' >> "$REPORT"
  fi
else
  printf 'host_sbuild=FAIL\n' >> "$REPORT"
fi
tail -n 45 "$SBUILD_LOG"
cat "$REPORT"
echo 'HOST_BACKEND_DIAGNOSTIC_ONLY: no KVM guest, no KDE package PASS.'
