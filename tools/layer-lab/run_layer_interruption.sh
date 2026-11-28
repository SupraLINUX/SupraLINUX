#!/usr/bin/env bash
# Abrupt interruption of an unpromoted trial, persistent private QCOW2.
# No host selection changes after initial setup.
set -euo pipefail
work=$(realpath "$1")
out=$(realpath "$2")
source="$work/layer/uefi"
lab="$work/layer/interruption"
mkdir "$lab"
sha256sum -c "$out/rootfs-layer-uefi-layer.sha256"
cp --reflink=auto --sparse=always "$source/disk.raw" "$lab/disk.raw"
cp "$source/esp.fat" "$lab/esp.fat"
printf 'default supra-staged.conf\ntimeout 0\neditor no\n' > "$lab/loader.conf"
mcopy -o -i "$lab/esp.fat" "$lab/loader.conf" ::/loader/loader.conf
for deployment in staged layer; do
    sed '/^options /s/$/ supra_layer_interrupt=1/' "$source/supra-$deployment.conf" > "$lab/supra-$deployment.conf"
    mcopy -o -i "$lab/esp.fat" "$lab/supra-$deployment.conf" "::/loader/entries/supra-$deployment.conf"
done
dd if="$lab/esp.fat" of="$lab/disk.raw" bs=1M seek=1 conv=notrunc status=none
sha256sum "$lab/disk.raw" > "$out/rootfs-layer-interruption-disk.sha256"
code=/usr/share/OVMF/OVMF_CODE_4M.fd
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$lab/vars.fd"
qemu-img create -q -f qcow2 -F raw -b "$lab/disk.raw" "$lab/persistent.qcow2"
for phase in arm interrupt return; do
    sha256sum "$lab/vars.fd" >> "$out/rootfs-layer-interruption-vars-history.sha256"
    bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-layer-interruption-$phase-kvm.txt"
    args=(-accel kvm -machine q35 -cpu host -m 2048 -smp 2
        -display none -monitor none -serial stdio -nic none -no-reboot
        -drive "if=pflash,format=raw,readonly=on,file=$code"
        -drive "if=pflash,format=raw,file=$lab/vars.fd"
        -drive "if=none,id=target,format=qcow2,file=$lab/persistent.qcow2,cache=none"
        -device virtio-blk-pci,drive=target,addr=0x5,bootindex=1)
    if [[ "$phase" = interrupt ]]; then
        python3 tools/layer-lab/interrupt_vm.py "$out/rootfs-layer-interruption-$phase-console.log" "$out/rootfs-layer-interruption-injection.json" -- qemu-system-x86_64 "${args[@]}"
    else
        timeout 240 qemu-system-x86_64 "${args[@]}" 2>&1 | tee "$out/rootfs-layer-interruption-$phase-console.log"
    fi
    sha256sum -c "$out/rootfs-layer-interruption-disk.sha256"
    # No repair: a corrupt QCOW2 container fails the experiment.
    qemu-img check "$lab/persistent.qcow2" | tee "$out/rootfs-layer-interruption-$phase-image-check.txt"
done
sha256sum "$lab/vars.fd" >> "$out/rootfs-layer-interruption-vars-history.sha256"
sha256sum -c "$out/rootfs-layer-uefi-layer.sha256"
python3 tools/layer-lab/interruption_evidence.py "$out"
