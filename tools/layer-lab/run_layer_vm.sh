#!/usr/bin/env bash
# Only private disposable disk images, never attach real host disks.
set -euo pipefail
base=$(realpath "$1")
work=$(realpath "$2")
out=$(realpath "$3")
lab="$work/layer"
mkdir "$lab" "$lab/input"
cp layer-input/{layer.tsv,expected.txt} "$lab/input/"
cp layer-packages/* "$lab/input/"
truncate -s 64M "$lab/input.raw"
mke2fs -q -F -t ext4 -L SUPRA_LAYER_IN -d "$lab/input" "$lab/input.raw"
truncate -s 64M "$lab/output.raw"
mke2fs -q -F -t ext4 -L SUPRA_LAB_OUTPUT "$lab/output.raw"
# Preserve the approved Btrfs checkpoint byte-for-byte; layer mutations in overlay.
sha256sum "$base" "$work/root.raw" "$lab/input.raw" > "$out/rootfs-layer-source.sha256"
qemu-img create -q -f qcow2 -F raw -b "$base" "$lab/active.qcow2"
qemu-img create -q -f qcow2 -F raw -b "$work/root.raw" "$lab/layer.qcow2"
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-layer-kvm.txt"
status=0
timeout 360 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 3072 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot \
    -kernel "$(dirname "$work")/target-kernel" -initrd "$(dirname "$work")/target-initrd" \
    -append 'root=/dev/vda rootfstype=ext4 rw console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_layer_prepare=1' \
    -drive "file=$lab/active.qcow2,format=qcow2,if=virtio,index=0" \
    -drive "file=$lab/layer.qcow2,format=qcow2,if=virtio,index=1" \
    -drive "file=$lab/input.raw,format=raw,if=virtio,index=2,readonly=on" \
    -drive "file=$lab/output.raw,format=raw,if=virtio,index=3" \
    2>&1 | tee "$out/rootfs-layer-prepare-console.log" || status=$?
for name in active-before.txt active-after.txt base-before.txt base-after.txt previous-before.txt previous-after.txt base-before-subvolume.txt base-after-subvolume.txt base-before-content.sha256 base-after-content.sha256 previous-before-content.sha256 previous-after-content.sha256 install.log layer-installed.txt tree-version.txt; do
    debugfs -R "dump /$name $out/rootfs-layer-$name" "$lab/output.raw" 2>/dev/null || true
done
sha256sum -c "$out/rootfs-layer-source.sha256"
(( status == 0 ))
python3 - "$out/rootfs-layer-prepare-console.log" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, 'tools/system-lab')
from rootfs_btrfs_root_evidence import ordered_marker
ordered_marker(Path(sys.argv[1]).read_text(errors='replace'), 'SUPRA_LAYER_PREPARED')
PY
sha256sum "$lab/layer.qcow2" > "$out/rootfs-layer-checkpoint.sha256"
# Boot independently using transient overlays; never change shared checkpoint.
for deployment in staged layer; do
    bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-layer-$deployment-kvm.txt"
    timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
        -display none -monitor none -serial stdio -nic none -no-reboot -snapshot \
        -kernel "$work/target-kernel" -initrd "$work/target-initrd" \
        -append "root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=deployments/$deployment rw console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_layer_boot=1" \
        -drive "file=$lab/layer.qcow2,format=qcow2,if=virtio,index=0" \
        2>&1 | tee "$out/rootfs-layer-$deployment-console.log"
done
sha256sum -c "$out/rootfs-layer-source.sha256"
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
python3 tools/layer-lab/layer_evidence.py "$out"

# Run the next firmware gate only after direct boot evidence is validated.
bash tools/layer-lab/run_layer_uefi.sh "$work" "$out"

# Separate private overlay: interrupt actual package hook before publication.
bash tools/layer-lab/run_install_interruption.sh "$base" "$work" "$out"

# Independent read-only root and state persistence gate.
bash tools/layer-lab/run_immutable_vm.sh "$base" "$work" "$out"
