#!/usr/bin/env bash
# Separate private disk state, reuse the validated powered-off checkpoint.
set -euo pipefail
base=$(realpath "$1")
work=$(realpath "$2")
out=$(realpath "$3")
lab="$work/layer/immutable"
mkdir "$lab"
sha256sum -c "$out/rootfs-layer-source.sha256"
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
qemu-img create -q -f qcow2 -F raw -b "$base" "$lab/active.qcow2"
qemu-img create -q -f qcow2 -F qcow2 -b "$work/layer/layer.qcow2" "$lab/root.qcow2"
truncate -s 1G "$lab/state.raw"
mkfs.btrfs -q -L SUPRA_LAB_STATE "$lab/state.raw"
common=(-accel kvm -machine q35 -cpu host -m 2048 -smp 2
    -display none -monitor none -serial stdio -nic none -no-reboot)
cmd='console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service'
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-immutable-prepare-kvm.txt"
timeout 240 qemu-system-x86_64 "${common[@]}" \
    -kernel "$(dirname "$work")/target-kernel" -initrd "$(dirname "$work")/target-initrd" \
    -append "root=/dev/vda rootfstype=ext4 rw $cmd supra_immutable_prepare=1" \
    -drive "file=$lab/active.qcow2,format=qcow2,if=virtio,index=0,cache=none" \
    -drive "file=$lab/root.qcow2,format=qcow2,if=virtio,index=1,cache=none" \
    -drive "file=$lab/state.raw,format=raw,if=virtio,index=2,cache=none" \
    2>&1 | tee "$out/rootfs-immutable-prepare-console.log"
python3 tools/layer-lab/immutable_evidence.py "$out" prepare
# Powered-off pristine state for independent firmware trial, before sentinels.
cp --reflink=auto --sparse=always "$lab/state.raw" "$lab/uefi-state.raw"
sha256sum "$lab/uefi-state.raw" > "$out/rootfs-immutable-uefi-state-initial.sha256"
for phase in first next return; do
    role=staged
    if [[ "$phase" = next ]]; then role=layer; fi
    bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-immutable-$phase-kvm.txt"
    timeout 240 qemu-system-x86_64 "${common[@]}" \
        -kernel "$work/target-kernel" -initrd "$work/target-initrd" \
        -append "root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=immutable/$role ro $cmd supra_immutable_boot=1 supra_immutable_phase=$phase" \
        -drive "file=$lab/root.qcow2,format=qcow2,if=virtio,index=0,cache=none" \
        -drive "file=$lab/state.raw,format=raw,if=virtio,index=1,cache=none" \
        2>&1 | tee "$out/rootfs-immutable-$phase-console.log"
    python3 tools/layer-lab/immutable_evidence.py "$out" "$phase"
done
qemu-img check "$lab/root.qcow2" | tee "$out/rootfs-immutable-image-check.txt"
sha256sum -c "$out/rootfs-layer-source.sha256"
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
python3 tools/layer-lab/immutable_evidence.py "$out"

# Independently validate the same frozen layout through real EFI firmware.
bash tools/layer-lab/run_immutable_uefi.sh "$work" "$out"
