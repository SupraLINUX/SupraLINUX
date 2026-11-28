#!/usr/bin/env bash
# Recovery inspection only; do not approve, boot, repair or delete the stage.
set -euo pipefail
export LC_ALL=C
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_BTRFS_ROOT
test "$(blkid -s LABEL -o value /dev/vdc)" = SUPRA_LAB_OUTPUT
work=$(mktemp -d)
mkdir "$work/top" "$work/out"
trap 'umount "$work/out"; umount "$work/top"; rmdir "$work/out" "$work/top" "$work"' EXIT
mount -t btrfs -o subvolid=5 /dev/vdb "$work/top"
mount -t ext4 /dev/vdc "$work/out"
base="$work/top/deployments/base"
previous="$work/top/deployments/staged"
partial="$work/top/deployments/layer"
test "$(btrfs property get -ts "$base" ro)" = ro=true
test -d "$partial"
test -x "$partial/usr/bin/tree"
test -d "$partial/var/lib/pacman/local/tree-2.3.2-1"
# Pacman hook was interrupted before final inventory and deployment identity.
test "$(cat "$partial/etc/supra-lab-deployment")" != layer
test ! -e "$previous/usr/bin/tree"
test ! -e "$base/usr/bin/tree"
source /usr/local/libexec/supra-layer-digest
layer_digest "$base" > "$work/out/base-recovered.sha256"
layer_digest "$previous" > "$work/out/previous-recovered.sha256"
chroot "$previous" pacman -Q > "$work/out/previous-recovered.txt"
sync
printf '%s\n' SUPRA_INSTALL_RECOVERED > /dev/ttyS0
