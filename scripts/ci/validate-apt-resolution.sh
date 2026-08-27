#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEB_DIR="${ROOT_DIR}/build/debs"

shopt -s nullglob
snap_policy_debs=("${DEB_DIR}"/supralinux-snap-policy_*.deb)
base_debs=("${DEB_DIR}"/supralinux-base_*.deb)
settings_debs=("${DEB_DIR}"/supralinux-settings_*.deb)
desktop_debs=("${DEB_DIR}"/supralinux-desktop_*.deb)

if [[ ${#snap_policy_debs[@]} -ne 1 || ${#base_debs[@]} -ne 1 || ${#settings_debs[@]} -ne 1 || ${#desktop_debs[@]} -ne 1 ]]; then
  echo "Expected exactly one built .deb for snap-policy, base, settings and desktop." >&2
  exit 1
fi

snap_policy_deb="${snap_policy_debs[0]}"
base_deb="${base_debs[0]}"
settings_deb="${settings_debs[0]}"
desktop_deb="${desktop_debs[0]}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT
mkdir -p "${tmpdir}/policy-root" "${tmpdir}/preferences.d"

dpkg-deb -x "${snap_policy_deb}" "${tmpdir}/policy-root"
cp "${tmpdir}/policy-root/etc/apt/preferences.d/supralinux-no-snap.pref" \
   "${tmpdir}/preferences.d/"

apt_opts=(
  -o "Dir::Etc::preferencesparts=${tmpdir}/preferences.d"
  -o "APT::Get::List-Cleanup=0"
)

sudo apt-get update

echo "==> Verifying Snap candidates are blocked for a fresh APT state"
for package in snapd plasma-discover-backend-snap; do
  output="$(apt-cache "${apt_opts[@]}" -o Dir::State::status=/dev/null policy "${package}")"
  printf '%s\n' "${output}"
  if ! grep -Fq 'Candidate: (none)' <<<"${output}"; then
    echo "${package} still has an installable candidate with SupraLINUX policy active." >&2
    exit 1
  fi
done

echo "==> Resolving the complete local SupraLINUX package set without installing it"
resolver_log="${tmpdir}/resolver.log"
if ! apt-get "${apt_opts[@]}" --simulate --no-remove install \
  "${snap_policy_deb}" "${base_deb}" "${settings_deb}" "${desktop_deb}" >"${resolver_log}" 2>&1; then
  cat "${resolver_log}" >&2
  echo "Aurora package dependency resolution failed." >&2
  exit 1
fi

if grep -Eq '^Inst (snapd|plasma-discover-backend-snap)( |$)' "${resolver_log}"; then
  cat "${resolver_log}" >&2
  echo "APT attempted to install a Snap component while the SupraLINUX policy was active." >&2
  exit 1
fi

if grep -Eq '^Inst plasma-session-x11( |$)' "${resolver_log}"; then
  cat "${resolver_log}" >&2
  echo "APT attempted to install the Plasma X11 session in the default Aurora baseline." >&2
  exit 1
fi

echo "==> Checking Discover resolution does not pull the Snap backend"
discover_log="${tmpdir}/discover.log"
if apt-get "${apt_opts[@]}" --simulate --no-remove install plasma-discover >"${discover_log}" 2>&1; then
  if grep -Eq '^Inst (snapd|plasma-discover-backend-snap)( |$)' "${discover_log}"; then
    cat "${discover_log}" >&2
    echo "Discover resolution attempted to install Snap support." >&2
    exit 1
  fi
else
  cat "${discover_log}" >&2
  echo "Discover itself did not resolve under the SupraLINUX policy." >&2
  exit 1
fi

echo "Aurora APT resolution smoke tests passed."
