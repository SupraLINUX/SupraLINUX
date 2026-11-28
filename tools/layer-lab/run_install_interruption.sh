#!/usr/bin/env bash
# Independent interrupted installation, never mutate the successful checkpoint.
set -euo pipefail
base=$(realpath "$1")
work=$(realpath "$2")
out=$(realpath "$3")
lab="$work/layer/install-interruption"
mkdir "$lab"
sha256sum -c "$out/rootfs-layer-source.sha256"
qemu-img create -q -f qcow2 -F raw -b "$base" "$lab/active.qcow2"
qemu-img create -q -f qcow2 -F raw -b "$work/root.raw" "$lab/stage.qcow2"
for role in prepare recovery; do
    truncate -s 64M "$lab/$role.raw"
    mke2fs -q -F -t ext4 -L SUPRA_LAB_OUTPUT "$lab/$role.raw"
done
common=(-accel kvm -machine q35 -cpu host -m 3072 -smp 2
    -display none -monitor none -serial stdio -nic none -no-reboot
    -kernel "$(dirname "$work")/target-kernel" -initrd "$(dirname "$work")/target-initrd"
    -drive "file=$lab/active.qcow2,format=qcow2,if=virtio,index=0,cache=none"
    -drive "file=$lab/stage.qcow2,format=qcow2,if=virtio,index=1,cache=none")
cmd='root=/dev/vda rootfstype=ext4 rw console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service'
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-layer-install-interrupt-kvm.txt"
python3 tools/layer-lab/interrupt_vm.py "$out/rootfs-layer-install-interrupt-console.log" "$out/rootfs-layer-install-injection.json" --install -- qemu-system-x86_64 "${common[@]}" \
    -append "$cmd supra_layer_prepare=1 supra_install_interrupt=1" \
    -drive "file=$work/layer/input.raw,format=raw,if=virtio,index=2,readonly=on" \
    -drive "file=$lab/prepare.raw,format=raw,if=virtio,index=3,cache=none"
for role in active stage; do qemu-img check "$lab/$role.qcow2" | tee "$out/rootfs-layer-install-$role-check.txt"; done
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-layer-install-recover-kvm.txt"
timeout 240 qemu-system-x86_64 "${common[@]}" -append "$cmd supra_install_recover=1" \
    -drive "file=$lab/recovery.raw,format=raw,if=virtio,index=2,cache=none" \
    2>&1 | tee "$out/rootfs-layer-install-recover-console.log"
for file in base-recovered.sha256 previous-recovered.sha256 previous-recovered.txt; do
    debugfs -R "dump /$file $out/rootfs-layer-install-$file" "$lab/recovery.raw" 2>/dev/null
done
cmp "$out/rootfs-layer-base-before-content.sha256" "$out/rootfs-layer-install-base-recovered.sha256"
cmp "$out/rootfs-layer-previous-before-content.sha256" "$out/rootfs-layer-install-previous-recovered.sha256"
cmp "$out/rootfs-layer-previous-before.txt" "$out/rootfs-layer-install-previous-recovered.txt"
sha256sum -c "$out/rootfs-layer-source.sha256"
# Verify previous deployment actually boots after Btrfs recovery.
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-layer-install-previous-kvm.txt"
timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot -snapshot \
    -kernel "$work/target-kernel" -initrd "$work/target-initrd" \
    -append 'root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=deployments/staged rw console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_layer_boot=1' \
    -drive "file=$lab/stage.qcow2,format=qcow2,if=virtio,index=0" \
    2>&1 | tee "$out/rootfs-layer-install-previous-console.log"
python3 tools/layer-lab/install_interruption_evidence.py "$out"
