#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
failed=0

mapfile -t controls < <(find "$repo_root/packages" -mindepth 2 -maxdepth 3 -type f -path '*/debian/control' | sort)

if [[ ${#controls[@]} -eq 0 ]]; then
    echo "FAIL: no Debian source packages found." >&2
    exit 1
fi

for control in "${controls[@]}"; do
    debian_dir="$(dirname "$control")"
    package_dir="$(dirname "$debian_dir")"
    rel="${package_dir#$repo_root/}"

    printf 'Checking %s\n' "$rel"

    for required in control changelog rules source/format; do
        if [[ ! -f "$debian_dir/$required" ]]; then
            echo "  FAIL: missing debian/$required" >&2
            failed=1
        fi
    done

    if [[ -f "$debian_dir/rules" && ! -x "$debian_dir/rules" ]]; then
        echo "  FAIL: debian/rules is not executable" >&2
        failed=1
    fi

    if [[ -f "$debian_dir/source/format" ]] && ! grep -qx '3.0 (native)' "$debian_dir/source/format"; then
        echo "  FAIL: unexpected source format" >&2
        failed=1
    fi

    if command -v dpkg-parsechangelog >/dev/null 2>&1 && [[ -f "$debian_dir/changelog" ]]; then
        if ! (cd "$package_dir" && dpkg-parsechangelog -S Source >/dev/null); then
            echo "  FAIL: invalid Debian changelog" >&2
            failed=1
        fi
    fi
done

if (( failed != 0 )); then
    exit 1
fi

echo "PASS: Debian source tree checks completed."
