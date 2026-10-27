#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

if [[ "${EUID}" -ne 0 ]]; then
    printf 'Authoritative host tooling repair must run as root.\n' >&2
    exit 1
fi

for command_name in apt-get dpkg-query python3; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required host package-manager command: %s\n' "${command_name}" >&2
        exit 1
    }
done

export DEBIAN_FRONTEND=noninteractive

persistent_change=false
package_manager_invoked=false
repair_action=none

if ! command -v apt-ftparchive >/dev/null 2>&1; then
    package_manager_invoked=true
    if dpkg-query -W -f='${db:Status-Abbrev}' apt-utils 2>/dev/null | grep -q '^ii '; then
        repair_action=reinstall
        apt-get -y --no-install-recommends --reinstall install apt-utils >&2
    else
        repair_action=install
        apt-get -y --no-install-recommends install apt-utils >&2
    fi
    persistent_change=true
fi

APT_FTPARCHIVE="$(command -v apt-ftparchive)"
APT_UTILS_VERSION="$(dpkg-query -W -f='${Version}' apt-utils)"

python3 - "${persistent_change}" "${package_manager_invoked}" "${repair_action}" "${APT_FTPARCHIVE}" "${APT_UTILS_VERSION}" <<'PY'
import json
import sys

persistent_change, package_manager_invoked, repair_action, command_path, version = sys.argv[1:]
payload = {
    "schema": 1,
    "state": "PASS",
    "kind": "authoritative-host-tooling",
    "required_commands": {
        "apt-ftparchive": command_path,
    },
    "packages": {
        "apt-utils": version,
    },
    "repair_action": repair_action,
    "package_manager_invoked": package_manager_invoked == "true",
    "persistent_change": persistent_change == "true",
    "apt_update_invoked": False,
    "dist_upgrade_invoked": False,
    "package_attempt_effect": "none",
    "vm_created": False,
    "jit_invoked": False,
}
print(json.dumps(payload, sort_keys=True))
PY
