#!/usr/bin/env bash
# Test-only boot evidence, not a distribution service.
set -euo pipefail
test "$(cat /proc/1/comm)" = systemd
systemctl is-active --quiet multi-user.target
test "$(findmnt --noheadings --output FSTYPE /)" = ext4
test "$(findmnt --noheadings --output MAJ:MIN /)" = "$(lsblk -dn -o MAJ:MIN /dev/vda)"
test "$(blkid -s LABEL -o value /dev/vda)" = SUPRA_TARGET
printf '%s\n' SUPRA_TARGET_BOOT_READY > /dev/ttyS0
systemctl --no-block poweroff
