#!/usr/bin/env bash
# Accept only drivers built into the exact target kernel or in its initramfs.
set -euo pipefail
export LC_ALL=C
release="$1"
builtin="$2"
archive="$3"
[[ "$release" =~ ^[a-zA-Z0-9._+-]+$ ]]
test -s "$builtin"
test -s "$archive"
for module in btrfs virtio_pci virtio_blk; do
    # kmod normalizes hyphen and underscore; match exact basename only.
    pattern=${module//_/'[-_]'}
    if grep -Eq "(^|/)${pattern}\.ko$" "$builtin"; then
        printf '%s\tbuiltin\n' "$module"
    elif awk -v prefix="usr/lib/modules/$release/" -v other="lib/modules/$release/" \
        'index($0,prefix)==1 || index($0,other)==1' "$archive" |
        grep -E "(^|/)${pattern}\.ko(\.(zst|xz|gz))?$" >/dev/null; then
        printf '%s\tinitramfs\n' "$module"
    else
        printf 'Missing required kernel driver: %s (%s)\n' "$module" "$release" >&2
        exit 1
    fi
done
