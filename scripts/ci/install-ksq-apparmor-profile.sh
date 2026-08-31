#!/usr/bin/env bash
set -euo pipefail

profile_name='supralinux-ksq-unshare'
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_profile="${script_dir}/apparmor/${profile_name}"
target_dir='/etc/apparmor.d/containers'
target_profile="${target_dir}/${profile_name}"

if [[ ${EUID} -ne 0 ]]; then
  echo 'ERROR: this installer must run as root on the self-hosted runner host.' >&2
  exit 1
fi

for command in apparmor_parser install cmp grep; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "ERROR: required host command not found: ${command}" >&2
    exit 1
  fi
done

if [[ ! -r "${source_profile}" ]]; then
  echo "ERROR: profile source not found: ${source_profile}" >&2
  exit 1
fi

if [[ ! -r /sys/kernel/security/apparmor/profiles ]]; then
  echo 'ERROR: AppArmor profiles interface is unavailable on this host.' >&2
  exit 1
fi

install -d -m 0755 "${target_dir}"
install -o root -g root -m 0644 "${source_profile}" "${target_profile}"

# Follow Docker's documented custom-profile loading model. -r replaces an
# existing loaded profile; -W reports parser warnings instead of hiding them.
apparmor_parser -r -W "${target_profile}"

if ! grep -Fqx "${profile_name} (enforce)" /sys/kernel/security/apparmor/profiles; then
  echo "ERROR: ${profile_name} was not found loaded in enforce mode." >&2
  exit 1
fi

cmp --silent "${source_profile}" "${target_profile}"

printf 'AURORA_KSQ_APPARMOR_PROFILE=%s\n' "${profile_name}"
printf 'AURORA_KSQ_APPARMOR_PROFILE_PATH=%s\n' "${target_profile}"
printf 'AURORA_KSQ_APPARMOR_PROFILE_STATUS=LOADED_ENFORCE\n'
