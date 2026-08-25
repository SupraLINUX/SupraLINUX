#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
pref="$repo_root/packages/supralinux-snap-policy/files/supralinux-no-snap.pref"

if [[ ! -r "$pref" ]]; then
    echo "FAIL: policy file not found: $pref" >&2
    exit 1
fi

if [[ ! -r /etc/os-release ]]; then
    echo "SKIP: cannot determine operating system." >&2
    exit 77
fi

# shellcheck disable=SC1091
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_CODENAME:-}" != "resolute" ]]; then
    echo "SKIP: this resolver test must run on Ubuntu 26.04 (resolute)." >&2
    exit 77
fi

command -v apt-cache >/dev/null 2>&1 || { echo "FAIL: apt-cache is required." >&2; exit 1; }
command -v apt-get >/dev/null 2>&1 || { echo "FAIL: apt-get is required." >&2; exit 1; }

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
mkdir -p "$tmpdir/preferences.d"

apt_opts=(
    -o "Dir::Etc::Preferences=$pref"
    -o "Dir::Etc::PreferencesParts=$tmpdir/preferences.d"
)

candidate_of() {
    apt-cache "${apt_opts[@]}" policy "$1" | awk '/Candidate:/ {print $2; exit}'
}

for package in snapd plasma-discover-backend-snap; do
    candidate="$(candidate_of "$package")"
    if [[ "$candidate" != "(none)" ]]; then
        echo "FAIL: $package still has APT candidate '$candidate' while Supra policy is active." >&2
        exit 1
    fi
    echo "PASS: $package has no installable candidate while policy is active."
done

simulation="$(apt-get "${apt_opts[@]}" -s install plasma-discover 2>&1)" || {
    printf '%s\n' "$simulation" >&2
    echo "FAIL: plasma-discover could not be resolved under the Supra Snap policy." >&2
    exit 1
}

if grep -Eq '^Inst (snapd|plasma-discover-backend-snap)( |$)' <<<"$simulation"; then
    printf '%s\n' "$simulation" >&2
    echo "FAIL: Discover simulation attempts to install Snap components." >&2
    exit 1
fi

echo "PASS: plasma-discover resolves without snapd or the Snap backend."

normal_candidate="$(apt-cache policy snapd | awk '/Candidate:/ {print $2; exit}')"
if [[ -z "$normal_candidate" || "$normal_candidate" == "(none)" ]]; then
    echo "FAIL: snapd has no normal Ubuntu candidate after ignoring the Supra policy." >&2
    exit 1
fi

echo "PASS: removing the policy would restore normal Ubuntu snapd availability ($normal_candidate)."
