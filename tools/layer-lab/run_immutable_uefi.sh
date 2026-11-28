#!/usr/bin/env bash
# Private GPT boot disk and separate persistent lab state; no host mounts.
set -euo pipefail
work=$(realpath "$1")
out=$(realpath "$2")
source="$work/layer/immutable"
lab="$source/uefi"
mkdir "$lab"
sha256sum -c "$out/rootfs-btrfs-gpt-image.sha256"
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
sha256sum -c "$out/rootfs-immutable-uefi-state-initial.sha256"
qemu-img convert -f qcow2 -O raw "$source/root.qcow2" "$lab/root.raw"
test "$(stat -c %s "$lab/root.raw")" = "$(stat -c %s "$work/root.raw")"
cp --reflink=auto --sparse=always "$work/gpt/gpt.raw" "$lab/disk.raw"
cp "$work/gpt/esp.fat" "$lab/esp.fat"
mren -i "$lab/esp.fat" ::/loader/entries/supra.conf ::/loader/entries/supra-immutable-staged.conf
# Install root once. Never rewrite it between boots.
dd if="$lab/root.raw" of="$lab/disk.raw" bs=1M seek=513 conv=notrunc status=none
root_hash=$(sha256sum "$lab/root.raw" | cut -d' ' -f1)
root_mib=$(($(stat -c %s "$lab/root.raw")/1048576))
test "$(dd if="$lab/disk.raw" bs=1M skip=513 count="$root_mib" status=none | sha256sum | cut -d' ' -f1)" = "$root_hash"
sgdisk --verify "$lab/disk.raw" | tee "$out/rootfs-immutable-uefi-gpt.txt"
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$lab/vars.fd"
code=/usr/share/OVMF/OVMF_CODE_4M.fd
for phase in first next return; do
    role=staged
    if [[ "$phase" = next ]]; then role=layer; fi
    # Deliberate host selection in this firmware integration gate ONLY.
    # Not boot counting or autonomous rollback; no writes to root partition.
    cat > "$lab/entry.conf" <<CONF
title SupraLINUX immutable $role
linux /vmlinuz-linux-lts
initrd /initramfs-linux-lts.img
options systemd.gpt_auto=0 root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=immutable/$role ro console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_immutable_boot=1 supra_immutable_uefi=1 supra_immutable_phase=$phase
CONF
    # Exactly one entry in the private ESP at a time; no stale fallback.
    if [[ "$phase" = next ]]; then
        mdel -i "$lab/esp.fat" ::/loader/entries/supra-immutable-staged.conf
    elif [[ "$phase" = return ]]; then
        mdel -i "$lab/esp.fat" ::/loader/entries/supra-immutable-layer.conf
    fi
    mcopy -o -i "$lab/esp.fat" "$lab/entry.conf" "::/loader/entries/supra-immutable-$role.conf"
    printf 'default supra-immutable-%s.conf\ntimeout 0\neditor no\n' "$role" > "$lab/loader.conf"
    mcopy -o -i "$lab/esp.fat" "$lab/loader.conf" ::/loader/loader.conf
    dd if="$lab/esp.fat" of="$lab/disk.raw" bs=1M seek=1 conv=notrunc status=none
    esp_hash=$(sha256sum "$lab/esp.fat" | cut -d' ' -f1)
    test "$(dd if="$lab/disk.raw" bs=1M skip=1 count=512 status=none | sha256sum | cut -d' ' -f1)" = "$esp_hash"
    bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-immutable-uefi-$phase-kvm.txt"
    timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
        -display none -monitor none -serial stdio -nic none -no-reboot \
        -drive "if=pflash,format=raw,readonly=on,file=$code" \
        -drive "if=pflash,format=raw,file=$lab/vars.fd" \
        -drive "if=none,id=target,format=raw,file=$lab/disk.raw,cache=none" \
        -device virtio-blk-pci,drive=target,addr=0x5,bootindex=1 \
        -drive "if=none,id=state,format=raw,file=$source/uefi-state.raw,cache=none" \
        -device virtio-blk-pci,drive=state,addr=0x6 \
        2>&1 | tee "$out/rootfs-immutable-uefi-$phase-console.log"
    python3 tools/layer-lab/immutable_uefi_evidence.py "$out" "$phase"
done
sgdisk --verify "$lab/disk.raw" | tee "$out/rootfs-immutable-uefi-final-gpt.txt"
sha256sum -c "$out/rootfs-btrfs-gpt-image.sha256"
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
python3 tools/layer-lab/immutable_uefi_evidence.py "$out"
