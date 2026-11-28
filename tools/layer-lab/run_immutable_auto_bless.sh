#!/usr/bin/env bash
# Independent automatic health dependency test, positive and rejected candidate.
set -euo pipefail
work=$(realpath "$1")
out=$(realpath "$2")
source="$work/layer/immutable"
mode=$3
case "$mode" in accept|reject) ;; *) exit 1 ;; esac
lab="$source/auto-$mode"
mkdir "$lab"
cp --reflink=auto --sparse=always "$source/uefi/disk.raw" "$lab/disk.raw"
cp --reflink=auto --sparse=always "$source/uefi-state.raw" "$lab/state.raw"
cp "$source/uefi/esp.fat" "$lab/esp.fat"
for role in staged layer; do
    version=1
    phase=count-return
    name=supra-immutable-staged.conf
    flag=supra_immutable_bootcount=1
    if [[ "$role" = layer ]]; then
        version=2
        phase=auto-bless
        name=supra-immutable-layer+2.conf
        flag=supra_immutable_auto_bless=1
        if [[ "$mode" = reject ]]; then
            name=supra-immutable-layer+1.conf
            flag="$flag supra_immutable_reject=1"
        fi
    fi
    cat > "$lab/$role.conf" <<CONF
title SupraLINUX healthy $role
sort-key supra
version $version
linux /vmlinuz-linux-lts
initrd /initramfs-linux-lts.img
options systemd.gpt_auto=0 root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=immutable/$role ro console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_immutable_boot=1 supra_immutable_uefi=1 supra_immutable_phase=$phase $flag
CONF
    mcopy -o -i "$lab/esp.fat" "$lab/$role.conf" "::/loader/entries/$name"
done
printf 'default supra-immutable-*\ntimeout 0\neditor no\nauto-entries no\nauto-firmware no\n' > "$lab/loader.conf"
mcopy -o -i "$lab/esp.fat" "$lab/loader.conf" ::/loader/loader.conf
dd if="$lab/esp.fat" of="$lab/disk.raw" bs=1M seek=1 conv=notrunc status=none
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$lab/vars.fd"
inspect() {
    local phase=$1 candidate=$2
    local img="$lab/disk.raw@@1048576"
    mdir -b -i "$img" ::/loader/entries/ | tee "$out/rootfs-auto-$mode-$phase-entries.txt"
    mtype -i "$img" ::/loader/loader.conf | cmp - "$lab/loader.conf"
    mtype -i "$img" ::/loader/entries/supra-immutable-staged.conf | cmp - "$lab/staged.conf"
    mtype -i "$img" "::/loader/entries/$candidate" | cmp - "$lab/layer.conf"
    python3 tools/layer-lab/auto_bless_evidence.py "$out" "$mode" "$phase"
}
if [[ "$mode" = accept ]]; then
    inspect initial supra-immutable-layer+2.conf
else
    inspect initial supra-immutable-layer+1.conf
fi
for phase in first second; do
    bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-auto-$mode-$phase-kvm.txt"
    timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
        -display none -monitor none -serial stdio -nic none -no-reboot \
        -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
        -drive "if=pflash,format=raw,file=$lab/vars.fd" \
        -drive "if=none,id=target,format=raw,file=$lab/disk.raw,cache=none" \
        -device virtio-blk-pci,drive=target,addr=0x5,bootindex=1 \
        -drive "if=none,id=state,format=raw,file=$lab/state.raw,cache=none" \
        -device virtio-blk-pci,drive=state,addr=0x6 \
        2>&1 | tee "$out/rootfs-auto-$mode-$phase-console.log"
    if [[ "$mode" = accept ]]; then
        inspect "$phase" supra-immutable-layer.conf
    else
        inspect "$phase" supra-immutable-layer+0-1.conf
    fi
done
sgdisk --verify "$lab/disk.raw" | tee "$out/rootfs-auto-$mode-gpt.txt"
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
python3 tools/layer-lab/auto_bless_evidence.py "$out" "$mode"
