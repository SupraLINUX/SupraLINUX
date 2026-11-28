#!/usr/bin/env bash
# Same disk and persistent OVMF variable store across all three powered-off
# boots. Only guest bootctl selects the trial. No host entry edits in between.
set -euo pipefail
work=$(realpath "$1")
out=$(realpath "$2")
source="$work/layer/uefi"
lab="$work/layer/oneshot"
mkdir "$lab"
sha256sum -c "$out/rootfs-layer-uefi-layer.sha256"
cp --reflink=auto --sparse=always "$source/disk.raw" "$lab/disk.raw"
cp "$source/esp.fat" "$lab/esp.fat"
printf 'default supra-staged.conf\ntimeout 0\neditor no\n' > "$lab/loader.conf"
mcopy -o -i "$lab/esp.fat" "$lab/loader.conf" ::/loader/loader.conf
for deployment in staged layer; do
    sed '/^options /s/$/ supra_layer_oneshot=1/' "$source/supra-$deployment.conf" > "$lab/supra-$deployment.conf"
    mcopy -o -i "$lab/esp.fat" "$lab/supra-$deployment.conf" "::/loader/entries/supra-$deployment.conf"
done
dd if="$lab/esp.fat" of="$lab/disk.raw" bs=1M seek=1 conv=notrunc status=none
sha256sum "$lab/disk.raw" > "$out/rootfs-layer-oneshot-disk.sha256"
code=/usr/share/OVMF/OVMF_CODE_4M.fd
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$lab/vars.fd"
for phase in arm trial return; do
    sha256sum "$lab/vars.fd" >> "$out/rootfs-layer-oneshot-vars-history.sha256"
    bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-layer-oneshot-$phase-kvm.txt"
    status=0
    timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
        -display none -monitor none -serial stdio -nic none -no-reboot \
        -drive "if=pflash,format=raw,readonly=on,file=$code" \
        -drive "if=pflash,format=raw,file=$lab/vars.fd" \
        -drive "if=none,id=target,format=raw,file=$lab/disk.raw,snapshot=on" \
        -device virtio-blk-pci,drive=target,addr=0x5,bootindex=1 \
        2>&1 | tee "$out/rootfs-layer-oneshot-$phase-console.log" || status=$?
    sha256sum -c "$out/rootfs-layer-oneshot-disk.sha256"
    (( status == 0 ))
done
sha256sum "$lab/vars.fd" >> "$out/rootfs-layer-oneshot-vars-history.sha256"
sha256sum -c "$out/rootfs-layer-uefi-layer.sha256"
python3 tools/layer-lab/oneshot_evidence.py "$out"

# Explicit promotion and reversal, separate from the unpromoted trial.
bash tools/layer-lab/run_layer_promotion.sh "$work" "$out"
