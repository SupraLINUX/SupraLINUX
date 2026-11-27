#!/usr/bin/env bash
# Original test fixture, only on the explicit disposable labelled second disk.
set -euo pipefail
export LC_ALL=C
test -b /dev/vdb
test "$(blkid -s TYPE -o value /dev/vdb)" = btrfs
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_BTRFS_LAB
test "$(findmnt -n -o MAJ:MIN /)" != "$(lsblk -dn -o MAJ:MIN /dev/vdb)"
dir=$(mktemp -d)
trap 'umount "$dir"; rmdir "$dir"' EXIT
mount -t btrfs -o subvolid=5 /dev/vdb "$dir"
cd "$dir"
mkdir deployments persistent
btrfs subvolume create deployments/base
btrfs subvolume create persistent/home
mkdir -p deployments/base/{etc,var/lib/pacman,home}
printf 'base-v1\n' > deployments/base/etc/version
printf 'package-v1\n' > deployments/base/var/lib/pacman/inventory
printf 'document-v1\n' > persistent/home/document
btrfs property set -ts deployments/base ro true
btrfs subvolume snapshot deployments/base deployments/staging
printf 'base-v2\n' > deployments/staging/etc/version
printf 'package-v2\n' > deployments/staging/var/lib/pacman/inventory
printf 'document-v2\n' > persistent/home/document
test "$(cat deployments/base/etc/version)" = base-v1
test "$(cat deployments/base/var/lib/pacman/inventory)" = package-v1
test "$(btrfs property get -ts deployments/base ro)" = ro=true
if (printf 'must-fail\n' > deployments/base/etc/version) 2>/dev/null; then
    echo "Read-only base accepted write" >&2
    exit 1
fi
test "$(cat deployments/staging/etc/version)" = base-v2
test "$(cat deployments/staging/var/lib/pacman/inventory)" = package-v2
test "$(cat persistent/home/document)" = document-v2
btrfs property set -ts deployments/staging ro true
btrfs subvolume snapshot deployments/base deployments/rollback-stage
test "$(cat deployments/rollback-stage/etc/version)" = base-v1
test "$(cat deployments/rollback-stage/var/lib/pacman/inventory)" = package-v1
test "$(cat persistent/home/document)" = document-v2
# Simulate a failed unpublished staging transaction and discard only its snapshot.
btrfs subvolume snapshot deployments/base deployments/failed-stage
printf 'incomplete\n' > deployments/failed-stage/etc/version
btrfs subvolume delete deployments/failed-stage
test ! -e deployments/failed-stage
test "$(cat deployments/base/etc/version)" = base-v1
test "$(cat deployments/staging/etc/version)" = base-v2
test "$(cat persistent/home/document)" = document-v2
sync
btrfs filesystem sync "$dir"
btrfs subvolume list "$dir"
cd /
umount "$dir"
mount -t btrfs -o subvolid=5 /dev/vdb "$dir"
test "$(cat "$dir/deployments/base/etc/version")" = base-v1
test "$(cat "$dir/deployments/staging/etc/version")" = base-v2
test "$(cat "$dir/deployments/rollback-stage/var/lib/pacman/inventory")" = package-v1
test "$(cat "$dir/persistent/home/document")" = document-v2
test ! -e "$dir/deployments/failed-stage"
printf '%s\n' SUPRA_BTRFS_LAB_READY > /dev/ttyS0
