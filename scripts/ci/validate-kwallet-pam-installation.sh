#!/usr/bin/env bash
set -euo pipefail

ROOTFS="${1:-/}"
ROOTFS="${ROOTFS%/}"
[[ -n "${ROOTFS}" ]] || ROOTFS="/"

for pam_file in common-session common-auth; do
  path="${ROOTFS}/etc/pam.d/${pam_file}"
  [[ -f "${path}" ]] || {
    echo "AURORA_KWALLET_PAM_INSTALL_FAILURE: missing ${path}" >&2
    exit 1
  }
  grep -Eq '(^|[[:space:]])pam_kwallet5\.so([[:space:]]|$)' "${path}" || {
    echo "AURORA_KWALLET_PAM_INSTALL_FAILURE: pam_kwallet5.so not registered in ${path}" >&2
    exit 1
  }
done

echo "AURORA_KWALLET_PAM_COMMON_SESSION=present"
echo "AURORA_KWALLET_PAM_COMMON_AUTH=present"
echo "AURORA_KWALLET_PAM_INSTALL_SUCCESS"
