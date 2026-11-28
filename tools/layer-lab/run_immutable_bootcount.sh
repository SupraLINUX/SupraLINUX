#!/usr/bin/env bash
# Private copies only. No host writes to boot entries, ESP or NVRAM after setup.
set -euo pipefail
work=$(realpath "$1")
out=$(realpath "$2")
source="$work/layer/immutable"
lab="$source/bootcount"
mkdir "$lab"
cp --reflink=auto --sparse=always "$source/uefi/disk.raw" "$lab/disk.raw"
cp --reflink=auto --sparse=always "$source/uefi-state.raw" "$lab/state.raw"
cp "$source/uefi/esp.fat" "$lab/esp.fat"
for role in staged layer; do
    version=1
    phase=count-return
    name=supra-immutable-staged.conf
    mask=
    if [[ "$role" = layer ]]; then
        version=2
        phase=count-trial
        name=supra-immutable-layer+2.conf
        mask='systemd.mask=systemd-bless-boot.service'
    fi
    cat > "$lab/$role.conf" <<CONF
title SupraLINUX counted $role
sort-key supra
version $version
linux /vmlinuz-linux-lts
initrd /initramfs-linux-lts.img
options systemd.gpt_auto=0 root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=immutable/$role ro console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_immutable_boot=1 supra_immutable_uefi=1 supra_immutable_bootcount=1 supra_immutable_phase=$phase $mask
CONF
    mcopy -o -i "$lab/esp.fat" "$lab/$role.conf" "::/loader/entries/$name"
done
printf 'default supra-immutable-*\ntimeout 0\neditor no\nauto-entries no\nauto-firmware no\n' > "$lab/loader.conf"
mcopy -o -i "$lab/esp.fat" "$lab/loader.conf" ::/loader/loader.conf
dd if="$lab/esp.fat" of="$lab/disk.raw" bs=1M seek=1 conv=notrunc status=none
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$lab/vars.fd"
code=/usr/share/OVMF/OVMF_CODE_4M.fd
# Read the real ESP from the powered-off disk, never mount or edit it.
inspect() {
    local phase=$1 candidate=$2
    local img="$lab/disk.raw@@1048576"
    mdir -b -i "$img" ::/loader/entries/ | tee "$out/rootfs-bootcount-$phase-entries.txt"
    mtype -i "$img" ::/loader/loader.conf | cmp - "$lab/loader.conf"
    mtype -i "$img" ::/loader/entries/supra-immutable-staged.conf | cmp - "$lab/staged.conf"
    mtype -i "$img" "::/loader/entries/$candidate" | cmp - "$lab/layer.conf"
    python3 tools/layer-lab/bootcount_evidence.py "$out" "$phase"
}
inspect initial supra-immutable-layer+2.conf
for phase in trial1 trial2 fallback; do
    bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-bootcount-$phase-kvm.txt"
    args=(-accel kvm -machine q35 -cpu host -m 2048 -smp 2
        -display none -monitor none -serial stdio -nic none -no-reboot
        -drive "if=pflash,format=raw,readonly=on,file=$code"
        -drive "if=pflash,format=raw,file=$lab/vars.fd"
        -drive "if=none,id=target,format=raw,file=$lab/disk.raw,cache=none"
        -device virtio-blk-pci,drive=target,addr=0x5,bootindex=1
        -drive "if=none,id=state,format=raw,file=$lab/state.raw,cache=none"
        -device virtio-blk-pci,drive=state,addr=0x6)
    if [[ "$phase" = fallback ]]; then
        timeout 240 qemu-system-x86_64 "${args[@]}" 2>&1 | tee "$out/rootfs-bootcount-$phase-console.log"
        inspect "$phase" supra-immutable-layer+0-2.conf
    else
        python3 tools/layer-lab/interrupt_vm.py "$out/rootfs-bootcount-$phase-console.log" "$out/rootfs-bootcount-$phase-injection.json" --bootcount -- qemu-system-x86_64 "${args[@]}"
        if [[ "$phase" = trial1 ]]; then
            inspect "$phase" supra-immutable-layer+1-1.conf
        else
            inspect "$phase" supra-immutable-layer+0-2.conf
        fi
    fi
done
sgdisk --verify "$lab/disk.raw" | tee "$out/rootfs-bootcount-gpt.txt"
sha256sum -c "$out/rootfs-layer-checkpoint.sha256"
python3 tools/layer-lab/bootcount_evidence.py "$out"

# Test healthy confirmation on an independent copy.
bash tools/layer-lab/run_immutable_bless.sh "$work" "$out"
