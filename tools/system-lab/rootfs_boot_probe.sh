#!/usr/bin/env bash
# Test-only boot evidence, not a distribution service.
set -Eeuo pipefail
trap 'rc=$?; printf "SUPRA_BOOT_PROBE_ERROR line=%s exit=%s command=%s\n" "$LINENO" "$rc" "$BASH_COMMAND" >&2' ERR
export LC_ALL=C
test "$(cat /proc/1/comm)" = systemd
systemctl is-active --quiet multi-user.target
if grep -qw supra_layer_boot=1 /proc/cmdline; then
    /usr/local/libexec/supra-layer-boot-guest
elif grep -qw supra_btrfs_root_probe=1 /proc/cmdline; then
    source=$(findmnt -n -o SOURCE /)
    device=/dev/vda
    if grep -qw supra_btrfs_gpt_probe=1 /proc/cmdline; then device=/dev/vda2; fi
    test "${source%%\[*}" = "$device"
    test "$(findmnt -n -o FSTYPE /)" = btrfs
    test "$(findmnt -n -o FSROOT /)" = /deployments/staged
    test "$(blkid -s LABEL -o value "$device")" = SUPRA_BTRFS_ROOT
    test "$(btrfs property get -ts / ro)" = ro=false
    test "$(cat /etc/supra-lab-deployment)" = staged
    pacman -Q | sha256sum --check /etc/supra-lab-inventory.sha256
    printf '%s\n' SUPRA_BTRFS_ROOT_READY > /dev/ttyS0
else
    test "$(findmnt --noheadings --output MAJ:MIN /)" = "$(lsblk -dn -o MAJ:MIN /dev/vda)"
    test "$(findmnt -n -o FSTYPE /)" = ext4
    test "$(blkid -s LABEL -o value /dev/vda)" = SUPRA_TARGET
fi
if grep -qw supra_install_recover=1 /proc/cmdline; then
    /usr/local/libexec/supra-install-recover
fi
if grep -qw supra_layer_prepare=1 /proc/cmdline; then
    /usr/local/libexec/supra-layer-guest
fi
if grep -qw supra_btrfs_root_prepare=1 /proc/cmdline; then
    /usr/local/libexec/supra-btrfs-prepare
fi
if grep -qw supra_btrfs_probe=1 /proc/cmdline; then
    /usr/local/libexec/supra-btrfs-probe
fi
if grep -qw supra_uefi_probe=1 /proc/cmdline; then
    test -d /sys/firmware/efi
    test "$(cat /sys/firmware/efi/fw_platform_size)" = 64
    printf '%s\n' SUPRA_UEFI_BOOT_READY > /dev/ttyS0
fi
if grep -qw supra_btrfs_gpt_probe=1 /proc/cmdline; then
    test -d /sys/firmware/efi
    test "$(cat /sys/firmware/efi/fw_platform_size)" = 64
    test "$(lsblk -dn -o PTTYPE /dev/vda)" = gpt
    test "$(lsblk -dn -o PKNAME /dev/vda1)" = vda
    test "$(lsblk -dn -o PKNAME /dev/vda2)" = vda
    test "$(lsblk -dn -o PARTTYPE /dev/vda1)" = c12a7328-f81f-11d2-ba4b-00a0c93ec93b
    test "$(blkid -s TYPE -o value /dev/vda1)" = vfat
    test "$(blkid -s LABEL -o value /dev/vda1)" = SUPRA_ESP
    test "$(lsblk -dn -o TYPE | grep -cx disk)" = 1
    # The disposable GPT entry disables automatic GPT mounts so this probe
    # is the sole ESP mount owner. Never remount an already active ESP.
    grep -qw systemd.gpt_auto=0 /proc/cmdline
    if findmnt -rn -S /dev/vda1; then
        echo "Unexpected pre-existing ESP mount" >&2
        exit 1
    fi
    esp=$(mktemp -d)
    mount -t vfat -o ro /dev/vda1 "$esp"
    test "$(findmnt -n -o SOURCE --mountpoint "$esp")" = /dev/vda1
    findmnt -n -o OPTIONS --mountpoint "$esp" | tr , '\n' | grep -Fx ro
    cmp "$esp/vmlinuz-linux-lts" /boot/vmlinuz-linux-lts
    cmp "$esp/initramfs-linux-lts.img" /boot/initramfs-linux-lts.img
    umount "$esp"
    rmdir "$esp"
    printf '%s\n' SUPRA_BTRFS_GPT_READY > /dev/ttyS0
fi
printf '%s\n' SUPRA_TARGET_BOOT_READY > /dev/ttyS0
systemctl --no-block poweroff
