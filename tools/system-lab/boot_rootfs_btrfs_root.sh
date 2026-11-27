#!/usr/bin/env bash
# All files are private disposable images; no host mounts or real devices.
set -euo pipefail
base=$(realpath "$1")
work=$(realpath "$2")/btrfs-root
out=$(realpath "$3")
mkdir "$work"
sha256sum "$base" > "$out/rootfs-btrfs-root-source.sha256"
qemu-img create -q -f qcow2 -F raw -b "$base" "$work/active.qcow2"
truncate -s 6G "$work/root.raw"
mkfs.btrfs -q -L SUPRA_BTRFS_ROOT "$work/root.raw"
truncate -s 256M "$work/output.raw"
mke2fs -q -F -t ext4 -L SUPRA_LAB_OUTPUT "$work/output.raw"
python3 tools/system-lab/rootfs_evidence.py hashes "$out" "$(dirname "$work")"
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-btrfs-root-prepare-kvm.txt"
prepare_rc=0
timeout 360 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 3072 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot \
    -kernel "$(dirname "$work")/target-kernel" -initrd "$(dirname "$work")/target-initrd" \
    -append 'root=/dev/vda rootfstype=ext4 rw console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_btrfs_root_prepare=1' \
    -drive "file=$work/active.qcow2,format=qcow2,if=virtio,index=0" \
    -drive "file=$base,format=raw,if=virtio,index=1,readonly=on" \
    -drive "file=$work/root.raw,format=raw,if=virtio,index=2" \
    -drive "file=$work/output.raw,format=raw,if=virtio,index=3" \
    2>&1 | tee "$out/rootfs-btrfs-root-prepare-console.log" || prepare_rc=$?
# Preserve partial diagnostics even if the guest failed before export completed.
debugfs -R "dump /mkinitcpio.log $out/rootfs-btrfs-root-mkinitcpio-partial.log" "$work/output.raw" 2>/dev/null || true
sha256sum -c "$out/rootfs-btrfs-root-source.sha256"
(( prepare_rc == 0 ))
python3 - "$out/rootfs-btrfs-root-prepare-console.log" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "tools/system-lab")
from rootfs_btrfs_root_evidence import ordered_marker
ordered_marker(Path(sys.argv[1]).read_text(errors="replace"), "SUPRA_BTRFS_ROOT_PREPARED")
PY
for name in target-kernel target-initrd boot.sha256 installed-packages.txt layout.txt mkinitcpio.log initramfs-contents.txt; do
    debugfs -R "dump /$name $work/$name" "$work/output.raw" 2>/dev/null
    test -s "$work/$name"
done
(cd "$work" && sha256sum -c boot.sha256)
cmp "$work/installed-packages.txt" "$out/installed-packages.txt"
cmp "$work/target-kernel" "$(dirname "$work")/target-kernel"
cp "$work/mkinitcpio.log" "$out/rootfs-btrfs-root-mkinitcpio.log"
cp "$work/initramfs-contents.txt" "$out/rootfs-btrfs-root-initramfs-contents.txt"
cp "$work/boot.sha256" "$out/rootfs-btrfs-root-boot.sha256"
grep -Fxq base_created=true "$work/layout.txt"
sha256sum -c "$out/rootfs-btrfs-root-source.sha256"
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-btrfs-root-kvm.txt"
timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot -snapshot \
    -kernel "$work/target-kernel" -initrd "$work/target-initrd" \
    -append 'root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=deployments/staged rw console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_btrfs_root_probe=1' \
    -drive "file=$work/root.raw,format=raw,if=virtio,index=0" \
    2>&1 | tee "$out/rootfs-btrfs-root-console.log"
python3 tools/system-lab/rootfs_btrfs_root_evidence.py "$out"
