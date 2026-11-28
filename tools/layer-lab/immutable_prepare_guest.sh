#!/usr/bin/env bash
# Private networkless VM: vda ext4 transport, vdb layer overlay, vdc state.
set -euo pipefail
export LC_ALL=C
test "$(findmnt -n -o SOURCE /)" = /dev/vda
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_BTRFS_ROOT
test "$(blkid -s LABEL -o value /dev/vdc)" = SUPRA_LAB_STATE
source /usr/local/libexec/supra-immutable-layout
work=$(mktemp -d)
mkdir "$work"/{top,state}
cleanup() {
    for dir in state top; do
        if mountpoint -q "$work/$dir"; then umount "$work/$dir"; fi
    done
}
trap cleanup EXIT
mount -t btrfs -o subvolid=5 /dev/vdb "$work/top"
mount -t btrfs -o subvolid=5 /dev/vdc "$work/state"
top="$work/top"
state="$work/state"
test ! -e "$top/immutable"
mkdir "$top/immutable"
test "$(btrfs property get -ts "$top/deployments/base" ro)" = ro=true
for entry in "${immutable_domains[@]}"; do
    domain="${entry%%:*}"
    path="${entry#*:}"
    original="$top/deployments/staged$path"
    test -d "$original"
    btrfs subvolume create "$state/$domain"
    cp -a "$original/." "$state/$domain/"
    chmod --reference="$original" "$state/$domain"
    chown --reference="$original" "$state/$domain"
done
# Do not duplicate an entropy seed from a prior deployment.
rm -f "$state/systemd/random-seed"
for role in staged layer; do
    root="$top/immutable/$role"
    btrfs subvolume snapshot "$top/deployments/$role" "$root"
    immutable_fstab "$role" > "$root/etc/fstab"
    # Stable identity within this disposable three-boot experiment only.
    grep -Eq '^[0-9a-f]{32}$' /etc/machine-id
    cp /etc/machine-id "$root/etc/machine-id"
    for entry in "${immutable_domains[@]}"; do
        test -d "$root${entry#*:}"
    done
    test -d "$root/tmp"
    test -d "$root/run"
    btrfs property set -ts "$root" ro true
    test "$(btrfs property get -ts "$root" ro)" = ro=true
done
sync
btrfs filesystem sync "$top"
btrfs filesystem sync "$state"
cleanup
trap - EXIT
printf '%s\n' SUPRA_IMMUTABLE_PREPARED > /dev/ttyS0
