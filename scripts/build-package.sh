#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <package-directory>" >&2
    echo "Example: $0 packages/supralinux-desktop" >&2
    exit 2
fi

package_dir="$1"
if [[ "$package_dir" != /* ]]; then
    package_dir="$repo_root/$package_dir"
fi

if [[ ! -f "$package_dir/debian/control" || ! -f "$package_dir/debian/changelog" || ! -f "$package_dir/debian/rules" ]]; then
    echo "Not a Debian source package: $package_dir" >&2
    exit 1
fi

if [[ ! -x "$package_dir/debian/rules" ]]; then
    echo "debian/rules is not executable: $package_dir/debian/rules" >&2
    exit 1
fi

command -v dpkg-buildpackage >/dev/null 2>&1 || {
    echo "dpkg-buildpackage is required (package: dpkg-dev)." >&2
    exit 1
}

printf 'Building %s\n' "${package_dir#$repo_root/}"
(
    cd "$package_dir"
    dpkg-buildpackage -us -uc -b
)
