#!/usr/bin/env bash
# Only the disposable, offline target VM with four explicitly labelled disks.
set -euo pipefail
export LC_ALL=C
for device in vdb vdc vdd; do test -b "/dev/$device"; done
test "$(blkid -s TYPE -o value /dev/vdb)" = ext4
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_TARGET
test "$(blockdev --getro /dev/vdb)" = 1
test "$(blkid -s TYPE -o value /dev/vdc)" = btrfs
test "$(blkid -s LABEL -o value /dev/vdc)" = SUPRA_BTRFS_ROOT
test "$(blkid -s LABEL -o value /dev/vdd)" = SUPRA_LAB_OUTPUT
test "$(findmnt -n -o MAJ:MIN /)" != "$(lsblk -dn -o MAJ:MIN /dev/vdb)"
work=$(mktemp -d)
mkdir "$work/source" "$work/top" "$work/out"
src="$work/source"
top="$work/top"
out="$work/out"
root="$top/deployments/staged"
cleanup() {
    local rc=0
    for path in "$root/dev" "$root/sys" "$root/proc" "$out" "$top" "$src"; do
        if mountpoint -q "$path"; then umount "$path" || rc=1; fi
    done
    rmdir "$work/source" "$work/top" "$work/out" "$work" || rc=1
    return "$rc"
}
trap cleanup EXIT
mount -t ext4 -o ro,noload /dev/vdb "$src"
mount -t btrfs -o subvolid=5 /dev/vdc "$top"
mount -t ext4 /dev/vdd "$out"
mkdir "$top/deployments"
btrfs subvolume create "$root"
# Preserve ownership, modes, hardlinks, ACLs and xattrs from the inactive root.
tar --numeric-owner --acls --xattrs --xattrs-include='*' --one-file-system -cpf - -C "$src" . | \
    tar --numeric-owner --same-owner --same-permissions --acls --xattrs --xattrs-include='*' -xpf - -C "$root"
printf 'staged\n' > "$root/etc/supra-lab-deployment"
# Explicit root filesystem and virtio modules for the new boot path.
mkdir -p "$root/etc/mkinitcpio.conf.d"
printf 'MODULES+=(btrfs virtio_pci virtio_blk)\n' > "$root/etc/mkinitcpio.conf.d/99-supra-btrfs-lab.conf"
printf 'LABEL=SUPRA_BTRFS_ROOT / btrfs rw,subvol=deployments/staged 0 0\n' > "$root/etc/fstab"
mount -t proc proc "$root/proc"
mount -t sysfs sysfs "$root/sys"
mount --bind /dev "$root/dev"
chroot "$root" mkinitcpio -P 2>&1 | tee "$out/mkinitcpio.log"
if grep -Ei '(^|[[:space:]])ERROR:' "$out/mkinitcpio.log"; then exit 1; fi
chroot "$root" pacman -Q > "$out/installed-packages.txt"
(cd "$out" && sha256sum installed-packages.txt | awk '{print $1 "  -"}') > "$root/etc/supra-lab-inventory.sha256"
cp "$root/boot/vmlinuz-linux-lts" "$out/target-kernel"
cp "$root/boot/initramfs-linux-lts.img" "$out/target-initrd"
(cd "$out" && sha256sum target-kernel target-initrd > boot.sha256)
for path in "$root/dev" "$root/sys" "$root/proc"; do umount "$path"; done
btrfs subvolume snapshot -r "$root" "$top/deployments/base"
test "$(btrfs property get -ts "$top/deployments/base" ro)" = ro=true
test "$(btrfs property get -ts "$root" ro)" = ro=false
# This base is a snapshot of the prepared lab root, not a promoted deployment.
printf 'base_created=true\n' > "$out/layout.txt"
sync
btrfs filesystem sync "$top"
cleanup
trap - EXIT
printf '%s\n' SUPRA_BTRFS_ROOT_PREPARED > /dev/ttyS0
