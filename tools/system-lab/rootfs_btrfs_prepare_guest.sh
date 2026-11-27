#!/usr/bin/env bash
# Only the disposable, offline target VM with four explicitly labelled disks.
set -Eeuo pipefail
export LC_ALL=C
trap 'rc=$?; printf "BTRFS_PREP_ERROR line=%s exit=%s command=%s\n" "$LINENO" "$rc" "$BASH_COMMAND" >&2' ERR
phase() { printf 'BTRFS_PREP_PHASE=%s\n' "$1"; }
phase device-checks
lsblk -o NAME,TYPE,FSTYPE,LABEL,RO,MAJ:MIN
findmnt -n -o SOURCE,FSTYPE,MAJ:MIN /
for device in vdb vdc vdd; do test -b "/dev/$device"; done
test "$(blkid -s TYPE -o value /dev/vdb)" = ext4
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_TARGET
test "$(blockdev --getro /dev/vdb)" = 1
test "$(blkid -s TYPE -o value /dev/vdc)" = btrfs
test "$(blkid -s LABEL -o value /dev/vdc)" = SUPRA_BTRFS_ROOT
test "$(blkid -s LABEL -o value /dev/vdd)" = SUPRA_LAB_OUTPUT
test "$(findmnt -n -o MAJ:MIN /)" != "$(lsblk -dn -o MAJ:MIN /dev/vdb)"
work=$(mktemp -d)
mkdir "$work/source" "$work/top" "$work/out" "$work/root"
src="$work/source"
top="$work/top"
out="$work/out"
root="$work/root"
cleanup() {
    local rc=0
    for path in "$root/dev" "$root/sys" "$root/proc" "$root" "$out" "$top" "$src"; do
        if mountpoint -q "$path"; then umount "$path" || rc=1; fi
    done
    rmdir "$work/source" "$work/top" "$work/out" "$work/root" "$work" || rc=1
    return "$rc"
}
trap cleanup EXIT
phase mount-source
mount -t ext4 -o ro,noload /dev/vdb "$src"
phase mount-destination
mount -t btrfs -o subvolid=5 /dev/vdc "$top"
mount -t ext4 /dev/vdd "$out"
mkdir "$top/deployments"
btrfs subvolume create "$top/deployments/staged"
mount -t btrfs -o subvol=deployments/staged /dev/vdc "$root"
test "$(findmnt -n -o FSROOT --mountpoint "$root")" = /deployments/staged
# Preserve ownership, modes, hardlinks, ACLs and xattrs from the inactive root.
phase copy-root
tar --numeric-owner --acls --xattrs --xattrs-include='*' --one-file-system -cpf - -C "$src" . | \
    tar --numeric-owner --same-owner --same-permissions --acls --xattrs --xattrs-include='*' -xpf - -C "$root"
phase configure-root
printf 'staged\n' > "$root/etc/supra-lab-deployment"
# Explicit root filesystem and virtio modules for the new boot path.
mkdir -p "$root/etc/mkinitcpio.conf.d"
# This image targets the guest, not the builder's detected hardware/root.
cat > "$root/etc/mkinitcpio.conf.d/99-supra-btrfs-lab.conf" <<'CONF'
MODULES+=(btrfs virtio_pci virtio_blk)
supra_hooks=()
for supra_hook in "${HOOKS[@]}"; do
    [[ "$supra_hook" == autodetect ]] || supra_hooks+=("$supra_hook")
done
HOOKS=("${supra_hooks[@]}")
unset supra_hooks supra_hook
CONF
printf 'LABEL=SUPRA_BTRFS_ROOT / btrfs rw,subvol=deployments/staged 0 0\n' > "$root/etc/fstab"
mount -t proc proc "$root/proc"
mount -t sysfs sysfs "$root/sys"
mount --bind /dev "$root/dev"
phase initramfs
# Avoid a blocked initramfs tool consuming the whole guest budget.
timeout --kill-after=10 150 chroot "$root" mkinitcpio -P 2>&1 | tee "$out/mkinitcpio.log"
if grep -Ei '(^|[[:space:]])ERROR:' "$out/mkinitcpio.log"; then exit 1; fi
if grep -Fq 'Running build hook: [autodetect]' "$out/mkinitcpio.log"; then
    echo 'Unexpected host-dependent autodetect hook' >&2
    exit 1
fi
phase initramfs-content
chroot "$root" lsinitcpio /boot/initramfs-linux-lts.img > "$out/initramfs-contents.txt"
for module in btrfs virtio_pci virtio_blk; do
    grep -Eq "(^|/)${module//_/-}\.ko(\.(zst|xz|gz))?$|(^|/)$module\.ko(\.(zst|xz|gz))?$" "$out/initramfs-contents.txt" || {
        echo "Missing required initramfs module: $module" >&2
        exit 1
    }
done
phase inventory
chroot "$root" pacman -Q > "$out/installed-packages.txt"
(cd "$out" && sha256sum installed-packages.txt | awk '{print $1 "  -"}') > "$root/etc/supra-lab-inventory.sha256"
cp "$root/boot/vmlinuz-linux-lts" "$out/target-kernel"
cp "$root/boot/initramfs-linux-lts.img" "$out/target-initrd"
(cd "$out" && sha256sum target-kernel target-initrd > boot.sha256)
for path in "$root/dev" "$root/sys" "$root/proc"; do umount "$path"; done
phase snapshot
btrfs subvolume snapshot -r "$top/deployments/staged" "$top/deployments/base"
test "$(btrfs property get -ts "$top/deployments/base" ro)" = ro=true
test "$(btrfs property get -ts "$root" ro)" = ro=false
# This base is a snapshot of the prepared lab root, not a promoted deployment.
printf 'base_created=true\n' > "$out/layout.txt"
phase sync
sync
btrfs filesystem sync "$top"
phase cleanup
cleanup
trap - EXIT
printf '%s\n' SUPRA_BTRFS_ROOT_PREPARED > /dev/ttyS0
