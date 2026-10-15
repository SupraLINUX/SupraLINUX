#!/usr/bin/env bash
# Diagnose Ubuntu 26.04 userns capabilities; not a sbuild/KVM/package certificate.
set -Eeuo pipefail
umask 077

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 OUTPUT_DIRECTORY" >&2
  exit 2
fi
OUTPUT_DIR=$1
test "${RUNNER_ENVIRONMENT:-}" = github-hosted
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_ID" = 26.04
test "$(dpkg --print-architecture)" = amd64
test "$(id -u)" -ne 0
for command_name in unshare timeout newuidmap newgidmap sudo stat awk; do
  command -v "$command_name" >/dev/null
done

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
report="$OUTPUT_DIR/probe-results.tsv"
meta="$OUTPUT_DIR/metadata.txt"
printf 'probe\tresult\texit_code\n' > "$report"

{
  printf 'scope=hosted-ubuntu26-userns-diagnosis-only\n'
  printf 'certifies_sbuild=false\n'
  printf 'certifies_guest_kvm=false\n'
  printf 'os=%s:%s\n' "$ID" "$VERSION_ID"
  printf 'arch=%s\n' "$(dpkg --print-architecture)"
  printf 'source_sha=%s\n' "${GITHUB_SHA:-not-provided}"
  printf 'unshare_package=%s\n' "$(dpkg-query -W -f='${Version}' util-linux)"
  printf 'uidmap_package=%s\n' "$(dpkg-query -W -f='${Version}' uidmap)"
  for f in \
    /proc/sys/user/max_user_namespaces \
    /proc/sys/kernel/unprivileged_userns_clone \
    /proc/sys/kernel/apparmor_restrict_unprivileged_userns; do
    if [[ -r "$f" ]]; then
      printf '%s=%s\n' "${f##*/}" "$(cat "$f")"
    else
      printf '%s=unavailable\n' "${f##*/}"
    fi
  done
  for account in "$(id -un)" root; do
    for kind in subuid subgid; do
      if [[ -r "/etc/$kind" ]]; then
        count=$(awk -F: -v user="$account" '$1 == user { total += $3 } END { print total+0 }' "/etc/$kind")
        printf '%s_%s_assigned=%s\n' "$account" "$kind" "$count"
      else
        printf '%s_%s_assigned=unavailable\n' "$account" "$kind"
      fi
    done
  done
  printf 'newuidmap_mode=%s\n' "$(stat -c '%a' "$(command -v newuidmap)")"
  printf 'newgidmap_mode=%s\n' "$(stat -c '%a' "$(command -v newgidmap)")"
} > "$meta"
cat "$meta"

probe() {
  local label=$1 rc result
  shift
  if timeout --signal=TERM --kill-after=2s 15s "$@" > "$tmp" 2>&1; then
    rc=0
    result=PASS
  else
    rc=$?
    result=FAIL
  fi
  printf '%s\t%s\t%s\n' "$label" "$result" "$rc" >> "$report"
  printf 'PROBE %s: %s (exit=%s)\n' "$label" "$result" "$rc"
  sed -n '1,8p' "$tmp"
}

probe runner-single-id \
  unshare --user --map-root-user --mount \
  sh -c 'id -u | grep -qx 0 && test -r /proc/self/uid_map'
probe runner-subordinate-ids \
  unshare --user --map-root-user --map-auto \
  sh -c 'id -u | grep -qx 0 && test -r /proc/self/gid_map'
probe root-single-id \
  sudo -n unshare --user --map-root-user --mount \
  sh -c 'id -u | grep -qx 0 && test -r /proc/self/uid_map'
probe root-subordinate-ids \
  sudo -n unshare --user --map-root-user --map-auto \
  sh -c 'id -u | grep -qx 0 && test -r /proc/self/gid_map'

cat "$report"
echo 'DIAGNOSTIC_COLLECTED: failures above are findings, not package failures.'
echo 'SBUILD_UNSHARE_CERTIFICATION=NOT_PERFORMED'
