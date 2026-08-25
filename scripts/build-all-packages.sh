#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
builder="$repo_root/scripts/build-package.sh"

mapfile -t packages < <(find "$repo_root/packages" -mindepth 2 -maxdepth 2 -type f -path '*/debian/control' -printf '%h\n' | sed 's#/debian$##' | sort)

if [[ ${#packages[@]} -eq 0 ]]; then
    echo "No Debian source packages found under packages/." >&2
    exit 1
fi

for package_dir in "${packages[@]}"; do
    "$builder" "$package_dir"
done
