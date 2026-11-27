#!/usr/bin/env bash
# Test independent Type #1 boot selections on a private single GPT disk.
# Not activation, boot counting, or rollback. Never write the original checkpoint.
set -euo pipefail
work=$(realpath "$1")
out=$(realpath "$2")
lab="$work/layer/uefi"
mkdir "$lab"
# Start with the already validated GPT geometry and firmware assets.
sha256sum -c "$out/rootfs-btrfs-gpt-image.sha256"
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
qemu-img convert -f qcow2 -O raw "$work/layer/layer.qcow2" "$lab/root.raw"
test "$(stat -c %s "$lab/root.raw")" = "$(stat -c %s "$work/root.raw")"
cp --reflink=auto --sparse=always "$work/gpt/gpt.raw" "$lab/disk.raw"
cp "$work/gpt/esp.fat" "$lab/esp.fat"
mren -i "$lab/esp.fat" ::/loader/entries/supra.conf ::/loader/entries/supra-staged.conf
for deployment in staged layer; do
    cat > "$lab/supra-$deployment.conf" <<CONF
title SupraLINUX experimental $deployment
linux /vmlinuz-linux-lts
initrd /initramfs-linux-lts.img
options systemd.gpt_auto=0 root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=deployments/$deployment rw console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_layer_boot=1 supra_layer_uefi=1
CONF
    mcopy -o -i "$lab/esp.fat" "$lab/supra-$deployment.conf" "::/loader/entries/supra-$deployment.conf"
done
# Replace root partition bytes exactly; sparse writes into an existing file
# would skip zeros and leave old data, so do NOT use conv=sparse here.
dd if="$lab/root.raw" of="$lab/disk.raw" bs=1M seek=513 conv=notrunc status=none
root_hash=$(sha256sum "$lab/root.raw" | cut -d' ' -f1)
test "$(dd if="$lab/disk.raw" bs=1M skip=513 count=$(($(stat -c %s "$lab/root.raw")/1048576)) status=none | sha256sum | cut -d' ' -f1)" = "$root_hash"
sgdisk --verify "$lab/disk.raw" | tee "$out/rootfs-layer-uefi-gpt.txt"
code=/usr/share/OVMF/OVMF_CODE_4M.fd
vars=/usr/share/OVMF/OVMF_VARS_4M.fd
for deployment in staged layer; do
    printf 'default supra-%s.conf\ntimeout 0\neditor no\n' "$deployment" > "$lab/loader.conf"
    mcopy -o -i "$lab/esp.fat" "$lab/loader.conf" ::/loader/loader.conf
    dd if="$lab/esp.fat" of="$lab/disk.raw" bs=1M seek=1 conv=notrunc status=none
    esp_hash=$(sha256sum "$lab/esp.fat" | cut -d' ' -f1)
    test "$(dd if="$lab/disk.raw" bs=1M skip=1 count=512 status=none | sha256sum | cut -d' ' -f1)" = "$esp_hash"
    sha256sum "$lab/disk.raw" > "$out/rootfs-layer-uefi-$deployment.sha256"
    cp "$vars" "$lab/$deployment-vars.fd"
    bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-layer-uefi-$deployment-kvm.txt"
    status=0
    timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
        -display none -monitor none -serial stdio -nic none -no-reboot \
        -drive "if=pflash,format=raw,readonly=on,file=$code" \
        -drive "if=pflash,format=raw,file=$lab/$deployment-vars.fd" \
        -drive "if=none,id=target,format=raw,file=$lab/disk.raw,snapshot=on" \
        -device virtio-blk-pci,drive=target,addr=0x5,bootindex=1 \
        2>&1 | tee "$out/rootfs-layer-uefi-$deployment-console.log" || status=$?
    sha256sum -c "$out/rootfs-layer-uefi-$deployment.sha256"
    (( status == 0 ))
done
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
sha256sum -c "$out/rootfs-btrfs-gpt-image.sha256"
python3 tools/layer-lab/layer_uefi_evidence.py "$out"
