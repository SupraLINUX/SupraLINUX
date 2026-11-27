#!/usr/bin/env bash
# Test-only boot evidence, not a distribution service.
set -euo pipefail
test "$(cat /proc/1/comm)" = systemd
systemctl is-active --quiet multi-user.target
test "$(findmnt --noheadings --output FSTYPE /)" = ext4
test "$(findmnt --noheadings --output MAJ:MIN /)" = "$(lsblk -dn -o MAJ:MIN /dev/vda)"
test "$(blkid -s LABEL -o value /dev/vda)" = SUPRA_TARGET
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
