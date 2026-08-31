#!/usr/bin/env bash
set -euo pipefail

expected_uidmap_version='1:4.17.4-2ubuntu3'
uidmap_version="$(dpkg-query -W -f='${Version}' uidmap 2>/dev/null || true)"

if [[ "${uidmap_version}" != "${expected_uidmap_version}" ]]; then
  echo "AURORA_KSQ_UIDMAP_FAILURE: expected uidmap ${expected_uidmap_version}, got ${uidmap_version:-missing}; re-qualify privilege behavior before changing helpers" >&2
  exit 1
fi

for command in sudo stat getcap setcap; do
  command -v "${command}" >/dev/null 2>&1 || {
    echo "AURORA_KSQ_UIDMAP_FAILURE: missing required command ${command}" >&2
    exit 1
  }
done

for helper in /usr/bin/newuidmap /usr/bin/newgidmap; do
  [[ -x "${helper}" ]] || {
    echo "AURORA_KSQ_UIDMAP_FAILURE: missing helper ${helper}" >&2
    exit 1
  }
  [[ "$(stat -c '%u:%g' "${helper}")" == '0:0' ]] || {
    echo "AURORA_KSQ_UIDMAP_FAILURE: ${helper} is not root-owned" >&2
    exit 1
  }
done

uid_cap="$(getcap /usr/bin/newuidmap || true)"
gid_cap="$(getcap /usr/bin/newgidmap || true)"
uid_mode="$(stat -c '%a' /usr/bin/newuidmap)"
gid_mode="$(stat -c '%a' /usr/bin/newgidmap)"

already_normalized=no
if [[ "${uid_mode}" == '755' && "${gid_mode}" == '755' \
      && "${uid_cap}" == '/usr/bin/newuidmap cap_setuid=ep' \
      && "${gid_cap}" == '/usr/bin/newgidmap cap_setgid=ep' ]]; then
  already_normalized=yes
else
  # Only transform the exact stock state that was root-caused and proven in
  # Actions run 33422301732. Refuse unknown privilege states rather than
  # papering over a future package or image change.
  if [[ "${uid_mode}" != '4755' || "${gid_mode}" != '4755' \
        || -n "${uid_cap}" || -n "${gid_cap}" ]]; then
    echo 'AURORA_KSQ_UIDMAP_FAILURE: helpers are neither exact stock-setuid nor exact certified filecap state' >&2
    stat -c '%A %a %U %G %u %g %n' /usr/bin/newuidmap /usr/bin/newgidmap >&2 || true
    getcap /usr/bin/newuidmap /usr/bin/newgidmap >&2 || true
    exit 1
  fi

  sudo chmod u-s /usr/bin/newuidmap /usr/bin/newgidmap
  sudo setcap cap_setuid=ep /usr/bin/newuidmap
  sudo setcap cap_setgid=ep /usr/bin/newgidmap
fi

[[ "$(stat -c '%a' /usr/bin/newuidmap)" == '755' ]]
[[ "$(stat -c '%a' /usr/bin/newgidmap)" == '755' ]]
[[ "$(getcap /usr/bin/newuidmap)" == '/usr/bin/newuidmap cap_setuid=ep' ]]
[[ "$(getcap /usr/bin/newgidmap)" == '/usr/bin/newgidmap cap_setgid=ep' ]]

echo "AURORA_KSQ_UIDMAP_PACKAGE_VERSION=${uidmap_version}"
echo 'AURORA_KSQ_UIDMAP_MODEL=filecap'
echo 'AURORA_KSQ_UIDMAP_NEWUIDMAP_CAP=cap_setuid=ep'
echo 'AURORA_KSQ_UIDMAP_NEWGIDMAP_CAP=cap_setgid=ep'
echo "AURORA_KSQ_UIDMAP_ALREADY_NORMALIZED=${already_normalized}"
echo 'AURORA_KSQ_UIDMAP_NORMALIZATION_PASS'
