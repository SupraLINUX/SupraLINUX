#!/usr/bin/env bash
# Use the already verified Arch root/kernel and a separate blank lab filesystem.
set -euo pipefail
target="$1"
work="$2"
out="$3"
python3 tools/system-lab/rootfs_evidence.py hashes "$out" "$work"
disk="$work/btrfs-lab.raw"
truncate -s 1G "$disk"
mkfs.btrfs -q -L SUPRA_BTRFS_LAB "$disk"
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-btrfs-kvm.txt"
timeout 180 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot \
    -kernel "$work/target-kernel" -initrd "$work/target-initrd" \
    -append 'root=LABEL=SUPRA_TARGET rootfstype=ext4 rw console=ttyS0 systemd.unit=multi-user.target supra_btrfs_probe=1' \
    -drive "file=$target,format=qcow2,if=virtio,index=0" \
    -drive "file=$disk,format=raw,if=virtio,index=1" \
    2>&1 | tee "$out/rootfs-btrfs-console.log"
python3 tools/system-lab/rootfs_btrfs_evidence.py "$out"
