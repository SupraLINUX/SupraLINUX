#!/usr/bin/env bash
# Test-only boot evidence, not a distribution service.
set -euo pipefail
export LC_ALL=C
test "$(cat /proc/1/comm)" = systemd
systemctl is-active --quiet multi-user.target
if grep -qw supra_btrfs_root_probe=1 /proc/cmdline; then
    source=$(findmnt -n -o SOURCE /)
    test "${source%%\[*}" = /dev/vda
    test "$(findmnt -n -o FSTYPE /)" = btrfs
    test "$(findmnt -n -o FSROOT /)" = /deployments/staged
    test "$(blkid -s LABEL -o value /dev/vda)" = SUPRA_BTRFS_ROOT
    test "$(btrfs property get -ts / ro)" = ro=false
    test "$(cat /etc/supra-lab-deployment)" = staged
    pacman -Q | sha256sum --check /etc/supra-lab-inventory.sha256
    printf '%s\n' SUPRA_BTRFS_ROOT_READY > /dev/ttyS0
else
    test "$(findmnt --noheadings --output MAJ:MIN /)" = "$(lsblk -dn -o MAJ:MIN /dev/vda)"
    test "$(findmnt -n -o FSTYPE /)" = ext4
    test "$(blkid -s LABEL -o value /dev/vda)" = SUPRA_TARGET
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
printf '%s\n' SUPRA_TARGET_BOOT_READY > /dev/ttyS0
systemctl --no-block poweroff
