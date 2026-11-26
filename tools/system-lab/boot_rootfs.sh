#!/usr/bin/env bash
# Direct kernel boot probe, not UEFI or a deployable disk image.
set -euo pipefail
target="$1"
work="$2"
out="$3"
debugfs -R "dump /boot/vmlinuz-linux-lts $work/target-kernel" "$target" 2>/dev/null
debugfs -R "dump /boot/initramfs-linux-lts.img $work/target-initrd" "$target" 2>/dev/null
test -s "$work/target-kernel"
test -s "$work/target-initrd"
expected_kernel=$(awk '$2=="/boot/vmlinuz-linux-lts" {print $1}' "$out/rootfs-boot-files.sha256")
expected_initrd=$(awk '$2=="/boot/initramfs-linux-lts.img" {print $1}' "$out/rootfs-boot-files.sha256")
printf '%s  %s\n' "$expected_kernel" "$work/target-kernel" "$expected_initrd" "$work/target-initrd" | sha256sum -c
timeout 180 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot \
    -kernel "$work/target-kernel" -initrd "$work/target-initrd" \
    -append 'root=LABEL=SUPRA_TARGET rootfstype=ext4 rw console=ttyS0 systemd.unit=multi-user.target' \
    -drive "file=$target,format=raw,if=virtio" \
    2>&1 | tee "$out/rootfs-target-console.log"
# The marker is produced only by the probe service after multi-user.target.
grep -Eq '^SUPRA_TARGET_BOOT_READY[[:space:]]*$' "$out/rootfs-target-console.log"
printf '%s\n' '{"schema_version":1,"direct_kernel_boot_verified":true,"uefi_boot_verified":false,"release_signed":false}' > "$out/rootfs-target-boot.json"
